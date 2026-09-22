# Changelog

## 3.0.7

- Full UI polish pass with flatter professional surfaces and more consistent spacing.
- Removed alternating dark table bands and eliminated opaque cell-widget backgrounds that could appear as blank black rows.
- Added explicit empty-state rows for games with no DLC metadata and installations with no compatible DLL target.
- Standardized list/table row heights, hover/selection states, borders and scrollbars.
- Replaced the Steam-derived desktop icon with a brighter neutral DLC ticket + unlocked-padlock icon.
- Added PNG and SVG icon assets for desktop/AppImage integration.
- Added an x86_64 AppImage build pipeline based on PyInstaller + the current official AppImage appimagetool.
- Added PyInstaller runtime resource-path support through `sys._MEIPASS`.

## 3.0.5

- Games are no longer silently excluded when Easy Anti-Cheat or BattlEye is detected.
- The legacy `PROTECTED_GAMES` rule is retained as a warning instead of a hard library filter.
- Protected games remain visible and receive a clear `⚠` marker in the game list.
- The details panel identifies the exact detected protection mechanism.
- Installing on a protected title now requires an explicit confirmation dialog.
- Games without a target Steam/EOS DLL remain visible and are labelled `sin DLL`; installation is disabled until a valid DLL route exists.
- DLC lookup is now allowed to run for protected titles because they are no longer discarded before metadata retrieval.

## 3.0.4

- Restored CreamLinux 2.0.0's Steam library discovery as the primary compatibility path.
- `libraryfolders.vdf` is now parsed first with the exact 2.0.0 line parser that is known to work on existing user installations.
- Removed `Path.resolve()` from Steam-library discovery; literal paths recorded by Steam are preserved for mounted, bind-mounted and symlinked libraries.
- Newer native/Flatpak Steam roots and mount probing remain supplementary and can no longer replace or suppress the 2.0.0 discovery result.
- Steam game manifests retain duplicate-title grouping, so one game can still aggregate all detected installation routes.
- Artwork and game title are now separate sibling cards with independent geometry.
- The artwork box always uses `KeepAspectRatio` and never crops the source image.
- The right details area becomes vertically scrollable when the application window is compressed.
- Added regression coverage for external `SteamLibrary` paths and duplicate installs across two libraries.

## 3.0.3

- Filters Steam compatibility tools and non-game components from the library, including Proton builds, Steam Linux Runtime, Steamworks Common Redistributables, Lossless Scaling, SteamVR, compatibility tools, dedicated servers and known runtime AppIDs.
- Groups duplicate Steam manifests into one visible game instead of showing the same title once per library/path.
- Groups duplicate Heroic/Legendary entries while retaining every valid installation directory.
- A grouped game stores every detected installation root and DLL directory found below those roots.
- Installing or restoring a grouped game applies the operation to every detected route.
- Added clearer per-route entries to operation results.
- Updated desktop metadata and DLC-related search keywords.

## 3.0.0

- Rewritten desktop UI from scratch in Qt while retaining the 2.0.0 core feature set.
- New SteamCommandGen-style visual design.
- Removed GTK3, WebKitGTK and the internal HTTP server/frontend bridge.
- Added PyQt6/PySide6 runtime compatibility.
- Added universal per-user installer and optional system-wide installer.
- Added immutable-distro-friendly installation path for SteamOS and similar systems.
- Preserved native Steam, Flatpak Steam, extra Steam libraries, Heroic and Legendary detection.
- Preserved Steam/Epic DLC metadata retrieval and caching.
- Preserved CreamAPI, SmokeAPI and ScreamAPI installation/configuration flows.
- Preserved original DLL backup and full restore logic.
- Added persistent DLC choices in `~/.local/share/CreamLinux/dlc.json`.
- Improved error handling when restoring/removing files.
