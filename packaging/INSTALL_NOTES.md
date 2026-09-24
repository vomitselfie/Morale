
### Downloads

| Platform | File | Notes |
| --- | --- | --- |
| Windows 10/11 (64-bit) | `…-windows-x86_64-setup.exe` | Installer. Windows SmartScreen may warn that the publisher is unknown: choose **More info → Run anyway**. A portable zip is also provided. |
| macOS 12+ (Apple silicon) | `…-macos-arm64.dmg` | Drag Morale to Applications. The app is not notarized: the first time, right-click it and choose **Open**, or allow it under **System Settings → Privacy & Security**. |
| Linux (x86_64) | `…-linux-x86_64.AppImage` | `chmod +x` the file and run it. The tar.gz holds the same app plus desktop-entry files under `share/`. |
| Python | `…whl` / `…tar.gz` | `pip install` the wheel, then run `morale`. |

Verify downloads against `SHA256SUMS`. Morale is pre-1.0 and its stitch output has
not been validated by physical sew-outs: test on scrap fabric first.
