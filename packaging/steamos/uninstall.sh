#!/usr/bin/env bash
set -euo pipefail
MODE="user"
[[ "${1:-}" == "--system" ]] && MODE="system"
APP_ID="com.creamlinux.CreamLinux"
ICON_NAME="creamlinux-dlc-unlocker"

if [[ "$MODE" == "system" ]]; then
  [[ "${EUID:-$(id -u)}" -eq 0 ]] || { echo "Use sudo for --system." >&2; exit 1; }
  PREFIX="/opt/CreamLinux"
  BIN="/usr/local/bin/creamlinux"
  APP_DIR="/usr/share/applications"
  ICON_ROOT="/usr/share/icons/hicolor"
else
  PREFIX="${XDG_DATA_HOME:-$HOME/.local/share}/CreamLinux/app"
  BIN="$HOME/.local/bin/creamlinux"
  APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
  ICON_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
fi

DESKTOP="$APP_DIR/$APP_ID.desktop"
rm -rf "$PREFIX"
rm -f "$BIN" "$DESKTOP" \
  "$ICON_ROOT/512x512/apps/$ICON_NAME.png" \
  "$ICON_ROOT/scalable/apps/creamlinux.svg" \
  "$ICON_ROOT/512x512/apps/creamlinux.png"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "$ICON_ROOT" >/dev/null 2>&1 || true
fi
if command -v kbuildsycoca6 >/dev/null 2>&1; then
  kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
elif command -v kbuildsycoca5 >/dev/null 2>&1; then
  kbuildsycoca5 --noincremental >/dev/null 2>&1 || true
fi

echo "CreamLinux application removed. User cache/preferences in ~/.local/share/CreamLinux were preserved."
