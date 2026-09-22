# CreamLinux v1.0.0

**First public release of CreamLinux for Linux.**

CreamLinux provides a native Qt interface for detecting Steam and Epic/Heroic/Legendary games, retrieving DLC information and managing supported DLC configuration backends while keeping original files recoverable.

## What's included

- Native **Qt 6** desktop interface.
- Detection of **Steam libraries on multiple drives** through `libraryfolders.vdf`.
- Support for native Steam and Flatpak Steam.
- Heroic / Legendary game discovery.
- Duplicate installations grouped into one game while retaining every detected route.
- CreamAPI and SmokeAPI support for Steam.
- ScreamAPI support for Epic-based installations.
- Original DLL backup and restore.
- DLC metadata lookup, local cache and persistent per-game selection.
- Easy Anti-Cheat / BattlEye titles remain visible and receive an explicit warning instead of being silently filtered.
- Proton, Steam Linux Runtime, Steamworks redistributables, Lossless Scaling and other non-game Steam entries are excluded from the game library.
- Games with no compatible target DLL remain visible with a clear status.
- New neutral DLC-unlocker desktop icon.
- Responsive interface with game artwork and compact-window scrolling.

## Downloads

Choose the package that best matches your system:

| File | Use case |
| --- | --- |
| **`CreamLinux-1.0.0-x86_64.AppImage`** | Portable build for most x86_64 Linux distributions |
| **`CreamLinux-1.0.0.deb`** | Ubuntu, Debian and compatible systems |
| **`CreamLinux-1.0.0.zip`** | Universal/source installation |
| **`CreamLinux-1.0.0-SteamOS.zip`** | SteamOS / Steam Deck optimized user-space installation |

### SteamOS / Steam Deck

The dedicated SteamOS package is intended for systems with an immutable/read-only root filesystem. It installs CreamLinux into the user's home directory and does not require disabling SteamOS read-only mode.

The AppImage can also be used directly on SteamOS when preferred.

## Quick start

### AppImage

```bash
chmod +x CreamLinux-1.0.0-x86_64.AppImage
./CreamLinux-1.0.0-x86_64.AppImage
```

### Universal / SteamOS ZIP

```bash
chmod +x install.sh
./install.sh
```

## Notes

CreamLinux modifies files inside game installations. Review the paths detected by the application before installing or restoring any configuration, particularly on games protected by anti-cheat software.

Use CreamLinux only with software and content you are authorized to modify.
