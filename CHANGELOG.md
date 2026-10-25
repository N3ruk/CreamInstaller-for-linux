# Changelog

## 1.0.2 — Search and scanning performance

- Scan games concurrently with four workers and a shared DLC lookup pool;
  limit Steam/Epic metadata traffic to four simultaneous requests.
- Reuse filesystem walks and game DLL hashes within each scan, including
  symlink aliases, without changing detected installation paths.
- Hash bundled DLLs once per process instead of rereading them per game.
- Download artwork asynchronously through Qt and cancel obsolete requests.
- Keep the unchanged selected-game panel while filtering; avoid redundant
  DLC-widget rebuilding and intermediate list repaints on every keystroke.
- Match the definitive red DLC launcher icon in the window, taskbar and packages.
- No layout, discovery-rule, DLC-selection, installation/restoration or
  compatibility-binary changes.

## 1.0.1 — Icon refresh

- Replaced the application, launcher and package icon with the definitive
  CreamLinux PNG supplied by the project owner.
- Standardized the fourth release artifact as the SteamOS package, replacing
  the temporary `SteamOS-hotfix` label while preserving its launcher fixes.
- No application logic or DLC-management behavior changed.

## 1.0.0 — First public release

- Native Qt 6 interface with a polished responsive layout.
- Steam library discovery through `libraryfolders.vdf`, including additional drives and Flatpak Steam.
- Heroic / Legendary game discovery.
- Duplicate game installations grouped into one visible entry while retaining every detected path.
- CreamAPI and SmokeAPI support for Steam; ScreamAPI support for Epic.
- Original DLL backup and restore workflows.
- DLC metadata lookup, caching and persistent per-game selections.
- Proton, Steam Linux Runtime, Steamworks redistributables, Lossless Scaling and other non-game Steam entries filtered from the library.
- Easy Anti-Cheat and BattlEye titles remain visible with explicit warnings.
- Games without a compatible target DLL remain visible with a clear status.
- Neutral DLC-unlocker desktop icon with no Steam branding.
- Universal installer, Debian package builder and x86_64 AppImage builder.
- Dedicated SteamOS distribution option for user-space installation on immutable SteamOS systems.
