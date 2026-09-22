# CreamLinux

CreamLinux is a native Qt desktop application for Linux that discovers Steam and Epic/Heroic/Legendary game installations, groups duplicate installs, retrieves DLC metadata, and manages the supported DLC configuration backends from one interface.

## Features

- Detects native Steam, Flatpak Steam, and additional Steam libraries from `libraryfolders.vdf`.
- Groups the same game found in multiple libraries and processes all detected routes in one operation.
- Filters Proton, Steam Linux Runtime, Steamworks redistributables, Lossless Scaling, and other non-game Steam components.
- Keeps Easy Anti-Cheat/BattlEye titles visible and warns before changes instead of silently hiding them.
- Keeps games with no compatible target DLL visible and reports the missing target.
- Supports CreamAPI and SmokeAPI for Steam and ScreamAPI for Epic/Heroic/Legendary.
- Backs up original DLLs using the `_o` suffix and supports restoration.
- Retrieves and caches DLC metadata and remembers per-game selections.
- Native PyQt6/PySide6 interface with game artwork, search/filtering, explicit status states, and multi-library support.

## Downloads

The first public release is **v1.0.0**. Packaged artifacts use these filenames:

- `CreamLinux-1.0.0-x86_64.AppImage` — portable x86_64 build.
- `CreamLinux-1.0.0.deb` — Debian/Ubuntu package.
- `CreamLinux-1.0.0.zip` — universal source package and installer.

## Universal installation

```bash
chmod +x install.sh
./install.sh
```

System-wide:

```bash
sudo ./install.sh --system
```

The installer supports Debian/Ubuntu, Fedora/RHEL, Arch/SteamOS, openSUSE, Alpine, and other distributions with Python 3.

## Portable source launch

```bash
python3 -m pip install -r requirements.txt
./run-portable.sh
```

## Build packages

Debian package:

```bash
./packaging/build-deb.sh
```

AppImage x86_64:

```bash
./packaging/build-appimage.sh
```

## Uninstall

```bash
./uninstall.sh
```

System-wide:

```bash
sudo ./uninstall.sh --system
```

The uninstaller intentionally preserves `~/.local/share/CreamLinux`.

## Notes

CreamLinux modifies files inside game installations. Review detected paths before applying changes, especially for games using anti-cheat software. Use only with software and content you are authorized to modify.

Third-party compatibility components remain subject to their respective upstream projects and licenses. Packaged releases contain the tested resource binaries used by CreamLinux.
