#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ -x "$HERE/.venv/bin/python" ]]; then
  exec "$HERE/.venv/bin/python" "$HERE/creamlinux.py" "$@"
fi
exec python3 "$HERE/creamlinux.py" "$@"
