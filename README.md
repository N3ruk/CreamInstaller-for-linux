# CreamLinux

Native Qt desktop manager for Steam and Epic DLC configuration on Linux.

CreamLinux scans Steam, Flatpak Steam, additional Steam libraries, Heroic and Legendary installations; groups duplicate installations under one title; detects the relevant Steam/EOS DLL locations; and provides install/restore workflows for the bundled compatibility modules.

## Features

- Native PyQt6/PySide6 interface with a compact Steam-inspired dark layout.
- Steam library discovery through `libraryfolders.vdf`, including libraries on other drives.
- Native Steam and Flatpak Steam support.
- Heroic and Legendary / Epic installation discovery.
- Duplicate game installations are grouped into one entry while retaining all detected paths.
- CreamAPI and SmokeAPI support for Steam; ScreamAPI support for Epic.
- Original DLL backup to `_o` plus restore/uninstall support.
- DLC metadata lookup and per-game selection persistence.
- Games using Easy Anti-Cheat or BattlEye remain visible and are clearly marked instead of silently disappearing.
- Proton, Steam Linux Runtime, Steamworks redistributables, Lossless Scaling and other non-game Steam components are filtered from the library.
- Responsive artwork/title layout with vertical scrolling on compact window sizes.
- Universal installer plus Debian and AppImage build recipes.

## Install

### Universal installer

```bash
chmod +x install.sh
./install.sh
```

For a system-wide install:

```bash
sudo ./install.sh --system
```

The installer supports Debian/Ubuntu, Fedora/RHEL, Arch/SteamOS, openSUSE, Alpine and other distributions with Python 3.

### Portable source launch

```bash
python3 -m pip install -r requirements.txt
./run-portable.sh
```

## Build packages

### Debian package

```bash
./packaging/build-deb.sh
```

Output:

```text
dist/creamlinux_3.0.7_all.deb
```

### AppImage (x86_64)

```bash
./packaging/build-appimage.sh
```

Output:

```text
dist/CreamLinux-3.0.7-x86_64.AppImage
```

## Uninstall

```bash
./uninstall.sh
```

For a system-wide install:

```bash
sudo ./uninstall.sh --system
```

User cache and per-game selections under `~/.local/share/CreamLinux` are intentionally preserved.

## Project layout

```text
creamlinux.py             Main application
creamlinux.desktop        Desktop integration
assets/                   Application icon
creamapi/                 CreamAPI resource location
smokeapi/                 SmokeAPI resource location
screamapi/                ScreamAPI resource location
packaging/                DEB and AppImage build scripts
install.sh                Universal installer
uninstall.sh              Uninstaller
run-portable.sh           Portable source launcher
requirements.txt          Python dependencies
CHANGELOG.md               Version history
```

## Notes

CreamLinux modifies DLL/configuration files inside game installations. Use it only on software and content you are authorized to modify. Anti-cheat protected games are detected and surfaced with an explicit warning before any modification.

Third-party compatibility components remain subject to their respective upstream projects and licenses. Their binary DLLs are intentionally not tracked in the Git repository; packaged releases contain the tested binaries used by CreamLinux.