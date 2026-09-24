# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build for Morale. Run through packaging/build.py, which renders
# the icons first and then self-tests and packages the result.
import os
import re
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).parent
VERSION = re.search(r'__version__ = "([^"]+)"', (ROOT / "morale" / "__init__.py").read_text()).group(1)
ICONS = Path(os.environ.get("MORALE_ICON_DIR", ROOT / "build" / "icons"))
BUNDLE_ID = "io.github.vomitselfie.morale"

datas = [(str(ROOT / name), ".") for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "CHANGELOG.md")]
datas += collect_data_files("morale")

a = Analysis(
    [str(ROOT / "run_morale.py")],
    pathex=[str(ROOT)],
    datas=datas,
    excludes=["tkinter"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

version_info = None
if sys.platform == "win32":
    from PyInstaller.utils.win32.versioninfo import (FixedFileInfo, StringFileInfo, StringStruct, StringTable,
                                                     VarFileInfo, VarStruct, VSVersionInfo)
    numbers = tuple(int(part) for part in re.findall(r"\d+", VERSION)[:3]) + (0,)
    version_info = VSVersionInfo(
        ffi=FixedFileInfo(filevers=numbers, prodvers=numbers),
        kids=[StringFileInfo([StringTable("040904B0", [
            StringStruct("CompanyName", "Morale contributors"),
            StringStruct("FileDescription", "Morale embroidery studio"),
            StringStruct("FileVersion", VERSION),
            StringStruct("InternalName", "Morale"),
            StringStruct("LegalCopyright", "MIT License"),
            StringStruct("OriginalFilename", "Morale.exe"),
            StringStruct("ProductName", "Morale"),
            StringStruct("ProductVersion", VERSION)])]),
            VarFileInfo([VarStruct("Translation", [1033, 1200])])])

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Morale",
    console=False,
    # UPX-packed executables are often flagged by antivirus software.
    upx=False,
    icon=str(ICONS / ("morale.ico" if sys.platform == "win32" else "morale.icns")) if sys.platform in {"win32", "darwin"} else None,
    version=version_info,
    argv_emulation=False,
)
coll = COLLECT(exe, a.binaries, a.datas, upx=False, name="Morale")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Morale.app",
        icon=str(ICONS / "morale.icns"),
        bundle_identifier=BUNDLE_ID,
        version=VERSION,
        info_plist={
            "CFBundleName": "Morale",
            "CFBundleDisplayName": "Morale",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
            "NSHumanReadableCopyright": "MIT License",
            "LSApplicationCategoryType": "public.app-category.graphics-design",
            "CFBundleDocumentTypes": [{
                "CFBundleTypeName": "Morale embroidery project",
                "CFBundleTypeRole": "Editor",
                "LSHandlerRank": "Owner",
                "CFBundleTypeExtensions": ["morale"],
                "CFBundleTypeIconFile": "morale.icns",
            }],
        },
    )
