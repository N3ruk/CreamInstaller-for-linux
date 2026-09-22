#!/usr/bin/env bash
set -euo pipefail

VERSION="1.0.0"
ARCH="x86_64"
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
BUILD="$ROOT/build/appimage"
APPDIR="$BUILD/CreamLinux.AppDir"
VENV="$BUILD/venv"
OUT="$ROOT/dist"
APPIMAGETOOL="$BUILD/appimagetool-${ARCH}.AppImage"

rm -rf "$BUILD"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib/creamlinux" "$OUT"

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -r "$ROOT/requirements.txt" pyinstaller

"$VENV/bin/pyinstaller"   --noconfirm   --clean   --onedir   --name creamlinux   --distpath "$BUILD/pyinstaller-dist"   --workpath "$BUILD/pyinstaller-build"   --specpath "$BUILD"   --add-data "$ROOT/assets:assets"   --add-data "$ROOT/creamapi:creamapi"   --add-data "$ROOT/smokeapi:smokeapi"   --add-data "$ROOT/screamapi:screamapi"   "$ROOT/creamlinux.py"

cp -a "$BUILD/pyinstaller-dist/creamlinux/." "$APPDIR/usr/lib/creamlinux/"
cat > "$APPDIR/usr/bin/creamlinux" <<'SH'
#!/bin/sh
APPDIR="${APPDIR:-$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)}"
exec "$APPDIR/usr/lib/creamlinux/creamlinux" "$@"
SH
chmod 0755 "$APPDIR/usr/bin/creamlinux"

cat > "$APPDIR/AppRun" <<'SH'
#!/bin/sh
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
export APPDIR="$HERE"
exec "$HERE/usr/bin/creamlinux" "$@"
SH
chmod 0755 "$APPDIR/AppRun"

cp "$ROOT/creamlinux.desktop" "$APPDIR/CreamLinux.desktop"
printf '\nX-AppImage-Version=%s\n' "$VERSION" >> "$APPDIR/CreamLinux.desktop"
cp "$ROOT/assets/creamlinux-dlc-unlocker.svg" "$APPDIR/creamlinux-dlc-unlocker.svg"
ln -sf creamlinux-dlc-unlocker.svg "$APPDIR/.DirIcon"

if [[ ! -x "$APPIMAGETOOL" ]]; then
  curl -fL     "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"     -o "$APPIMAGETOOL"
  chmod +x "$APPIMAGETOOL"
fi

ARCH="$ARCH" "$APPIMAGETOOL" "$APPDIR" "$OUT/CreamLinux-${VERSION}-${ARCH}.AppImage"
chmod +x "$OUT/CreamLinux-${VERSION}-${ARCH}.AppImage"
echo "$OUT/CreamLinux-${VERSION}-${ARCH}.AppImage"
