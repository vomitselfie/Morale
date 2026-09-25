# Developing Morale

Morale is written in Python with the Qt (PySide6) toolkit. This page is for people
who want to run it from source, change it or publish releases. Users should
download a ready-made version instead: see the [README](../README.md).

## Run from source

```sh
conda activate morale
python -m morale
```

From a fresh Python 3.11+ environment:

```sh
python -m pip install -e ".[dev]"
python -m morale
```

The app opens an editable wildflower example. Use **File → New design** for a
blank hoop. Projects and exports are saved wherever you choose. Local recovery
copies protect interrupted sessions without overwriting your saved project.

Main-window stitch previews calculate in a separate process. Keep editing while
counts and stitches update; obsolete calculations are cancelled. **Cancel
calculation** stops a job and **Recalculate** retries it. Playback, machine export,
thread charts and stitch editing wait for a current preview. Projects can still
be saved while calculating. Preview workers have a 60-second limit. Some editing
commands still validate candidates synchronously, and some export/dialog
operations can still pause the interface. Opening and importing designs decode
the file in a separate process with a cancellable progress dialog and a 60-second
limit; a file that changes while it is read is rejected.

## Test and package

```sh
python -m pip install -e ".[dev]"
python -m pytest
python packaging/build.py
```

The test suite runs Qt with its offscreen platform plugin. Tests cover the engine,
project validation, all 81 ordered writer conversion pairs, controls/pauses, a
hand-encoded DST fixture, and native UI workflows. An unexpected modal message
box fails its test instead of waiting for a click. Real machine sew-outs and
externally produced golden files remain necessary evidence;
`python -m morale.compatibility --output docs/compatibility-report.json` refreshes
the synthetic format report.

`packaging/build.py` builds for the platform it runs on (PyInstaller does not
cross-compile). It renders the icons from the logo, bundles the app with
`packaging/morale.spec`, runs the bundle's self-test, and writes packages to
`dist/release/`:

| Platform | Packages |
| --- | --- |
| Linux | AppImage, plus a tar.gz with desktop-entry, icon and MIME files under `share/` |
| Windows | Inno Setup installer (per-user by default, optional `.morale` association) and a portable zip |
| macOS | Ad-hoc signed `Morale.app` in a `.dmg`, with `.morale` document type |

The Windows installer needs [Inno Setup 6](https://jrsoftware.org/isinfo.php);
pass `--no-installer` to build only the zip. Builds are not signed with a
publisher certificate, so Windows SmartScreen and macOS Gatekeeper ask users to
confirm the first launch. The self-test launches the built executable with
`--self-test`: an offscreen window, project save/reopen, generation and tracing
subprocesses, artwork Undo, and nine-format export/reopen, leaving a report in
`artifacts/bundle-self-test/`. To run the same checks from source, use
`python -m morale --self-test NEW_FOLDER`.

### Continuous integration and releases

`.github/workflows/ci.yml` runs the tests on every push: Ubuntu with Python
3.11–3.13, and Windows and macOS with Python 3.12. Failures appear as annotations
on the run; if a run is killed, the last test that started is named. Each test
has a five-minute limit.

To publish a release, update the version in `pyproject.toml` and
`morale/__init__.py`, add a `## X.Y.Z` section to [CHANGELOG.md](../CHANGELOG.md),
commit, then tag and push over SSH:

```sh
git tag -a vX.Y.Z -m "Morale X.Y.Z"
git push origin master vX.Y.Z
```

The tag triggers `.github/workflows/release.yml`. It checks that the tag matches
the package version, tests and packages on all three platforms (Linux on Ubuntu
22.04 for wider glibc compatibility), builds the Python wheel and sdist, and
publishes a GitHub Release with that changelog section, install notes, every
package and `SHA256SUMS`. Versions containing letters (`0.3.0rc1`) become
pre-releases. Running the workflow manually builds and uploads the packages as
run artifacts without publishing.

## Architecture and contributing

- `morale/model.py`: versioned project schema and editable geometry.
- `morale/engine.py`: Qt-independent geometry-to-stitch generation.
- `morale/formats.py`: pyembroidery adapters and guarded exports.
- `morale/canvas.py`: native drawing, hit testing, tools, and playback rendering.
- `morale/app.py`: main window core: previews, selection, properties, Undo, view and playback.
- `morale/window_ui.py`, `window_files.py`, `window_editing.py`, `window_artwork.py`:
  the window's menus and panels, file workflows, editing commands, and artwork,
  lettering and thread tools, as mixins of the main window.
- `morale/smooth_trace.py`, `raster_trace.py`: raster color tracing to vector regions.
- `morale/auto_digitize.py`: physical-width running/satin/fill suggestions.
- `morale/trace_dialog.py`: the conversion workspace and its cancellable worker.
- `morale/library.py`, `preview_worker.py`: design browsing and isolated decoding.
- `morale/image_benchmark.py`, `self_test.py`: internal benchmark and bundle smoke test.

Start with a reproducible example and test for engine or format changes. Preserve
millimeter units in the model; convert to tenths of millimeters only at the format
boundary. Large designs are capped at 250,000 preview commands and 500 objects.
The application entry point enables worker-based main-window previews. Internal
test/library windows can use deterministic synchronous previews; asynchronous
window tests exercise real subprocesses, cancellation and result versioning.
Pre-commit generation checks and some dialog/export workflows remain synchronous. Engine, format and
conversion modules have docstrings describing their responsibilities; about 85
modules live in `morale/`.

Morale is MIT-licensed. Dependencies retain their own licenses; see
[third-party notices](../THIRD_PARTY_NOTICES.md).

## Project documents

- [Roadmap](ROADMAP.md) and the [v1 parity ledger](V1_PARITY.md), which tracks
  evidence for every feature area.
- [Image digitizing](IMAGE_DIGITIZING.md): how artwork conversion works.
- [VP3 investigation](VP3_INVESTIGATION.md): a known export limitation.
- [Changelog](../CHANGELOG.md).
