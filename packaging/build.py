"""Build, self-test and package Morale for the current platform.

    python packaging/build.py                      # bundle + packages into dist/release
    python packaging/build.py --check-tag v0.2.0   # only verify the release tag

Linux: AppImage and tar.gz. Windows: Inno Setup installer and portable zip.
macOS: ad-hoc signed app in a .dmg. PyInstaller cannot cross-compile, so each
platform builds its own packages.
"""
import argparse
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tomllib
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
APP_ID = "io.github.vomitselfie.morale"
APPIMAGETOOL = "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"


def version():
    """The package version, which must agree between the module and pyproject."""
    module = re.search(r'__version__ = "([^"]+)"', (ROOT / "morale" / "__init__.py").read_text()).group(1)
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    if module != project:
        raise SystemExit(f"Version mismatch: morale/__init__.py has {module}, pyproject.toml has {project}.")
    return module


def arch():
    machine = platform.machine().lower()
    return {"amd64": "x86_64", "x64": "x86_64", "aarch64": "arm64"}.get(machine, machine)


def run(*command, **options):
    print("+", " ".join(str(part) for part in command), flush=True)
    subprocess.run([str(part) for part in command], check=True, **options)


def build_bundle(icons):
    env = dict(os.environ, MORALE_ICON_DIR=str(icons))
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", ROOT / "dist",
        "--workpath", ROOT / "build" / "pyinstaller", ROOT / "packaging" / "morale.spec", env=env, cwd=ROOT)


def self_test():
    report = ROOT / "artifacts" / "bundle-self-test"
    if report.exists():
        shutil.rmtree(report)
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    run(sys.executable, ROOT / "scripts" / "check_bundle.py", "--dist", ROOT / "dist", "--output", report, env=env, cwd=ROOT)


def package_linux(name, output, icons):
    bundle = ROOT / "dist" / "Morale"
    share = bundle / "share"
    # Desktop integration files travel inside the portable folder too.
    (share / "applications").mkdir(parents=True, exist_ok=True)
    (share / "icons").mkdir(parents=True, exist_ok=True)
    (share / "mime").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "packaging" / "linux" / f"{APP_ID}.desktop", share / "applications")
    shutil.copy(ROOT / "packaging" / "linux" / f"{APP_ID}.xml", share / "mime")
    shutil.copy(icons / "morale-256.png", share / "icons" / f"{APP_ID}.png")
    archive = output / f"{name}.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        stream.add(bundle, arcname="Morale")
    outputs = [archive]
    appdir = ROOT / "build" / "Morale.AppDir"
    if appdir.exists():
        shutil.rmtree(appdir)
    shutil.copytree(bundle, appdir / "usr" / "lib" / "morale", symlinks=True)
    shutil.copy(ROOT / "packaging" / "linux" / f"{APP_ID}.desktop", appdir / f"{APP_ID}.desktop")
    shutil.copy(icons / "morale-256.png", appdir / f"{APP_ID}.png")
    shutil.copy(icons / "morale-256.png", appdir / ".DirIcon")
    apprun = appdir / "AppRun"
    apprun.write_text('#!/bin/sh\nHERE="$(dirname "$(readlink -f "$0")")"\nexec "$HERE/usr/lib/morale/Morale" "$@"\n')
    apprun.chmod(apprun.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    tool = Path(os.environ.get("APPIMAGETOOL", ROOT / "build" / "appimagetool-x86_64.AppImage"))
    if not tool.exists():
        print(f"Downloading appimagetool from {APPIMAGETOOL}", flush=True)
        urllib.request.urlretrieve(APPIMAGETOOL, tool)
    tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
    image = output / f"{name}.AppImage"
    # Extract-and-run avoids needing FUSE on build machines and containers; extract
    # under build/ because /tmp is mounted noexec on some systems.
    env = dict(os.environ, ARCH="x86_64", APPIMAGE_EXTRACT_AND_RUN="1", TMPDIR=str(ROOT / "build"))
    run(tool, "--no-appstream", appdir, image, env=env)
    return outputs + [image]


def find_iscc():
    candidates = [shutil.which("iscc"), shutil.which("ISCC")]
    for variable in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        base = os.environ.get(variable)
        if base:
            candidates += [Path(base) / "Inno Setup 6" / "ISCC.exe", Path(base) / "Programs" / "Inno Setup 6" / "ISCC.exe"]
    return next((Path(c) for c in candidates if c and Path(c).is_file()), None)


def package_windows(name, output, icons, current, installer=True):
    bundle = ROOT / "dist" / "Morale"
    archive = output / f"{name}-portable.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as stream:
        for path in sorted(bundle.rglob("*")):
            stream.write(path, Path("Morale") / path.relative_to(bundle))
    outputs = [archive]
    if installer:
        iscc = find_iscc()
        if iscc is None:
            raise SystemExit("Inno Setup 6 (ISCC.exe) was not found. Install it or pass --no-installer.")
        run(iscc, f"/DAppVersion={current}", f"/DSourceDir={bundle}", f"/DIconFile={icons / 'morale.ico'}",
            f"/DLicenseFile={ROOT / 'LICENSE'}", f"/DOutputDir={output}", f"/DOutputName={name}-setup",
            ROOT / "packaging" / "windows" / "morale.iss")
        outputs.append(output / f"{name}-setup.exe")
    return outputs


def package_macos(name, output):
    app = ROOT / "dist" / "Morale.app"
    # Apple silicon refuses unsigned code; an ad-hoc signature lets it run
    # (Gatekeeper still asks users to confirm an unidentified developer).
    run("codesign", "--force", "--deep", "--sign", "-", app)
    run("codesign", "--verify", "--deep", "--strict", app)
    staging = ROOT / "build" / "dmg"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    shutil.copytree(app, staging / "Morale.app", symlinks=True)
    (staging / "Applications").symlink_to("/Applications")
    image = output / f"{name}.dmg"
    image.unlink(missing_ok=True)
    run("hdiutil", "create", "-volname", "Morale", "-srcfolder", staging, "-ov", "-format", "UDZO", image)
    return [image]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "release")
    parser.add_argument("--check-tag", help="Only verify that a vX.Y.Z tag matches the package version")
    parser.add_argument("--skip-self-test", action="store_true")
    parser.add_argument("--no-installer", action="store_true", help="Windows: skip the Inno Setup installer")
    args = parser.parse_args()
    current = version()
    if args.check_tag is not None:
        if args.check_tag != f"v{current}":
            raise SystemExit(f"Tag {args.check_tag} does not match package version {current}.")
        print(f"Tag {args.check_tag} matches version {current}.")
        return
    from PySide6.QtGui import QGuiApplication
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    application = QGuiApplication.instance() or QGuiApplication([])
    sys.path.insert(0, str(ROOT / "packaging"))
    from icons import build_icons
    icons = build_icons(ROOT / "build" / "icons")
    build_bundle(icons)
    if not args.skip_self_test:
        self_test()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    system = {"linux": "linux", "win32": "windows", "darwin": "macos"}.get(sys.platform, sys.platform)
    name = f"Morale-{current}-{system}-{arch()}"
    if system == "linux":
        outputs = package_linux(name, output, icons)
    elif system == "windows":
        outputs = package_windows(name, output, icons, current, installer=not args.no_installer)
    elif system == "macos":
        outputs = package_macos(name, output)
    else:
        raise SystemExit(f"Packaging is not set up for {sys.platform}.")
    for path in outputs:
        print(f"Built {path} ({path.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
