# Package build and performance architecture

## v1.0.2 runtime

`creamlinux.py` remains a single native Qt application. Discovery and VDF
parsers are unchanged. `ScanWorker` calls `scan_games()` outside the UI thread.
Four game workers share a per-scan `ScanCache` and a separate four-worker DLC
pool. `executor.map` retains input ordering; final game sorting is unchanged.
A semaphore bounds all store metadata requests to four simultaneous requests;
striped locks protect cache/cooldown transactions for shared AppIDs/namespaces.

Directory-cache keys use filesystem identity plus platform. Relative results
are projected onto each original installation path, not canonicalized in the
UI. Hash keys include identity, size, mtime and ctime. The cache is discarded
after each scan, so later scans see newly installed/moved DLLs. Only immutable
bundled DLL hashes are cached for the process lifetime.

Filtering does not render the unchanged selected game's panel again. Artwork
uses `QNetworkAccessManager`, retaining both CDN fallbacks and the disk cache.
Only one artwork request is active; switching games aborts the old request.
After both hosts fail, that image can be retried after the next scan.

## Release build

Formats: universal ZIP, SteamOS ZIP, Debian package and x86_64 AppImage.
Align version metadata in `creamlinux.py`, three `build-*.sh` scripts, public
READMEs, changelog and release notes.

Compatibility DLLs are gitignored. Obtain the six DLLs from the preceding
trusted release after checking its asset SHA256. Do not upgrade backends in a
performance-only release.

Use Ubuntu 22.04 rather than freezing against a newer host glibc:

```sh
podman build -t localhost/creamlinux-build:ubuntu22 -f packaging/Containerfile .
podman run --rm --memory=3g --memory-swap=4g --cpus=2 \
  -v "$PWD:/src" localhost/creamlinux-build:ubuntu22 \
  bash -c 'bash packaging/build-zips.sh && bash packaging/build-deb.sh && bash packaging/build-appimage.sh'
```

Outputs go to `dist/`. AppImage creation needs network access for Python
dependencies and appimagetool. Extraction-based AppImage execution avoids a
host FUSE dependency. This is not a bit-reproducible build claim: dependencies
and the tool's continuous channel remain floating.

Generate SHA256SUMS from the four outputs and copy it to the repository.
Publish the tag against the exact committed main SHA; never replace old
releases. Redownload all five assets and compare with the local hashes.

Before local SteamOS installation, back up the existing app payload, launcher
and desktop entry privately. Preserve metadata, caches and `dlc.json`. Never
invoke DLC install/restore actions merely to inspect performance.
