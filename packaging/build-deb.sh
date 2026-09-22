#!/usr/bin/env bash
set -euo pipefail

VERSION="1.0.0"
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
OUT="$ROOT/dist"
WORK="$(mktemp -d /tmp/creamlinux-deb.XXXXXX)"
trap 'rm -rf "$WORK"' EXIT
PKG="$WORK/creamlinux"

mkdir -p   "$PKG/DEBIAN"   "$PKG/usr/bin"   "$PKG/usr/share/CreamLinux"   "$PKG/usr/share/applications"   "$PKG/usr/share/icons/hicolor/scalable/apps"

cp "$ROOT/creamlinux.py" "$PKG/usr/share/CreamLinux/"
cp -a "$ROOT/creamapi" "$ROOT/smokeapi" "$ROOT/screamapi" "$ROOT/assets" "$PKG/usr/share/CreamLinux/"
cp "$ROOT/creamlinux.desktop" "$PKG/usr/share/applications/com.creamlinux.CreamLinux.desktop"
cp "$ROOT/assets/creamlinux-dlc-unlocker.svg" "$PKG/usr/share/icons/hicolor/scalable/apps/creamlinux-dlc-unlocker.svg"

cat > "$PKG/usr/bin/creamlinux" <<'SH'
#!/bin/sh
exec python3 /usr/share/CreamLinux/creamlinux.py "$@"
SH
chmod 0755 "$PKG/usr/bin/creamlinux" "$PKG/usr/share/CreamLinux/creamlinux.py"

cat > "$PKG/DEBIAN/control" <<EOF2
Package: creamlinux
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Maintainer: CreamLinux
Depends: python3, python3-pyqt6, python3-vdf
Description: CreamLinux native Qt desktop manager
 Native Qt desktop manager with Steam and Epic library discovery.
EOF2

cat > "$PKG/DEBIAN/postinst" <<'SH'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
exit 0
SH
cat > "$PKG/DEBIAN/postrm" <<'SH'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
exit 0
SH
chmod 0755 "$PKG/DEBIAN/postinst" "$PKG/DEBIAN/postrm"

mkdir -p "$OUT"
dpkg-deb --build --root-owner-group "$PKG" "$OUT/CreamLinux-${VERSION}.deb"
echo "$OUT/CreamLinux-${VERSION}.deb"
