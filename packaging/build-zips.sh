#!/usr/bin/env bash
set -euo pipefail

VERSION="1.0.2"
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
OUT="$ROOT/dist"
WORK="$(mktemp -d /tmp/creamlinux-zips.XXXXXX)"
trap 'rm -rf -- "$WORK"' EXIT

copy_payload() {
  local target="$1"
  mkdir -p "$target"
  install -m 0755 "$ROOT/creamlinux.py" "$ROOT/install.sh" \
    "$ROOT/uninstall.sh" "$ROOT/run-portable.sh" "$target/"
  install -m 0644 "$ROOT/creamlinux.desktop" "$ROOT/requirements.txt" \
    "$ROOT/README.md" "$ROOT/README_ES.md" "$ROOT/CHANGELOG.md" \
    "$ROOT/RELEASE_NOTES.md" "$target/"
  cp -a "$ROOT/assets" "$ROOT/creamapi" "$ROOT/smokeapi" \
    "$ROOT/screamapi" "$target/"
}

mkdir -p "$OUT"

universal="$WORK/CreamLinux-$VERSION"
copy_payload "$universal"
(
  cd "$WORK"
  zip -X -q -r "$OUT/CreamLinux-$VERSION.zip" "CreamLinux-$VERSION"
)

steamos_root="$WORK/steamos"
steamos="$steamos_root/CreamLinux-$VERSION"
mkdir -p "$steamos_root"
copy_payload "$steamos"
install -m 0755 "$ROOT/packaging/steamos/install.sh" "$steamos/install.sh"
install -m 0755 "$ROOT/packaging/steamos/uninstall.sh" "$steamos/uninstall.sh"
install -m 0755 "$ROOT/packaging/steamos/run-portable.sh" "$steamos/run-portable.sh"
(
  cd "$steamos_root"
  zip -X -q -r "$OUT/CreamLinux-$VERSION-SteamOS.zip" "CreamLinux-$VERSION"
)

printf '%s\n' \
  "$OUT/CreamLinux-$VERSION.zip" \
  "$OUT/CreamLinux-$VERSION-SteamOS.zip"
