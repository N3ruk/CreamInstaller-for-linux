# CreamLinux v1.0.2

Performance-only update for game scanning, searching and artwork loading.
The existing UI, game discovery rules and DLC installation/restoration logic
are retained. Window and taskbar icons match the blue DLC launcher icon.

## Improvements

- Four concurrent game-scan workers instead of serial library processing.
- Shared DLC lookup pool; at most four Steam/Epic metadata requests in flight.
- Reuse directory walks and DLL hashes per scan, including filesystem aliases,
  while preserving all original installation paths.
- Hash immutable bundled compatibility resources once per process.
- Asynchronous artwork: slow CDNs no longer block typing or game selection.
- Filtering retains the unchanged selected-game panel instead of recreating
  its DLC controls at every keystroke.

Metadata cache durations, fallback behavior, DLC ordering, installation
backups, selections and bundled compatibility DLLs remain unchanged.
No fixed speedup percentage is claimed: timings depend on library size,
storage, cache state and store availability.

## Packages

| Download | Target |
| --- | --- |
| `CreamLinux-1.0.2-SteamOS.zip` | SteamOS/Steam Deck, user-space installation |
| `CreamLinux-1.0.2-x86_64.AppImage` | Portable x86_64 Linux build |
| `CreamLinux-1.0.2.deb` | Debian/Ubuntu and compatible distributions |
| `CreamLinux-1.0.2.zip` | Universal/source installation |
| `SHA256SUMS` | Checksums for all four packages |

SteamOS: extract the ZIP and run `bash install.sh`. Installation stays in the
user's home directory; read-only system and startup settings are untouched.
Existing metadata and DLC selections are retained.

Compatibility DLLs are byte-identical to v1.0.1. Third-party components retain
their upstream licensing. Use only with software/content you may modify.
