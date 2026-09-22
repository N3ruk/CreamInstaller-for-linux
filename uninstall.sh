#!/usr/bin/env bash
set -euo pipefail
MODE="user"
[[ "${1:-}" == "--system" ]] && MODE="system"
APP_ID="com.creamlinux.CreamLinux"
if [[ "$MODE" == "system" ]]; then
  [[ "${EUID:-$(id -u)}" -eq 0 ]] || { echo "Use sudo for --system." >&2; exit 1; }
  PREFIX="/opt/CreamLinux"
  BIN="/usr/local/bin/creamlinux"
  DESKTOP="/usr/share/applications/$APP_ID.desktop"
  ICON="/usr/share/icons/hicolor/scalable/apps/creamlinux-dlc-unlocker.svg"
  OLD_ICON="/usr/share/icons/hicolor/scalable/apps/creamlinux.svg"
else
  PREFIX="${XDG_DATA_HOME:-$HOME/.local/share}/CreamLinux/app"
  BIN="$HOME/.local/bin/creamlinux"
  DESKTOP="${XDG_DATA_HOME:-$HOME/.local/share}/applications/$APP_ID.desktop"
  ICON="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps/creamlinux-dlc-unlocker.svg"
  OLD_ICON="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps/creamlinux.svg"
fi
rm -rf "$PREFIX"
rm -f "$BIN" "$DESKTOP" "$ICON" "$OLD_ICON"
echo "CreamLinux application removed. User cache/preferences in ~/.local/share/CreamLinux were preserved."
