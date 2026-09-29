#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

# Local portable runtime, if one was explicitly prepared beside the sources.
if [[ -x "$HERE/.venv/bin/python" ]]; then
  exec "$HERE/.venv/bin/python" "$HERE/creamlinux.py" "$@"
fi

# If CreamLinux was installed for this user, always use its launcher/runtime.
# This prevents accidentally running creamlinux.py with SteamOS' global Python,
# which does not contain the PyQt6 installed in CreamLinux's isolated venv.
if [[ -x "$HOME/.local/bin/creamlinux" ]]; then
  exec "$HOME/.local/bin/creamlinux" "$@"
fi

# Last resort: only use system Python if all required modules are really there.
if python3 - <<'PY' >/dev/null 2>&1
try:
    import PyQt6
except ImportError:
    import PySide6
import vdf
PY
then
  exec python3 "$HERE/creamlinux.py" "$@"
fi

echo "CreamLinux portable runtime is not configured." >&2
echo "Run ./install.sh first, then launch CreamLinux from the application menu or with ~/.local/bin/creamlinux." >&2
exit 1
