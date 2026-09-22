# CreamLinux

**CreamLinux** is a native Qt desktop manager for Linux that detects installed Steam and Epic/Heroic/Legendary games, retrieves their DLC metadata, groups duplicate installations, and manages supported DLC configuration backends from a single interface.

It is designed around a simple goal: **show the real game library clearly, detect every valid installation path, and make configuration/recovery predictable.**

## Highlights

- **Multi-library Steam detection** through `libraryfolders.vdf`, including libraries stored on additional drives.
- Supports **native Steam** and **Flatpak Steam** installations.
- Detects games installed through **Heroic** and **Legendary**.
- Duplicate installations of the same game are shown as **one entry**, while retaining every detected path.
- Filters non-game Steam entries such as Proton, Steam Linux Runtime, Steamworks redistributables and Lossless Scaling.
- Games using **Easy Anti-Cheat** or **BattlEye** remain visible and are clearly marked instead of being silently excluded.
- Games without a compatible target DLL also remain visible with an explicit status.
- Supports **CreamAPI**, **SmokeAPI** and **ScreamAPI** workflows.
- Original DLLs are backed up before replacement and can be restored from the application.
- DLC metadata is cached locally and per-game selections are remembered.
- Native **PyQt6 / PySide6** interface with artwork, search, filters and compact responsive layouts.

## Downloads

Use the **GitHub Releases** page for packaged builds.

| Package | Recommended for |
| --- | --- |
| `CreamLinux-1.0.0-x86_64.AppImage` | Most x86_64 Linux distributions — portable, no installation required |
| `CreamLinux-1.0.0.deb` | Ubuntu, Debian and compatible distributions |
| `CreamLinux-1.0.0.zip` | Universal/source installation on Linux |
| `CreamLinux-1.0.0-SteamOS.zip` | SteamOS / Steam Deck — user-space installation without modifying the immutable system |

## Compatibility

CreamLinux is intended to work on modern Linux distributions with Python 3 and Qt 6, including:

- Ubuntu / Debian
- Fedora / RHEL-based distributions
- Arch Linux
- SteamOS / Steam Deck
- openSUSE
- Alpine Linux
- Other distributions able to provide PyQt6 or PySide6

### SteamOS

For SteamOS, use either the **AppImage** or the dedicated **SteamOS ZIP**.

The SteamOS package installs into the user's home directory and does **not** require disabling the read-only root filesystem.

## Universal installation

Extract `CreamLinux-1.0.0.zip` and run:

```bash
chmod +x install.sh
./install.sh
```

For a system-wide installation:

```bash
sudo ./install.sh --system
```

## SteamOS installation

Extract `CreamLinux-1.0.0-SteamOS.zip` and run:

```bash
chmod +x install.sh
./install.sh
```

The installation remains under the current user's home directory so SteamOS system updates do not depend on modifications to the immutable root filesystem.

## AppImage

```bash
chmod +x CreamLinux-1.0.0-x86_64.AppImage
./CreamLinux-1.0.0-x86_64.AppImage
```

## Portable source launch

```bash
python3 -m pip install -r requirements.txt
./run-portable.sh
```

## Build packages

Build the Debian package:

```bash
./packaging/build-deb.sh
```

Build the x86_64 AppImage:

```bash
./packaging/build-appimage.sh
```

## Project layout

```text
creamlinux.py             Main application
creamlinux.desktop        Desktop integration
assets/                   Application icon and visual assets
creamapi/                 CreamAPI resource directory
smokeapi/                 SmokeAPI resource directory
screamapi/                ScreamAPI resource directory
packaging/                DEB and AppImage build scripts
install.sh                Universal installer
uninstall.sh              Uninstaller
run-portable.sh           Portable source launcher
requirements.txt          Python dependencies
CHANGELOG.md              Version history
RELEASE_NOTES.md          Current public release notes
```

## Uninstall

User installation:

```bash
./uninstall.sh
```

System-wide installation:

```bash
sudo ./uninstall.sh --system
```

CreamLinux intentionally preserves its user data and cache directory under:

```text
~/.local/share/CreamLinux
```

## Important notes

CreamLinux modifies DLL and configuration files inside game installations. Always review the detected game paths before applying changes, especially on titles using anti-cheat software.

Use CreamLinux only with software and content you are authorized to modify.

Third-party compatibility components remain subject to their respective upstream projects and licenses.
