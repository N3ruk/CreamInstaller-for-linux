#!/usr/bin/env bash
set -euo pipefail

APP_NAME="CreamLinux"
APP_ID="com.creamlinux.CreamLinux"
ICON_NAME="creamlinux-dlc-unlocker"
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
MODE="user"

usage() {
  cat <<'USAGE'
CreamLinux universal installer

Usage:
  ./install.sh                 Install for the current user (recommended)
  ./install.sh --user          Same as above; no root required in normal cases
  sudo ./install.sh --system   Install system-wide under /opt and /usr/local/bin

Supported families: Debian/Ubuntu, Fedora/RHEL, Arch/SteamOS, openSUSE, Alpine and
other Linux distributions with Python 3. The installer prefers an already
available PyQt6/PySide6 and otherwise creates an isolated Python venv.
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --user) MODE="user" ;;
    --system) MODE="system" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; usage; exit 2 ;;
  esac
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: Python 3 is required." >&2
  exit 1
fi

run_root() {
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo "ERROR: root privileges are required to install a missing system dependency, and sudo is unavailable." >&2
    return 1
  fi
}

if [[ "$MODE" == "system" ]]; then
  [[ "${EUID:-$(id -u)}" -eq 0 ]] || { echo "Use sudo for --system." >&2; exit 1; }
  PREFIX="/opt/CreamLinux"
  BIN_DIR="/usr/local/bin"
  APP_DIR="/usr/share/applications"
  ICON_ROOT="/usr/share/icons/hicolor"
else
  PREFIX="${XDG_DATA_HOME:-$HOME/.local/share}/CreamLinux/app"
  BIN_DIR="$HOME/.local/bin"
  APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
  ICON_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
fi

ICON_512_DIR="$ICON_ROOT/512x512/apps"
DESKTOP_FILE="$APP_DIR/$APP_ID.desktop"
LAUNCHER="$BIN_DIR/creamlinux"
APP_ICON="$PREFIX/assets/$ICON_NAME.png"

printf '\nCreamLinux universal installer\n'
printf '  mode:   %s\n  prefix: %s\n\n' "$MODE" "$PREFIX"

mkdir -p "$PREFIX" "$BIN_DIR" "$APP_DIR" "$ICON_512_DIR"

# Copy application resources, excluding local build artefacts.
rm -rf "$PREFIX/creamapi" "$PREFIX/smokeapi" "$PREFIX/screamapi" "$PREFIX/assets"
install -m 0755 "$HERE/creamlinux.py" "$PREFIX/creamlinux.py"
cp -a "$HERE/creamapi" "$HERE/smokeapi" "$HERE/screamapi" "$HERE/assets" "$PREFIX/"

# Choose runtime. A distro Qt package is accepted when already present. If Qt
# is absent, use a per-app venv. This avoids toolkit package-name differences
# and works on immutable systems such as SteamOS without modifying /usr.
RUNTIME="python3"
if python3 - <<'PY' >/dev/null 2>&1
try:
    import PyQt6
except ImportError:
    import PySide6
import vdf
PY
then
  echo "✓ Found system Qt binding and vdf parser"
else
  echo "• Qt binding not found; preparing isolated runtime"
  if ! python3 -m venv "$PREFIX/.venv" >/dev/null 2>&1; then
    echo "  Python venv support is missing. Attempting distro dependency install…"
    install_venv_dependency() {
      if command -v apt-get >/dev/null 2>&1; then
        run_root apt-get update && run_root apt-get install -y python3-venv python3-pip
      elif command -v dnf >/dev/null 2>&1; then
        run_root dnf install -y python3-pip
      elif command -v pacman >/dev/null 2>&1; then
        run_root pacman -S --needed --noconfirm python python-pip
      elif command -v zypper >/dev/null 2>&1; then
        run_root zypper --non-interactive install python3-pip python3-virtualenv
      elif command -v apk >/dev/null 2>&1; then
        run_root apk add python3 py3-pip py3-virtualenv py3-pyqt6
      else
        return 1
      fi
    }
    install_venv_dependency || {
      echo "ERROR: Could not create a Python virtual environment." >&2
      exit 1
    }
    python3 -m venv "$PREFIX/.venv"
  fi
  "$PREFIX/.venv/bin/python" -m pip install --upgrade pip >/dev/null
  if "$PREFIX/.venv/bin/python" -m pip install PyQt6 vdf; then
    RUNTIME="$PREFIX/.venv/bin/python"
    echo "✓ Installed PyQt6 + vdf inside the application runtime"
  else
    echo "  PyPI Qt installation failed; trying the distro's native Qt package…"
    rm -rf "$PREFIX/.venv"
    if command -v apt-get >/dev/null 2>&1; then
      run_root apt-get update && run_root apt-get install -y python3-pyqt6
    elif command -v dnf >/dev/null 2>&1; then
      run_root dnf install -y python3-qt6
    elif command -v pacman >/dev/null 2>&1; then
      run_root pacman -S --needed --noconfirm python-pyqt6
    elif command -v apk >/dev/null 2>&1; then
      run_root apk add py3-pyqt6
    else
      echo "ERROR: no compatible Qt runtime could be installed automatically." >&2
      exit 1
    fi
    RUNTIME="python3"
  fi
fi

# The launcher stores the resolved runtime path. This is important on SteamOS:
# Plasma does not have to know about the venv and does not need ~/.local/bin in
# its PATH in order to start the application from the desktop/menu entry.
cat > "$LAUNCHER" <<EOF_LAUNCHER
#!/usr/bin/env bash
set -e
exec "$RUNTIME" "$PREFIX/creamlinux.py" "\$@"
EOF_LAUNCHER
chmod 0755 "$LAUNCHER"

# Install the supplied PNG unchanged. The desktop entry below points directly
# to it to avoid stale/missing KDE icon-theme resolution on SteamOS.
install -m 0644 "$HERE/assets/$ICON_NAME.png" "$ICON_512_DIR/$ICON_NAME.png"

# Generate the desktop entry with absolute launcher/icon paths. Using
# Exec=creamlinux is unreliable on SteamOS because Plasma may not inherit
# ~/.local/bin in PATH even though the terminal does.
cat > "$DESKTOP_FILE" <<EOF_DESKTOP
[Desktop Entry]
Name=CreamLinux
Comment=Manage and unlock DLC for Steam and Epic games
Comment[es]=Gestiona y desbloquea DLC para juegos de Steam y Epic
Exec="$LAUNCHER"
TryExec=$LAUNCHER
Icon=$APP_ICON
Terminal=false
Type=Application
Categories=Game;Utility;
Keywords=Steam;Epic;DLC;CreamAPI;SmokeAPI;ScreamAPI;
StartupNotify=true
StartupWMClass=CreamLinux
EOF_DESKTOP
chmod 0644 "$DESKTOP_FILE"

# Refresh the desktop databases/caches when the host provides the helpers.
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

printf '\n✓ CreamLinux installed.\n'
printf '  Launcher: %s\n' "$LAUNCHER"
printf '  Desktop:  %s\n' "$DESKTOP_FILE"
printf '  Icon:     %s\n' "$APP_ICON"
if [[ "$MODE" == "user" && ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
  printf '  NOTE: ~/.local/bin is not in this terminal PATH, but the desktop entry uses an absolute launcher path and will still work.\n'
fi
