#!/usr/bin/env python3
"""
CreamLinux 1.0.0
Native Qt rewrite of CreamLinux 2.x.

Functional scope retained from 2.0.0:
- Scan Steam libraries (native + Flatpak + additional libraryfolders.vdf)
- Scan Heroic / Legendary Epic installations
- Locate Steam / EOS SDK DLL directories recursively
- Detect existing CreamAPI / SmokeAPI / ScreamAPI installs
- Query and cache Steam / Epic DLC metadata
- Select DLC per game and persist selection
- Install bundled unlocker DLLs while backing up originals
- Generate CreamAPI / SmokeAPI / ScreamAPI configuration
- Restore original DLLs and remove generated configuration
- Open detected DLL directories in the desktop file manager

The 1.0.0 UI is fully native Qt and does not use an embedded web browser or local HTTP server.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import urllib.request

try:
    import vdf as steam_vdf
except ImportError:
    steam_vdf = None
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

VERSION = "1.0.0"
APP_NAME = "CreamLinux"
APP_ID = "com.creamlinux.CreamLinux"

# -----------------------------------------------------------------------------
# Qt binding compatibility: prefer PyQt6, allow PySide6 as a distro-friendly
# fallback. The application code below uses only APIs common to both bindings.
# -----------------------------------------------------------------------------
QT_BINDING = None
try:
    from PyQt6.QtCore import Qt, QThread, pyqtSignal as Signal, QSize
    from PyQt6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPalette, QPixmap
    from PyQt6.QtCore import QUrl
    from PyQt6.QtWidgets import (
        QApplication, QAbstractItemView, QButtonGroup, QCheckBox, QDialog,
        QDialogButtonBox, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
        QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
        QScrollArea, QSizePolicy, QSplitter, QStackedWidget, QStatusBar,
        QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
    )
    QT_BINDING = "PyQt6"
except ImportError:
    try:
        from PySide6.QtCore import Qt, QThread, Signal, QSize, QUrl
        from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPalette, QPixmap
        from PySide6.QtWidgets import (
            QApplication, QAbstractItemView, QButtonGroup, QCheckBox, QDialog,
            QDialogButtonBox, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
            QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
            QScrollArea, QSizePolicy, QSplitter, QStackedWidget, QStatusBar,
            QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
        )
        QT_BINDING = "PySide6"
    except ImportError:
        print(
            "CreamLinux requires PyQt6 or PySide6. Run ./install.sh so the "
            "portable installer can configure the Qt dependency.",
            file=sys.stderr,
        )
        raise


SCRIPT_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
CREAMAPI_DIR = SCRIPT_DIR / "creamapi"
SMOKEAPI_DIR = SCRIPT_DIR / "smokeapi"
SCREAMAPI_DIR = SCRIPT_DIR / "screamapi"
ASSETS_DIR = SCRIPT_DIR / "assets"

HOME = Path.home()
DATA_DIR = HOME / ".local" / "share" / "CreamLinux"
APPINFO_DIR = DATA_DIR / "appinfo"
COOLDOWN_DIR = DATA_DIR / "cooldown"
DLC_CHOICES = DATA_DIR / "dlc.json"
IMAGE_CACHE_DIR = DATA_DIR / "images"

STEAM_ROOTS = [
    HOME / ".steam" / "steam",
    HOME / ".steam" / "root",
    HOME / ".local" / "share" / "Steam",
    HOME / ".var" / "app" / "com.valvesoftware.Steam" / ".steam" / "steam",
    HOME / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
    HOME / ".var" / "app" / "com.valvesoftware.Steam" / "data" / "Steam",
    Path("/usr/share/steam"),
]

# Exact root order used by CreamLinux 2.0.0.  This is kept as the primary
# discovery path because it is known to work correctly on existing installs.
LEGACY_STEAM_ROOTS = [
    HOME / ".steam" / "steam",
    HOME / ".local" / "share" / "Steam",
    HOME / ".var" / "app" / "com.valvesoftware.Steam" / ".steam" / "steam",
    Path("/usr/share/steam"),
]
EPIC_HEROIC_PATHS = [
    HOME / ".config" / "heroic",
    HOME / ".var" / "app" / "com.heroicgameslauncher.hgl" / "config" / "heroic",
]
LEGENDARY_INSTALLED = HOME / ".config" / "legendary" / "installed.json"

PROTECTED_GAMES = {"PAYDAY 2"}
PROTECTED_SUBDIRS = ["EasyAntiCheat", "BattlEye"]

SMOKEAPI_MD5S = {
    "B2434578957CBE38BDCE0A671C1262FC",
    "973AB1632B747D4BF3B2666F32E34327",
    "E833ACE855245D5939EE36FF25D8B4A4",
    "A2728FC65BFF3305F43F87CB6E3AE448",
    "2B2413E3CCDA93C3821711D089129D34",
}
CREAMAPI_MD5S = {
    "23909B4B1C7A182A6596BD0FDF2BFC7C",
    "E6DDF91F4419BE471FBE126A0966648B",
    "7B052096931080FDC7E10FB9BCE25177",
    "10638F7AC4E18DDBFA533EB6F307AE9E",
    "B14007170E59B03D5DF844BD3457295B",
    "24C712826D939F5CEC9049D4B94FCBDB",
}
SCREAMAPI_MD5S = {
    "069A57B1834A960193D2AD6B96926D70",
    "E2FB3A4A9583FDC215832E5F935E4440",
    "2F98D62283AA024CBD756921B9533489",
    "CBC89E2221713B0D4482F91282030A88",
}

STEAM_DLL_NAMES = {
    "steam_api.dll", "steam_api64.dll", "steam_api_o.dll", "steam_api64_o.dll"
}
EPIC_DLL_NAMES = {
    "EOSSDK-Win32-Shipping.dll", "EOSSDK-Win64-Shipping.dll",
    "EOSSDK-Win32-Shipping_o.dll", "EOSSDK-Win64-Shipping_o.dll",
}
SKIP_DIRS = {
    "__macosx", ".git", "redist", "directx", "vcredist", "physx", "dotnetfx", "setup"
}

# Steam installs a number of compatibility tools and shared runtimes alongside
# games. They have appmanifest files too, so a manifest-only scanner must filter
# them explicitly or they appear as if they were games. Keep both known AppIDs
# and name-based rules because Valve can publish newer Proton/runtime AppIDs.
STEAM_NON_GAME_APP_IDS = {
    "228980",   # Steamworks Common Redistributables
    "250820",   # SteamVR
    "858280",   # Proton 3.x
    "930400",   # Proton 3.x
    "993090",   # Lossless Scaling
    "1054830",  # Proton 4.x
    "1113280",  # Proton 4.x
    "1070560",  # Steam Linux Runtime
    "1245040",  # Proton 5.x
    "1391110",  # Steam Linux Runtime - Soldier
    "1420170",  # Proton 5.x
    "1493710",  # Proton Experimental
    "1580130",  # Proton 6.x
    "1628350",  # Steam Linux Runtime - Sniper
    "1887720",  # Proton 7.x
    "2180100",  # Proton Hotfix
    "2348590",  # Proton 8.x
    "2805730",  # Proton 9.x
}

STEAM_NON_GAME_NAME_PATTERNS = (
    r"^proton(?:\s|$|-)",
    r"steam\s+linux\s+runtime",
    r"steamworks(?:\s+common)?\s+redistributables?",
    r"steamworks\s+sdk",
    r"^lossless\s+scaling$",
    r"pressure[- ]vessel",
    r"^steam\s+runtime",
    r"^steamvr$",
    r"dedicated\s+server",
    r"redistributable",
    r"compatibility\s+tool",
)


def normalize_game_title(name: str) -> str:
    """Stable title key used to collapse duplicate manifests/installations."""
    value = name.casefold().strip()
    value = value.replace("™", "").replace("®", "")
    value = re.sub(r"\s+", " ", value)
    return value


def is_steam_non_game(app_id: str, name: str, installdir: str = "") -> bool:
    app_id = str(app_id or "")
    if app_id in STEAM_NON_GAME_APP_IDS:
        return True
    values = (str(name or "").strip(), str(installdir or "").strip())
    for pattern in STEAM_NON_GAME_NAME_PATTERNS:
        if any(re.search(pattern, value, re.IGNORECASE) for value in values if value):
            return True
    return False


def game_install_dirs(game: dict) -> List[Path]:
    """Return every installation root represented by one grouped game."""
    raw = game.get("directories") or ([game.get("directory")] if game.get("directory") else [])
    result: List[Path] = []
    seen: set[str] = set()
    for value in raw:
        if not value:
            continue
        path = Path(value)
        key = str(path)
        if key not in seen:
            result.append(path)
            seen.add(key)
    return result


def game_dll_dirs(game: dict) -> List[str]:
    """Return cached DLL directories or discover them across every install root."""
    cached = list(game.get("dllDirs") or [])
    if cached:
        return list(dict.fromkeys(cached))
    found: List[str] = []
    for install_dir in game_install_dirs(game):
        for directory in find_dll_dirs(install_dir, game["platform"]):
            if directory not in found:
                found.append(directory)
    return found


def ensure_dirs() -> None:
    for directory in (DATA_DIR, APPINFO_DIR, COOLDOWN_DIR, IMAGE_CACHE_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def md5_file(path: Path) -> Optional[str]:
    try:
        h = hashlib.md5()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                h.update(chunk)
        return h.hexdigest().upper()
    except Exception:
        return None


@lru_cache(maxsize=1)
def bundled_unlocker_hashes() -> set[str]:
    """Include hashes of the DLLs actually bundled with this build.

    2.0.0 had several bundled binaries whose hashes were absent from its static
    MD5 lists. Including the local resource hashes prevents a reinstall from
    mistaking its own replacement DLL for an original DLL and backing it up.
    """
    hashes: set[str] = set()
    for folder in (CREAMAPI_DIR, SMOKEAPI_DIR, SCREAMAPI_DIR):
        if not folder.is_dir():
            continue
        for file in folder.glob("*.dll"):
            value = md5_file(file)
            if value:
                hashes.add(value)
    return hashes


def is_any_unlocker(path: Path) -> bool:
    value = md5_file(path)
    if not value:
        return False
    return value in (CREAMAPI_MD5S | SMOKEAPI_MD5S | SCREAMAPI_MD5S | bundled_unlocker_hashes())


def check_cooldown(identifier: str, seconds: int) -> bool:
    marker = COOLDOWN_DIR / f"{identifier}.txt"
    now = time.time()
    if marker.exists():
        try:
            last = float(marker.read_text().strip())
            if now - last < seconds:
                return False
        except Exception:
            pass
    try:
        marker.write_text(str(now))
    except Exception:
        pass
    return True


def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def write_json(path: Path, data) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception:
        pass


def detect_protections(name: str, directory: Path) -> List[str]:
    """Return protection warnings without hiding the game from the library.

    CreamLinux 2.x used this information as a hard exclusion. 3.0.5 keeps the
    detection, but surfaces the title and warns before any modification.
    """
    warnings: List[str] = []
    if str(name or "").casefold() in {item.casefold() for item in PROTECTED_GAMES}:
        warnings.append("Bloqueo heredado de CreamLinux")

    try:
        child_names = {child.name.casefold(): child.name for child in directory.iterdir() if child.is_dir()}
    except Exception:
        child_names = {}

    labels = {
        "easyanticheat": "Easy Anti-Cheat",
        "battleye": "BattlEye",
    }
    for sub in PROTECTED_SUBDIRS:
        key = sub.casefold()
        if key in child_names:
            label = labels.get(key, child_names[key])
            if label not in warnings:
                warnings.append(label)
    return warnings


def is_blocked(name: str, directory: Path) -> bool:
    """Compatibility helper retained for external callers; no longer filters UI."""
    return bool(detect_protections(name, directory))


def get_pe_bits(path: Path) -> Optional[int]:
    try:
        with path.open("rb") as f:
            if f.read(2) != b"MZ":
                return None
            f.seek(0x3C)
            pe_offset = struct.unpack("<I", f.read(4))[0]
            f.seek(pe_offset)
            if f.read(4) != b"PE\x00\x00":
                return None
            machine = struct.unpack("<H", f.read(2))[0]
            return 64 if machine in (0x8664, 0x0200) else 32
    except Exception:
        return None




def get_elf_bits(path: Path) -> Optional[int]:
    """Return 32/64 for ELF binaries; retained from 2.0 for diagnostics."""
    try:
        with path.open("rb") as f:
            magic = f.read(5)
            if magic[:4] != b"\x7fELF":
                return None
            return 64 if magic[4] == 2 else 32
    except Exception:
        return None


def detect_bits_in_dir(directory: str) -> List[int]:
    """Return PE bitnesses found in a DLL/EXE directory (2.0 compatibility)."""
    bits: set[int] = set()
    path = Path(directory)
    try:
        for file in path.iterdir():
            if file.suffix.lower() in (".dll", ".exe"):
                value = get_pe_bits(file)
                if value:
                    bits.add(value)
            if bits == {32, 64}:
                break
    except Exception:
        pass
    return sorted(bits)

def dll_available(unlocker: str, bits: int) -> bool:
    path = get_dll_path(unlocker, bits)
    return path is not None and path.exists()


def get_dll_path(unlocker: str, bits: int) -> Optional[Path]:
    mapping = {
        ("creamapi", 32): CREAMAPI_DIR / "steam_api.dll",
        ("creamapi", 64): CREAMAPI_DIR / "steam_api64.dll",
        ("smokeapi", 32): SMOKEAPI_DIR / "steam_api.dll",
        ("smokeapi", 64): SMOKEAPI_DIR / "steam_api64.dll",
        ("screamapi", 32): SCREAMAPI_DIR / "EOSSDK-Win32-Shipping.dll",
        ("screamapi", 64): SCREAMAPI_DIR / "EOSSDK-Win64-Shipping.dll",
    }
    return mapping.get((unlocker.lower(), bits))


# -----------------------------------------------------------------------------
# Steam / Epic scanners
# -----------------------------------------------------------------------------
def find_steam_root_legacy() -> Optional[Path]:
    """Exact CreamLinux 2.0.0 Steam-root selection."""
    for directory in LEGACY_STEAM_ROOTS:
        if directory.is_dir():
            return directory
    return None


def find_steam_root() -> Optional[Path]:
    # Preserve 2.0.0 behaviour first; extended roots are fallback only.
    legacy = find_steam_root_legacy()
    if legacy:
        return legacy
    roots = get_steam_roots()
    return roots[0] if roots else None


def get_steam_roots() -> List[Path]:
    """Return every plausible Steam root without resolving symlinks.

    CreamLinux 3.0.2/3.0.3 resolved paths before scanning.  2.0.0 did not, so
    3.0.4+ deliberately keeps Steam's literal paths.  This matters with mounted,
    bind-mounted and symlinked libraries.
    """
    result: List[Path] = []
    seen: set[str] = set()
    for root in STEAM_ROOTS:
        key = os.path.normpath(os.path.abspath(os.path.expanduser(str(root))))
        if (root / "steamapps").is_dir() and key not in seen:
            result.append(root)
            seen.add(key)
    return result


def discover_additional_steamapps() -> List[Path]:
    """Supplementary discovery only; libraryfolders.vdf remains authoritative."""
    user = os.environ.get("USER", "")
    bases = [
        Path("/mnt"),
        Path("/media"),
        Path("/run/media") / user if user else Path("/run/media"),
    ]
    result: List[Path] = []
    seen: set[str] = set()

    def add(path: Path):
        key = os.path.normpath(os.path.abspath(os.path.expanduser(str(path))))
        if path.is_dir() and key not in seen:
            result.append(path)
            seen.add(key)

    def inspect_base(base: Path):
        if not base.is_dir():
            return
        for candidate in (
            base / "steamapps",
            base / "SteamLibrary" / "steamapps",
            base / "steamlibrary" / "steamapps",
        ):
            add(candidate)
        try:
            for child in base.iterdir():
                if not child.is_dir():
                    continue
                for candidate in (
                    child / "steamapps",
                    child / "SteamLibrary" / "steamapps",
                    child / "steamlibrary" / "steamapps",
                    child / ".steam" / "steam" / "steamapps",
                ):
                    add(candidate)
        except OSError:
            return

    for base in bases:
        inspect_base(base)
    return result


def parse_vdf_legacy(text: str) -> dict:
    """The parser from CreamLinux 2.0.0, kept byte-for-byte in behaviour."""
    result = {}
    stack = [result]
    current = result
    for line in text.splitlines():
        line = line.strip()
        match = re.match(r'^"([^"]+)"\s+"([^"]*)"', line)
        if match:
            current[match.group(1).lower()] = match.group(2)
            continue
        section = re.match(r'^"([^"]+)"$', line)
        if section:
            key = section.group(1).lower()
            new = {}
            current[key] = new
            stack.append(current)
            current = new
            continue
        if line == "}" and len(stack) > 1:
            current = stack.pop()
    return result


def parse_vdf_simple(text: str) -> dict:
    """Flexible KeyValues fallback used only after the 2.0.0 parser."""
    tokens = re.findall(r'"((?:\\.|[^"])*)"|([{}])', text)
    root: dict = {}
    stack = [root]
    pending_key: Optional[str] = None
    for quoted, brace in tokens:
        if brace:
            if brace == "{":
                if pending_key is None:
                    continue
                child = {}
                stack[-1][pending_key] = child
                stack.append(child)
                pending_key = None
            elif len(stack) > 1:
                stack.pop()
                pending_key = None
            continue
        token = quoted
        if pending_key is None:
            pending_key = token
        else:
            stack[-1][pending_key] = token
            pending_key = None
    return root


def load_vdf(path: Path) -> dict:
    # First attempt the exact parser used by 2.0.0.  It is deliberately first,
    # because the user's previous build successfully discovered their libraries.
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        legacy = parse_vdf_legacy(text)
        if legacy:
            return legacy
    except Exception:
        text = None

    if steam_vdf is not None:
        try:
            with path.open(encoding="utf-8", errors="ignore") as handle:
                return steam_vdf.load(handle)
        except Exception:
            pass
    try:
        if text is None:
            text = path.read_text(encoding="utf-8", errors="replace")
        return parse_vdf_simple(text)
    except Exception:
        return {}


def _get_ci(mapping: dict, key: str, default=None):
    if key in mapping:
        return mapping[key]
    lower = key.lower()
    for current_key, value in mapping.items():
        if str(current_key).lower() == lower:
            return value
    return default


def get_steam_library_dirs_legacy(steam_root: Path) -> List[Path]:
    """Exact library discovery used by CreamLinux 2.0.0."""
    directories = [steam_root / "steamapps"]
    library_file = steam_root / "steamapps" / "libraryfolders.vdf"
    if library_file.exists():
        try:
            data = parse_vdf_legacy(library_file.read_text(errors="replace"))
            folders = data.get("libraryfolders", {})
            for value in folders.values():
                if isinstance(value, dict):
                    path = value.get("path")
                    if path:
                        directories.append(Path(path) / "steamapps")
                elif isinstance(value, str) and value.startswith("/"):
                    directories.append(Path(value) / "steamapps")
        except Exception:
            pass
    return [directory for directory in directories if directory.is_dir()]


def get_steam_library_dirs(steam_root: Optional[Path] = None) -> List[Path]:
    """Discover libraries with 2.0.0 first, then add newer Steam roots.

    No discovered path is canonicalised with Path.resolve(); Steam's path is
    retained exactly as stored in libraryfolders.vdf.
    """
    directories: List[Path] = []

    # 1) Primary compatibility path: identical to 2.0.0.
    primary = steam_root or find_steam_root_legacy()
    if primary:
        directories.extend(get_steam_library_dirs_legacy(primary))

    # 2) Additional roots (Flatpak variants, ~/.steam/root, etc.).
    for root in ([steam_root] if steam_root else get_steam_roots()):
        if not root:
            continue
        directories.append(root / "steamapps")
        library_file = root / "steamapps" / "libraryfolders.vdf"
        if not library_file.exists():
            continue
        try:
            data = load_vdf(library_file)
            folders = _get_ci(data, "libraryfolders", {}) or {}
            for value in folders.values():
                if isinstance(value, dict):
                    path = _get_ci(value, "path")
                    if path:
                        directories.append(Path(str(path)) / "steamapps")
                elif isinstance(value, str) and value.startswith("/"):
                    directories.append(Path(value) / "steamapps")
        except Exception:
            pass

    # 3) Last-resort mount probing. Never replaces libraryfolders.vdf.
    directories.extend(discover_additional_steamapps())

    result: List[Path] = []
    seen: set[str] = set()
    for directory in directories:
        key = os.path.normpath(os.path.abspath(os.path.expanduser(str(directory))))
        if directory.is_dir() and key not in seen:
            result.append(directory)
            seen.add(key)
    return result


def get_steam_games() -> List[dict]:
    libraries = get_steam_library_dirs()
    if not libraries:
        return []

    # Group by normalized title. In normal Steam installs duplicate manifests
    # share the same AppID, but title grouping also handles stale/duplicated
    # library metadata without showing the same game twice.
    grouped: Dict[str, dict] = {}
    for library in libraries:
        for acf in library.glob("appmanifest_*.acf"):
            try:
                data = load_vdf(acf)
                app = _get_ci(data, "AppState", data) or data
                app_id = str(_get_ci(app, "appid", "") or "")
                name = str(_get_ci(app, "name", "") or "").strip()
                installdir = str(_get_ci(app, "installdir", "") or "").strip()
                if not app_id or not name or not installdir:
                    continue
                if is_steam_non_game(app_id, name, installdir):
                    continue

                game_dir = library / "common" / installdir
                if not game_dir.is_dir():
                    continue

                key = normalize_game_title(name)
                entry = grouped.setdefault(key, {
                    "appId": app_id,
                    "appIds": [],
                    "name": name,
                    "directory": str(game_dir),
                    "directories": [],
                    "platform": "Steam",
                })
                if app_id not in entry["appIds"]:
                    entry["appIds"].append(app_id)
                directory = str(game_dir)
                if directory not in entry["directories"]:
                    entry["directories"].append(directory)
            except Exception:
                pass

    return list(grouped.values())

def get_epic_games() -> List[dict]:
    grouped: Dict[str, dict] = {}

    def add(namespace, name, install_path):
        namespace = str(namespace or "").strip()
        name = str(name or "").strip()
        install_path = str(install_path or "").strip()
        if not namespace or not name or not install_path:
            return
        path = Path(install_path)
        if not path.is_dir():
            return

        key = normalize_game_title(name)
        entry = grouped.setdefault(key, {
            "appId": namespace,
            "appIds": [],
            "name": name,
            "directory": str(path),
            "directories": [],
            "platform": "Epic",
        })
        if namespace not in entry["appIds"]:
            entry["appIds"].append(namespace)
        directory = str(path)
        if directory not in entry["directories"]:
            entry["directories"].append(directory)

    for heroic in EPIC_HEROIC_PATHS:
        for filename in ("legendary_library.json", "installed.json"):
            source = heroic / "store_cache" / filename
            if not source.exists():
                source = heroic / filename
            if not source.exists():
                continue
            try:
                raw = json.loads(source.read_text())
                if isinstance(raw, list):
                    items = raw
                else:
                    items = raw.get("library", raw.get("installed", list(raw.values())))
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    namespace = item.get("namespace") or item.get("catalog_namespace")
                    name = item.get("title") or item.get("app_title", "")
                    install = item.get("install", {})
                    if isinstance(install, dict):
                        path = install.get("install_path") or item.get("install_path") or item.get("folder_name")
                    else:
                        path = item.get("install_path") or item.get("folder_name")
                    add(namespace, name, path)
            except Exception:
                pass

    if LEGENDARY_INSTALLED.exists():
        try:
            for item in json.loads(LEGENDARY_INSTALLED.read_text()).values():
                add(
                    item.get("catalog_namespace") or item.get("namespace"),
                    item.get("title", ""),
                    item.get("install_path", ""),
                )
        except Exception:
            pass
    return list(grouped.values())

def find_dll_dirs(game_dir: Path, platform: str) -> List[str]:
    targets = STEAM_DLL_NAMES if platform == "Steam" else EPIC_DLL_NAMES
    found: List[str] = []
    try:
        for root, dirs, files in os.walk(game_dir):
            dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
            lower_files = {f.lower() for f in files}
            if any(target.lower() in lower_files for target in targets):
                value = str(Path(root))
                if value not in found:
                    found.append(value)
    except Exception:
        pass
    return found


def get_installed_unlocker(directory: str, platform: str) -> Optional[str]:
    path = Path(directory)
    bundled = bundled_unlocker_hashes()
    if platform == "Steam":
        for name in ("steam_api.dll", "steam_api64.dll"):
            file = path / name
            if file.exists():
                value = md5_file(file)
                if value in CREAMAPI_MD5S or value in {
                    md5_file(CREAMAPI_DIR / "steam_api.dll"),
                    md5_file(CREAMAPI_DIR / "steam_api64.dll"),
                }:
                    return "creamapi"
                if value in SMOKEAPI_MD5S or value in {
                    md5_file(SMOKEAPI_DIR / "steam_api.dll"),
                    md5_file(SMOKEAPI_DIR / "steam_api64.dll"),
                }:
                    return "smokeapi"
        if (path / "cream_api.ini").exists():
            return "creamapi"
        if (path / "SmokeAPI.config.json").exists() or (path / "SmokeAPI.json").exists():
            return "smokeapi"
    elif platform == "Epic":
        scream_hashes = {
            md5_file(SCREAMAPI_DIR / "EOSSDK-Win32-Shipping.dll"),
            md5_file(SCREAMAPI_DIR / "EOSSDK-Win64-Shipping.dll"),
        }
        for name in ("EOSSDK-Win32-Shipping.dll", "EOSSDK-Win64-Shipping.dll"):
            file = path / name
            if file.exists():
                value = md5_file(file)
                if value in SCREAMAPI_MD5S or value in scream_hashes or value in bundled:
                    return "screamapi"
        if (path / "ScreamAPI.config.json").exists() or (path / "ScreamAPI.json").exists():
            return "screamapi"
    return None


# -----------------------------------------------------------------------------
# DLC metadata / cache
# -----------------------------------------------------------------------------
def steam_banner_path(app_id: str) -> Path:
    return IMAGE_CACHE_DIR / f"steam-{app_id}-header.jpg"


def fetch_steam_banner(app_id: str) -> Optional[Path]:
    if not app_id:
        return None
    target = steam_banner_path(app_id)
    if target.exists() and target.stat().st_size > 0:
        return target
    urls = [
        f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg",
        f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg",
    ]
    for url in urls:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": f"CreamLinux/{VERSION}"})
            with urllib.request.urlopen(request, timeout=10) as response:
                data = response.read()
            if data:
                target.write_bytes(data)
                return target
        except Exception:
            continue
    return target if target.exists() else None


def query_steam_store(app_id: str, is_dlc: bool = False) -> Optional[dict]:
    cache = APPINFO_DIR / f"{app_id}.json"
    cooldown = 1200 if is_dlc else 600
    if cache.exists() and not check_cooldown(app_id, cooldown):
        return read_json(cache)
    try:
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
        request = urllib.request.Request(url, headers={"User-Agent": f"CreamLinux/{VERSION}"})
        with urllib.request.urlopen(request, timeout=12) as response:
            raw = json.loads(response.read())
        data = raw.get(str(app_id), {})
        if data.get("success") and data.get("data"):
            write_json(cache, data["data"])
            return data["data"]
    except Exception:
        pass
    return read_json(cache) if cache.exists() else None


def get_steam_dlc(app_id: str) -> List[dict]:
    result: List[dict] = []
    store = query_steam_store(app_id)
    if not store:
        return result
    for dlc_id in store.get("dlc", []):
        data = query_steam_store(str(dlc_id), is_dlc=True)
        name = (data.get("name") if data else None) or f"DLC {dlc_id}"
        result.append({"id": str(dlc_id), "name": name, "type": "Steam"})
    return result


def query_epic_catalog(namespace: str) -> List[dict]:
    cache = APPINFO_DIR / f"epic_{namespace}.json"
    if cache.exists() and not check_cooldown(f"epic_{namespace}", 600):
        return read_json(cache) or []
    payload = json.dumps({
        "query": (
            "query($ns:String!){Catalog{"
            "searchStore(namespace:$ns,category:\"*\"){elements{id title items{id}}}"
            "catalogOffers(namespace:$ns,params:{count:1000}){elements{id title items{id title}}}}}"
        ),
        "variables": {"ns": namespace},
    }).encode()
    try:
        request = urllib.request.Request(
            "https://launcher.store.epicgames.com/graphql",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "EpicGamesLauncher/18.9.0-45233261+++Portal+Release-Live",
            },
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            raw = json.loads(response.read())
        catalog = raw.get("data", {}).get("Catalog", {})
        result: List[dict] = []
        seen_ids: set[str] = set()
        for section in ("searchStore", "catalogOffers"):
            for element in catalog.get(section, {}).get("elements", []):
                for item in element.get("items", []):
                    item_id = item.get("id")
                    if item_id and item_id not in seen_ids:
                        result.append({
                            "id": item_id,
                            "name": item.get("title") or element.get("title") or item_id,
                            "type": "Epic",
                        })
                        seen_ids.add(item_id)
        write_json(cache, result)
        return result
    except Exception:
        return read_json(cache) or [] if cache.exists() else []


# -----------------------------------------------------------------------------
# Install / uninstall logic
# -----------------------------------------------------------------------------
def install_steam_unlocker(directory: str, unlocker: str) -> List[dict]:
    log: List[dict] = []
    path = Path(directory)
    unlocker = unlocker.lower()
    pairs = [
        ("steam_api.dll", "steam_api_o.dll", 32),
        ("steam_api64.dll", "steam_api64_o.dll", 64),
    ]
    for original_name, backup_name, bits in pairs:
        original = path / original_name
        backup = path / backup_name
        source = get_dll_path(unlocker, bits)
        if not original.exists() and not backup.exists():
            continue
        if original.exists() and not backup.exists() and not is_any_unlocker(original):
            try:
                original.rename(backup)
                log.append({"msg": f"Renamed {original_name} → {backup_name}", "ok": True})
            except Exception as exc:
                log.append({"msg": f"Failed to rename {original_name}: {exc}", "ok": False})
                continue
        if source and source.exists():
            try:
                shutil.copy2(source, original)
                log.append({"msg": f"Installed {unlocker} ({bits}-bit): {original_name}", "ok": True})
            except Exception as exc:
                log.append({"msg": f"Failed to copy {unlocker} DLL: {exc}", "ok": False})
        else:
            log.append({
                "msg": f"⚠ Bundled {unlocker} {bits}-bit DLL not found — place it in the {unlocker}/ folder",
                "ok": False,
            })
    return log


def install_screamapi_unlocker(directory: str) -> List[dict]:
    log: List[dict] = []
    path = Path(directory)
    pairs = [
        ("EOSSDK-Win32-Shipping.dll", "EOSSDK-Win32-Shipping_o.dll", 32),
        ("EOSSDK-Win64-Shipping.dll", "EOSSDK-Win64-Shipping_o.dll", 64),
    ]
    for original_name, backup_name, bits in pairs:
        original = path / original_name
        backup = path / backup_name
        source = get_dll_path("screamapi", bits)
        if not original.exists() and not backup.exists():
            continue
        if original.exists() and not backup.exists() and not is_any_unlocker(original):
            try:
                original.rename(backup)
                log.append({"msg": f"Renamed {original_name} → {backup_name}", "ok": True})
            except Exception as exc:
                log.append({"msg": f"Failed to rename {original_name}: {exc}", "ok": False})
                continue
        if source and source.exists():
            try:
                shutil.copy2(source, original)
                log.append({"msg": f"Installed ScreamAPI ({bits}-bit): {original_name}", "ok": True})
            except Exception as exc:
                log.append({"msg": f"Failed to copy ScreamAPI DLL: {exc}", "ok": False})
        else:
            log.append({
                "msg": f"⚠ Bundled ScreamAPI {bits}-bit DLL not found — place it in the screamapi/ folder",
                "ok": False,
            })
    return log


def uninstall_steam_unlocker(directory: str) -> List[dict]:
    log: List[dict] = []
    path = Path(directory)
    for original_name, backup_name in [
        ("steam_api.dll", "steam_api_o.dll"),
        ("steam_api64.dll", "steam_api64_o.dll"),
    ]:
        original = path / original_name        backup = path / backup_name
        if backup.exists():
            try:
                if original.exists():
                    original.unlink()
                    log.append({"msg": f"Removed unlocker DLL: {original_name}", "ok": True})
                backup.rename(original)
                log.append({"msg": f"Restored: {backup_name} → {original_name}", "ok": True})
            except Exception as exc:
                log.append({"msg": f"Failed to restore {original_name}: {exc}", "ok": False})
    for filename in (
        "cream_api.ini", "SmokeAPI.config.json", "SmokeAPI.json",
        "SmokeAPI.log", "SmokeAPI.log.log", "SmokeAPI.cache.json",
    ):
        file = path / filename
        if file.exists():
            try:
                file.unlink()
                log.append({"msg": f"Deleted {filename}", "ok": True})
            except Exception as exc:
                log.append({"msg": f"Failed to delete {filename}: {exc}", "ok": False})
    return log


def uninstall_screamapi(directory: str) -> List[dict]:
    log: List[dict] = []
    path = Path(directory)
    for original_name, backup_name in [
        ("EOSSDK-Win32-Shipping.dll", "EOSSDK-Win32-Shipping_o.dll"),
        ("EOSSDK-Win64-Shipping.dll", "EOSSDK-Win64-Shipping_o.dll"),
    ]:
        original = path / original_name
        backup = path / backup_name
        if backup.exists():
            try:
                if original.exists():
                    original.unlink()
                    log.append({"msg": f"Removed ScreamAPI DLL: {original_name}", "ok": True})
                backup.rename(original)
                log.append({"msg": f"Restored: {backup_name} → {original_name}", "ok": True})
            except Exception as exc:
                log.append({"msg": f"Failed to restore {original_name}: {exc}", "ok": False})
    for filename in ("ScreamAPI.config.json", "ScreamAPI.json", "ScreamAPI.log", "ScreamAPI.log.log"):
        file = path / filename
        if file.exists():
            try:
                file.unlink()
                log.append({"msg": f"Deleted {filename}", "ok": True})
            except Exception as exc:
                log.append({"msg": f"Failed to delete {filename}: {exc}", "ok": False})
    return log


def write_creamapi_config(directory: str, game: dict, enabled_dlc: List[dict]) -> str:
    lines = [
        f"; {game['name']}", "[steam]", f"appid = {game['appId']}",
        "unlockall = false", "orgapi = steam_api_o.dll", "orgapi64 = steam_api64_o.dll",
        "extraprotection = false", "forceoffline = false", "", "[steam_misc]",
        "disableuserinterface = false", "", "[dlc]",
    ]
    for dlc in sorted(enabled_dlc, key=lambda item: item["id"]):
        safe_name = str(dlc["name"]).replace("\n", " ").replace("\r", " ")
        lines.append(f"{dlc['id']} = {safe_name}")
    output = Path(directory) / "cream_api.ini"
    output.write_text("\n".join(lines))
    return str(output)


def write_smokeapi_config(directory: str, game: dict, enabled_dlc: List[dict], all_dlc: List[dict]) -> str:
    enabled = {dlc["id"] for dlc in enabled_dlc}
    locked = {dlc["id"]: "locked" for dlc in all_dlc if dlc["id"] not in enabled}
    config = {
        "$version": 4, "logging": False, "log_steam_http": False,
        "default_app_status": "unlocked", "override_app_status": {},
        "override_dlc_status": locked, "auto_inject_inventory": True,
        "extra_inventory_items": [], "extra_dlcs": {},
    }
    output = Path(directory) / "SmokeAPI.config.json"
    output.write_text(json.dumps(config, indent=2))
    return str(output)


def write_screamapi_config(directory: str, game: dict, enabled_dlc: List[dict], all_dlc: List[dict]) -> str:
    enabled = {dlc["id"] for dlc in enabled_dlc}
    locked = {dlc["id"]: "locked" for dlc in all_dlc if dlc["id"] not in enabled}
    config = {
        "$version": 3, "logging": False, "log_eos": False, "block_metrics": False,
        "namespace_id": "", "default_dlc_status": "unlocked", "override_dlc_status": locked,
        "extra_graphql_endpoints": [], "extra_entitlements": {},
    }
    output = Path(directory) / "ScreamAPI.config.json"
    output.write_text(json.dumps(config, indent=2))
    return str(output)


def install_for_game(game: dict, dlc_selection: List[dict], unlocker: str) -> dict:
    all_log: List[dict] = []
    all_dlc = game.get("dlc", [])
    dll_dirs = game_dll_dirs(game)
    if not dll_dirs:
        return {"game": game["name"], "results": [{"msg": "No DLL directories found in any game installation.", "ok": False}]}

    for directory in dll_dirs:
        all_log.append({"msg": f"Ruta: {directory}", "ok": True})
        if game["platform"] == "Steam":
            all_log.extend(install_steam_unlocker(directory, unlocker))
            try:
                if unlocker.lower() == "creamapi":
                    config = write_creamapi_config(directory, game, dlc_selection)
                else:
                    config = write_smokeapi_config(directory, game, dlc_selection, all_dlc)
                all_log.append({"msg": f"Wrote config: {Path(config).name}", "ok": True})
            except Exception as exc:
                all_log.append({"msg": f"Config write failed: {exc}", "ok": False})
        elif game["platform"] == "Epic":
            all_log.extend(install_screamapi_unlocker(directory))
            try:
                config = write_screamapi_config(directory, game, dlc_selection, all_dlc)
                all_log.append({"msg": f"Wrote config: {Path(config).name}", "ok": True})
            except Exception as exc:
                all_log.append({"msg": f"Config write failed: {exc}", "ok": False})
    return {"game": game["name"], "results": all_log}


def uninstall_for_game(game: dict) -> dict:
    all_log: List[dict] = []
    for directory in game_dll_dirs(game):
        all_log.append({"msg": f"Ruta: {directory}", "ok": True})
        if game["platform"] == "Steam":
            all_log.extend(uninstall_steam_unlocker(directory))
        elif game["platform"] == "Epic":
            all_log.extend(uninstall_screamapi(directory))
    if not all_log:
        all_log.append({"msg": "Nothing to uninstall.", "ok": True})
    return {"game": game["name"], "results": all_log}


def scan_games() -> List[dict]:
    games = get_steam_games() + get_epic_games()
    result: List[dict] = []
    for game in games:
        install_dirs = game_install_dirs(game)
        if not install_dirs:
            continue
        protection_warnings: List[str] = []
        for directory in install_dirs:
            for warning in detect_protections(game["name"], directory):
                if warning not in protection_warnings:
                    protection_warnings.append(warning)
        game["protectionWarnings"] = protection_warnings
        game["protected"] = bool(protection_warnings)

        dll_dirs: List[str] = []
        for install_dir in install_dirs:
            for directory in find_dll_dirs(install_dir, game["platform"]):
                if directory not in dll_dirs:
                    dll_dirs.append(directory)
        game["dllDirs"] = dll_dirs
        game["installCount"] = len(install_dirs)

        installed_unlockers: List[str] = []
        for directory in dll_dirs:
            detected = get_installed_unlocker(directory, game["platform"])
            if detected and detected not in installed_unlockers:
                installed_unlockers.append(detected)
        game["installedUnlockers"] = installed_unlockers
        game["installedUnlocker"] = installed_unlockers[0] if len(installed_unlockers) == 1 else ("mixed" if installed_unlockers else None)
        game["installed"] = bool(installed_unlockers)

        try:
            if game["platform"] == "Steam":
                game["dlc"] = get_steam_dlc(game["appId"])
            else:
                game["dlc"] = query_epic_catalog(game["appId"])
        except Exception:
            game["dlc"] = []
        game["dllAvailability"] = {
            "creamapi": dll_available("creamapi", 32) or dll_available("creamapi", 64),
            "smokeapi": dll_available("smokeapi", 32) or dll_available("smokeapi", 64),
            "screamapi": dll_available("screamapi", 32) or dll_available("screamapi", 64),
        }
        result.append(game)
    return sorted(result, key=lambda item: item["name"].lower())

def load_dlc_choices() -> Dict[str, List[str]]:
    data = read_json(DLC_CHOICES)
    return data if isinstance(data, dict) else {}


def save_dlc_choices(choices: Dict[str, List[str]]) -> None:
    write_json(DLC_CHOICES, choices)


# -----------------------------------------------------------------------------
# Workers
# -----------------------------------------------------------------------------
class ScanWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def run(self):
        try:
            self.completed.emit(scan_games())
        except Exception as exc:
            self.failed.emit(str(exc))


class ActionWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, action: str, game: dict, selected_dlc: List[dict], unlocker: str):
        super().__init__()
        self.action = action
        self.game = game
        self.selected_dlc = selected_dlc
        self.unlocker = unlocker

    def run(self):
        try:
            if self.action == "install":
                result = install_for_game(self.game, self.selected_dlc, self.unlocker)
            else:
                result = uninstall_for_game(self.game)
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


# -----------------------------------------------------------------------------
# Qt UI — visual language follows SteamCommandGen
# -----------------------------------------------------------------------------
STYLE = r"""
QWidget {
    background: transparent;
    color: #DCE5EC;
    font-family: "Inter", "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 13px;
}
QMainWindow, QWidget#CentralRoot { background: #161D25; }
QFrame#TopBar {
    background: #1C2732;
    border: none;
    border-bottom: 1px solid #30404D;
}
QFrame#Panel { background: #161D25; border: none; }
QFrame#InfoCard, QFrame#ActionCard, QFrame#HeroCard {
    background: #1C2732;
    border: 1px solid #30404D;
    border-radius: 10px;
}
QLabel#AppTitle { color: #FFFFFF; font-size: 22px; font-weight: 800; }
QLabel#AppSubTitle { color: #78C8F2; font-size: 12px; }
QLabel#SectionTitle { color: #F7FAFC; font-size: 14px; font-weight: 750; }
QLabel#GameTitle { color: #FFFFFF; font-size: 27px; font-weight: 850; }
QLabel#HeroBanner {
    background: #17212B;
    border: 1px solid #344754;
    border-radius: 8px;
    padding: 8px;
    color: #AFC0CC;
    font-size: 14px;
    font-weight: 700;
}
QLabel#HeroSub { color: #78C8F2; font-size: 11px; font-weight: 700; }
QLabel#Muted { color: #98A7B2; }
QLabel#Value { color: #E3EBF1; font-weight: 650; }
QLabel#Success { color: #7ED89B; font-weight: 750; }
QLabel#Warning { color: #F2C76C; font-weight: 700; }
QLineEdit {
    background: #1A2530;
    border: 1px solid #344754;
    border-radius: 7px;
    padding: 9px 11px;
    color: #FFFFFF;
    selection-background-color: #2C83B8;
}
QLineEdit:focus { border-color: #67C7F5; }
QListWidget, QTableWidget {
    background: #18212A;
    border: 1px solid #30404D;
    border-radius: 8px;
    outline: none;
    alternate-background-color: #18212A;
    gridline-color: transparent;
}
QListWidget::item {
    background: transparent;
    color: #DCE5EC;
    padding: 9px 10px;
    margin: 2px 4px;
    border: 1px solid transparent;
    border-radius: 6px;
}
QListWidget::item:selected {
    background: transparent;
    color: #FFFFFF;
    border: 1px solid #67C7F5;
}
QListWidget::item:hover:!selected {
    background: transparent;
    color: #FFFFFF;
    border: 1px solid #405564;
}
QHeaderView { background: #18212A; }
QHeaderView::section {
    background: #1C2732;
    color: #AAB8C4;
    border: none;
    border-bottom: 1px solid #344754;
    padding: 8px 9px;
    font-weight: 700;
}
QTableWidget::item {
    background: transparent;
    color: #DCE5EC;
    padding: 7px 8px;
    border: none;
    border-bottom: 1px solid #273640;
}
QTableWidget::item:selected {
    background: transparent;
    color: #DCE5EC;
}
QTableCornerButton::section { background: #1C2732; border: none; }
QPushButton, QToolButton {
    background: #223442;
    border: 1px solid #3A5364;
    border-radius: 7px;
    color: #E5EDF2;
    padding: 8px 13px;
    font-weight: 650;
}
QPushButton:hover, QToolButton:hover {
    background: #294052;
    border-color: #67C7F5;
    color: #FFFFFF;
}
QPushButton:pressed, QToolButton:pressed { background: #213747; }
QPushButton:disabled, QToolButton:disabled {
    color: #6E7D88;
    background: #1B2730;
    border-color: #2A3A45;
}
QPushButton#PrimaryButton {
    background: #238CCA;
    border-color: #67C7F5;
    color: #FFFFFF;
    font-weight: 800;
}
QPushButton#PrimaryButton:hover { background: #2B9DDF; }
QPushButton#DangerButton {
    background: transparent;
    border-color: #87515B;
    color: #EEAAB1;
}
QPushButton#DangerButton:hover { background: #3A292D; border-color: #C06B76; color: #FFFFFF; }
QToolButton#FilterButton { padding: 7px 10px; background: transparent; }
QToolButton#FilterButton:checked { background: transparent; border-color: #67C7F5; color: #FFFFFF; }
QToolButton#UnlockerCard {
    min-height: 60px;
    background: #1A2630;
    border: 1px solid #3A5364;
    border-radius: 9px;
    font-size: 14px;
    font-weight: 800;
    padding: 10px;
}
QToolButton#UnlockerCard:hover { border-color: #67C7F5; background: #1A2630; }
QToolButton#UnlockerCard:checked { border: 2px solid #67C7F5; background: #1C3140; color: #FFFFFF; }
QCheckBox { spacing: 8px; background: transparent; }
QCheckBox::indicator { width: 17px; height: 17px; }
QCheckBox::indicator:unchecked { border: 1px solid #5F7787; background: #18212A; border-radius: 4px; }
QCheckBox::indicator:checked { border: 1px solid #67C7F5; background: #238CCA; border-radius: 4px; }
QListWidget::viewport, QTableWidget::viewport { background: #18212A; }
QScrollArea, QScrollArea::viewport, QScrollArea > QWidget, QScrollArea > QWidget > QWidget { background: #161D25; border: none; }
QScrollBar:vertical { background: transparent; width: 9px; margin: 2px; }
QScrollBar::handle:vertical { background: #405767; min-height: 30px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #536F82; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 9px; margin: 2px; }
QScrollBar::handle:horizontal { background: #405767; min-width: 30px; border-radius: 4px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QSplitter::handle { background: #30404D; width: 1px; }
QStatusBar { background: #1A242D; color: #98A7B2; border-top: 1px solid #30404D; }
QStatusBar::item { border: none; }
"""


class AspectRatioPixmapLabel(QLabel):
    """Artwork label that always fits the full source image in its box."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._source_pixmap = QPixmap()

    def setSourcePixmap(self, pixmap: QPixmap):
        self._source_pixmap = pixmap if pixmap is not None else QPixmap()
        self._refresh_pixmap()

    def clearSourcePixmap(self):
        self._source_pixmap = QPixmap()
        self.setPixmap(QPixmap())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_pixmap()

    def _refresh_pixmap(self):
        if self._source_pixmap.isNull():
            return
        size = self.contentsRect().size()
        if size.width() <= 0 or size.height() <= 0:
            return
        self.setPixmap(self._source_pixmap.scaled(
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))


class ResultDialog(QDialog):
    def __init__(self, title: str, results: List[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(700, 420)
        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setObjectName("GameTitle")
        layout.addWidget(heading)
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["Estado", "Acción"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setShowGrid(False)
        table.setAlternatingRowColors(False)
        table.verticalHeader().setDefaultSectionSize(36)
        for row, result in enumerate(results or [{"msg": "No actions were taken.", "ok": True}]):
            table.insertRow(row)
            status = QTableWidgetItem("✓" if result.get("ok") else "✕")
            status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 0, status)
            table.setItem(row, 1, QTableWidgetItem(str(result.get("msg", ""))))
        layout.addWidget(table)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.games: List[dict] = []
        self.filtered_games: List[dict] = []
        self.current_game: Optional[dict] = None
        self.current_filter = "All"
        self.current_unlocker = "creamapi"
        self.dlc_choices = load_dlc_choices()
        self.scan_worker: Optional[ScanWorker] = None
        self.action_worker: Optional[ActionWorker] = None
        self.setWindowTitle(f"CreamLinux {VERSION}")
        self.resize(1200, 700)
        self.setMinimumSize(900, 520)
        icon = ASSETS_DIR / "creamlinux-dlc-unlocker.svg"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        self.setStyleSheet(STYLE)
        self._build_ui()
        self._set_status("Listo — pulsa «Escanear juegos» para comenzar")

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("CentralRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        top = QFrame()
        top.setObjectName("TopBar")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(18, 10, 18, 10)
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title = QLabel("CreamLinux")
        title.setObjectName("AppTitle")
        subtitle = QLabel(f"DLC Manager · v{VERSION} · {QT_BINDING}")
        subtitle.setObjectName("AppSubTitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        top_layout.addLayout(title_box)
        top_layout.addStretch(1)
        self.scan_button = QPushButton("↻  Escanear juegos")
        self.scan_button.clicked.connect(self.start_scan)
        help_button = QPushButton("?  Ayuda")
        help_button.clicked.connect(self.show_help)
        top_layout.addWidget(self.scan_button)
        top_layout.addWidget(help_button)
        root_layout.addWidget(top)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        root_layout.addWidget(splitter, 1)

        # Left panel
        left = QFrame()
        left.setObjectName("Panel")
        left.setMinimumWidth(285)
        left.setMaximumWidth(390)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(9)
        left_title = QLabel("Juegos detectados")
        left_title.setObjectName("SectionTitle")
        left_layout.addWidget(left_title)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar juego…")
        self.search.textChanged.connect(self.apply_filter)
        left_layout.addWidget(self.search)

        filters = QHBoxLayout()
        filters.setSpacing(5)
        self.filter_group = QButtonGroup(self)
        self.filter_group.setExclusive(True)
        for name in ("All", "Steam", "Epic"):
            button = QToolButton()
            button.setObjectName("FilterButton")
            button.setText("Todos" if name == "All" else name)
            button.setCheckable(True)
            button.setChecked(name == "All")
            button.clicked.connect(lambda checked=False, value=name: self.set_filter(value))
            self.filter_group.addButton(button)
            filters.addWidget(button)
        left_layout.addLayout(filters)

        self.game_list = QListWidget()
        self.game_list.setSpacing(1)
        self.game_list.setUniformItemSizes(True)
        self.game_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.game_list.currentRowChanged.connect(self.on_game_selected)
        left_layout.addWidget(self.game_list, 1)
        self.count_label = QLabel("Steam: 0   ·   Epic: 0")
        self.count_label.setObjectName("Muted")
        left_layout.addWidget(self.count_label)
        splitter.addWidget(left)

        # Right panel
        right = QFrame()
        right.setObjectName("Panel")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)
        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack)

        placeholder = QWidget()
        ph = QVBoxLayout(placeholder)
        ph.addStretch(1)
        ph_title = QLabel("CreamLinux")
        ph_title.setObjectName("GameTitle")
        ph_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_text = QLabel("Escanea tu biblioteca, selecciona un juego y verás su cabecera visual, título destacado y configuración de DLC.")
        ph_text.setObjectName("Muted")
        ph_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph.addWidget(ph_title)
        ph.addWidget(ph_text)
        ph.addStretch(1)
        self.stack.addWidget(placeholder)

        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(10)

        # Artwork lives in its own fixed-height card.  The title is a separate
        # sibling card, so the two widgets can never share/overlap geometry.
        hero_card = QFrame()
        hero_card.setObjectName("HeroCard")
        hero_card.setMinimumHeight(246)
        hero_card.setMaximumHeight(246)
        hero_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        hero_layout = QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(12, 12, 12, 8)
        hero_layout.setSpacing(6)
        self.hero_banner = AspectRatioPixmapLabel("IMAGEN NO DISPONIBLE")
        self.hero_banner.setObjectName("HeroBanner")
        self.hero_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hero_banner.setMinimumHeight(201)
        self.hero_banner.setMaximumHeight(201)
        self.hero_banner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        hero_layout.addWidget(self.hero_banner)
        self.hero_subtitle = QLabel("STEAM · EPIC · DLC")
        self.hero_subtitle.setObjectName("HeroSub")
        self.hero_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hero_subtitle.setMinimumHeight(20)
        hero_layout.addWidget(self.hero_subtitle)
        panel_layout.addWidget(hero_card)

        info = QFrame()
        info.setObjectName("InfoCard")
        info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(14, 12, 14, 12)
        self.game_title = QLabel("—")
        self.game_title.setObjectName("GameTitle")
        self.game_title.setWordWrap(True)
        self.game_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.game_title.setMinimumHeight(44)
        info_layout.addWidget(self.game_title)
        meta = QHBoxLayout()
        self.platform_label = QLabel("Plataforma: —")
        self.platform_label.setObjectName("Muted")
        self.appid_label = QLabel("AppID: —")
        self.appid_label.setObjectName("Muted")
        self.status_label = QLabel("No instalado")
        self.status_label.setObjectName("Muted")
        meta.addWidget(self.platform_label)
        meta.addWidget(self.appid_label)
        meta.addStretch(1)
        meta.addWidget(self.status_label)
        info_layout.addLayout(meta)
        self.path_label = QLabel("—")
        self.path_label.setObjectName("Muted")
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.path_label.setWordWrap(True)
        info_layout.addWidget(self.path_label)
        self.compatibility_label = QLabel("")
        self.compatibility_label.setWordWrap(True)
        self.compatibility_label.setObjectName("Muted")
        info_layout.addWidget(self.compatibility_label)
        panel_layout.addWidget(info)

        action_card = QFrame()
        action_card.setObjectName("ActionCard")
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(14, 12, 14, 12)
        action_title = QLabel("Método")
        action_title.setObjectName("SectionTitle")
        action_layout.addWidget(action_title)
        cards = QHBoxLayout()
        cards.setSpacing(9)
        self.unlocker_group = QButtonGroup(self)
        self.unlocker_group.setExclusive(True)
        self.cream_button = QToolButton()
        self.smoke_button = QToolButton()
        self.scream_button = QToolButton()
        for button, key, text in (
            (self.cream_button, "creamapi", "CreamAPI\nSTEAM"),
            (self.smoke_button, "smokeapi", "SmokeAPI\nSTEAM"),
            (self.scream_button, "screamapi", "ScreamAPI\nEPIC"),
        ):
            button.setObjectName("UnlockerCard")
            button.setText(text)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, value=key: self.set_unlocker(value))
            self.unlocker_group.addButton(button)
            cards.addWidget(button)
        action_layout.addLayout(cards)
        self.unlocker_warning = QLabel("")
        self.unlocker_warning.setObjectName("Warning")
        self.unlocker_warning.setWordWrap(True)
        action_layout.addWidget(self.unlocker_warning)
        panel_layout.addWidget(action_card)

        dlc_header = QHBoxLayout()
        dlc_title = QLabel("Contenido descargable")
        dlc_title.setObjectName("SectionTitle")
        self.dlc_count = QLabel("0 DLC")
        self.dlc_count.setObjectName("Muted")
        select_all = QPushButton("✓ Todos")
        select_none = QPushButton("✕ Ninguno")
        select_all.clicked.connect(lambda: self.set_all_dlc(True))
        select_none.clicked.connect(lambda: self.set_all_dlc(False))
        dlc_header.addWidget(dlc_title)
        dlc_header.addWidget(self.dlc_count)
        dlc_header.addStretch(1)
        dlc_header.addWidget(select_all)
        dlc_header.addWidget(select_none)
        panel_layout.addLayout(dlc_header)

        self.dlc_table = QTableWidget(0, 3)
        self.dlc_table.setHorizontalHeaderLabels(["Activar", "ID", "DLC"])
        self.dlc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.dlc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.dlc_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.dlc_table.verticalHeader().setVisible(False)
        self.dlc_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.dlc_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.dlc_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.dlc_table.setAlternatingRowColors(False)
        self.dlc_table.setShowGrid(False)
        self.dlc_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.dlc_table.verticalHeader().setDefaultSectionSize(38)
        self.dlc_table.setMinimumHeight(210)
        panel_layout.addWidget(self.dlc_table, 1)

        dirs_title = QLabel("Rutas DLL detectadas en todas las instalaciones")
        dirs_title.setObjectName("SectionTitle")
        panel_layout.addWidget(dirs_title)
        self.dir_list = QListWidget()
        self.dir_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.dir_list.setMaximumHeight(145)
        self.dir_list.itemDoubleClicked.connect(self.open_selected_directory)
        panel_layout.addWidget(self.dir_list)

        bottom = QHBoxLayout()
        open_button = QPushButton("📁  Abrir carpeta")
        open_button.clicked.connect(self.open_selected_directory)
        self.install_button = QPushButton("Generar e instalar")
        self.install_button.setObjectName("PrimaryButton")
        self.install_button.clicked.connect(self.install_current)
        self.uninstall_button = QPushButton("Desinstalar / restaurar")
        self.uninstall_button.setObjectName("DangerButton")
        self.uninstall_button.clicked.connect(self.uninstall_current)
        bottom.addWidget(open_button)
        bottom.addStretch(1)
        bottom.addWidget(self.uninstall_button)
        bottom.addWidget(self.install_button)
        panel_layout.addLayout(bottom)

        panel.setMinimumWidth(560)
        panel_scroll = QScrollArea()
        panel_scroll.setWidgetResizable(True)
        panel_scroll.setFrameShape(QFrame.Shape.NoFrame)
        panel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        panel_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        panel_scroll.setWidget(panel)
        self.stack.addWidget(panel_scroll)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([330, 870])

        status = QStatusBar()
        self.status_text = QLabel("")
        self.status_text.setObjectName("Muted")
        status.addWidget(self.status_text, 1)
        self.setStatusBar(status)

    def _set_status(self, text: str):
        self.status_text.setText(text)

    def set_filter(self, value: str):
        self.current_filter = value
        self.apply_filter()

    def apply_filter(self):
        query = self.search.text().strip().lower()
        self.filtered_games = [
            game for game in self.games
            if (self.current_filter == "All" or game["platform"] == self.current_filter)
            and (not query or query in game["name"].lower())
        ]
        current_id = self.current_game.get("appId") if self.current_game else None
        self.game_list.blockSignals(True)
        self.game_list.clear()
        selected_row = -1
        for row, game in enumerate(self.filtered_games):
            installed = "  ✓" if game.get("installed") else ""
            warning = "  ⚠" if game.get("protectionWarnings") else ""
            no_dll = "  · sin DLL" if not game.get("dllDirs") else ""
            dlc_count = len(game.get("dlc", []))
            item = QListWidgetItem(f"{game['platform'][:3].upper()}  ·  {game['name']}{installed}{warning}{no_dll}   ·  {dlc_count} DLC")
            item.setData(Qt.ItemDataRole.UserRole, game.get("appId"))
            self.game_list.addItem(item)
            if game.get("appId") == current_id:
                selected_row = row
        self.game_list.blockSignals(False)
        if selected_row >= 0:
            self.game_list.setCurrentRow(selected_row)
        elif self.filtered_games:
            self.game_list.setCurrentRow(0)
        else:
            self.current_game = None
            self.stack.setCurrentIndex(0)

    def start_scan(self):
        if self.scan_worker and self.scan_worker.isRunning():
            return
        self.scan_button.setEnabled(False)
        self.scan_button.setText("Escaneando…")
        self._set_status("Escaneando raíces de Steam, bibliotecas adicionales, Heroic y Legendary…")
        self.scan_worker = ScanWorker()
        self.scan_worker.completed.connect(self.scan_finished)
        self.scan_worker.failed.connect(self.scan_failed)
        self.scan_worker.finished.connect(lambda: self.scan_button.setEnabled(True))
        self.scan_worker.finished.connect(lambda: self.scan_button.setText("↻  Escanear juegos"))
        self.scan_worker.start()

    def scan_finished(self, games):
        self.games = list(games)
        steam_count = sum(1 for game in self.games if game["platform"] == "Steam")
        epic_count = sum(1 for game in self.games if game["platform"] == "Epic")
        self.count_label.setText(f"Steam: {steam_count}   ·   Epic: {epic_count}")
        self.apply_filter()
        self._set_status(f"Encontrados {len(self.games)} juegos")

    def scan_failed(self, error: str):
        self._set_status(f"Error durante el escaneo: {error}")
        QMessageBox.critical(self, "CreamLinux", f"No se pudo completar el escaneo:\n\n{error}")

    def on_game_selected(self, row: int):
        if row < 0 or row >= len(self.filtered_games):
            return
        self.current_game = self.filtered_games[row]
        self.render_current_game()

    def render_current_game(self):
        game = self.current_game
        if not game:
            self.stack.setCurrentIndex(0)
            return
        self.stack.setCurrentIndex(1)
        self.game_title.setText(game["name"])
        install_dirs = [str(path) for path in game_install_dirs(game)]
        install_count = len(install_dirs)
        self.render_hero(game, install_count)
        suffix = f" · {install_count} instalaciones" if install_count != 1 else " · 1 instalación"
        self.platform_label.setText(f"Plataforma: {game['platform']}{suffix}")
        app_ids = game.get("appIds") or [game.get("appId")]
        app_ids = [str(value) for value in app_ids if value]
        self.appid_label.setText(("AppIDs: " if len(app_ids) > 1 else "AppID: ") + ", ".join(app_ids))
        self.path_label.setText("\n".join(f"• {directory}" for directory in install_dirs))
        installed = game.get("installedUnlocker")
        if installed == "mixed":
            values = ", ".join(game.get("installedUnlockers") or [])
            self.status_label.setText(f"Instalaciones con desbloqueador: {values}")
            self.status_label.setObjectName("Success")
        elif installed:
            self.status_label.setText(f"Instalado: {installed}")
            self.status_label.setObjectName("Success")
        else:
            self.status_label.setText("No instalado")
            self.status_label.setObjectName("Muted")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

        protections = game.get("protectionWarnings") or []
        if protections:
            self.compatibility_label.setText("⚠ Protección detectada: " + ", ".join(protections) + ". El juego se muestra igualmente.")
            self.compatibility_label.setObjectName("Warning")
        elif not game.get("dllDirs"):
            target_name = "steam_api.dll / steam_api64.dll" if game.get("platform") == "Steam" else "EOSSDK-Win*-Shipping.dll"
            self.compatibility_label.setText(f"Sin DLL objetivo detectada ({target_name}). El juego se mantiene visible, pero no hay una ruta de instalación válida.")
            self.compatibility_label.setObjectName("Muted")
        else:
            count = len(game.get("dllDirs") or [])
            self.compatibility_label.setText(f"✓ {count} ruta{'s' if count != 1 else ''} DLL válida{'s' if count != 1 else ''} detectada{'s' if count != 1 else ''}.")
            self.compatibility_label.setObjectName("Success")
        self.compatibility_label.style().unpolish(self.compatibility_label)
        self.compatibility_label.style().polish(self.compatibility_label)

        if game["platform"] == "Steam":
            self.cream_button.setVisible(True)
            self.smoke_button.setVisible(True)
            self.scream_button.setVisible(False)
            target = installed if installed in ("creamapi", "smokeapi") else self.current_unlocker
            if target not in ("creamapi", "smokeapi"):
                target = "creamapi"
            self.set_unlocker(target)
        else:
            self.cream_button.setVisible(False)
            self.smoke_button.setVisible(False)
            self.scream_button.setVisible(True)
            self.set_unlocker("screamapi")

        self.render_dlc()
        self.dir_list.clear()
        dll_dirs = game.get("dllDirs", [])
        for directory in dll_dirs:
            item = QListWidgetItem(directory)
            item.setData(Qt.ItemDataRole.UserRole, directory)
            self.dir_list.addItem(item)
        if dll_dirs:
            self.dir_list.setCurrentRow(0)
        else:
            empty = QListWidgetItem("No se encontró una DLL Steam/EOS compatible en las instalaciones detectadas")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.dir_list.addItem(empty)
        if install_count > 1:
            self.install_button.setText(f"Instalar en {install_count} rutas")
        else:
            self.install_button.setText("Generar e instalar")

    def render_hero(self, game: dict, install_count: int):
        dlc_count = len(game.get("dlc", []))
        platform = str(game.get("platform", "")).upper()
        self.hero_subtitle.setText(f"{platform} · {dlc_count} DLC detectados · {install_count} instalación{'es' if install_count != 1 else ''}")

        banner_loaded = False
        if game.get("platform") == "Steam":
            banner_path = fetch_steam_banner(str(game.get("appId", "")))
            if banner_path and banner_path.exists():
                pixmap = QPixmap(str(banner_path))
                if not pixmap.isNull():
                    self.hero_banner.setText("")
                    self.hero_banner.setSourcePixmap(pixmap)
                    banner_loaded = True

        if not banner_loaded:
            self.hero_banner.clearSourcePixmap()
            self.hero_banner.setText("IMAGEN NO DISPONIBLE")


    def set_unlocker(self, value: str):
        self.current_unlocker = value
        self.cream_button.setChecked(value == "creamapi")
        self.smoke_button.setChecked(value == "smokeapi")
        self.scream_button.setChecked(value == "screamapi")
        if not self.current_game:
            return
        availability = self.current_game.get("dllAvailability", {})
        available = availability.get(value, False)
        names = {"creamapi": "CreamAPI", "smokeapi": "SmokeAPI", "screamapi": "ScreamAPI"}
        if available:
            self.unlocker_warning.setText(f"{names[value]} listo para instalar.")
            self.unlocker_warning.setObjectName("Success")
        else:
            self.unlocker_warning.setText(f"⚠ Falta la DLL de {names[value]} en los recursos de la aplicación.")
            self.unlocker_warning.setObjectName("Warning")
        self.unlocker_warning.style().unpolish(self.unlocker_warning)
        self.unlocker_warning.style().polish(self.unlocker_warning)
        has_target = bool(self.current_game.get("dllDirs"))
        self.install_button.setEnabled(bool(available and has_target))

    def selected_dlc_ids(self) -> List[str]:
        ids: List[str] = []
        for row in range(self.dlc_table.rowCount()):
            widget = self.dlc_table.cellWidget(row, 0)
            if isinstance(widget, QCheckBox) and widget.isChecked():
                item = self.dlc_table.item(row, 1)
                if item:
                    ids.append(item.text())
        return ids

    def render_dlc(self):
        game = self.current_game
        if not game:
            return
        dlcs = game.get("dlc", [])
        saved = self.dlc_choices.get(str(game["appId"]))
        selected = set(saved if saved is not None else [str(dlc["id"]) for dlc in dlcs])
        self.dlc_table.setRowCount(0)
        for row, dlc in enumerate(dlcs):
            self.dlc_table.insertRow(row)
            checkbox = QCheckBox()
            checkbox.setChecked(str(dlc["id"]) in selected)
            checkbox.stateChanged.connect(self.persist_current_choices)
            holder = QWidget()
            holder.setStyleSheet("background: transparent;")
            holder_layout = QHBoxLayout(holder)
            holder_layout.setContentsMargins(8, 0, 8, 0)
            holder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            holder_layout.addWidget(checkbox)
            self.dlc_table.setCellWidget(row, 0, holder)
            self.dlc_table.setItem(row, 1, QTableWidgetItem(str(dlc["id"])))
            self.dlc_table.setItem(row, 2, QTableWidgetItem(str(dlc["name"])))
        self.dlc_count.setText(f"{len(dlcs)} DLC")
        if not dlcs:
            self.dlc_table.insertRow(0)
            empty = QTableWidgetItem("No se detectaron DLC para este juego")
            empty.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.dlc_table.setItem(0, 0, empty)
            self.dlc_table.setSpan(0, 0, 1, 3)
            self._set_status("La tienda no devolvió DLC para este juego; la instalación sigue disponible")

    def set_all_dlc(self, enabled: bool):
        for row in range(self.dlc_table.rowCount()):
            holder = self.dlc_table.cellWidget(row, 0)
            checkbox = holder.findChild(QCheckBox) if holder else None
            if checkbox:
                checkbox.blockSignals(True)
                checkbox.setChecked(enabled)
                checkbox.blockSignals(False)
        self.persist_current_choices()

    def persist_current_choices(self):
        if not self.current_game:
            return
        ids: List[str] = []
        for row in range(self.dlc_table.rowCount()):
            holder = self.dlc_table.cellWidget(row, 0)
            checkbox = holder.findChild(QCheckBox) if holder else None
            if checkbox and checkbox.isChecked():
                item = self.dlc_table.item(row, 1)
                if item:
                    ids.append(item.text())
        self.dlc_choices[str(self.current_game["appId"])] = ids
        save_dlc_choices(self.dlc_choices)

    def open_selected_directory(self, *_args):
        item = self.dir_list.currentItem()
        if item and item.data(Qt.ItemDataRole.UserRole):
            path = str(item.data(Qt.ItemDataRole.UserRole))
        elif self.current_game:
            installs = game_install_dirs(self.current_game)
            path = str(installs[0]) if installs else ""        else:
            path = ""
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def install_current(self):
        if not self.current_game or (self.action_worker and self.action_worker.isRunning()):
            return
        protections = self.current_game.get("protectionWarnings") or []
        if protections:
            answer = QMessageBox.warning(
                self,
                "Protección detectada",
                "CreamLinux ha detectado: " + ", ".join(protections) +
                ".\n\nEl juego ya no se oculta, pero modificar DLL en títulos con anti-cheat puede afectar al arranque o al multijugador. ¿Quieres continuar igualmente?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.persist_current_choices()
        selected_ids = set(self.dlc_choices.get(str(self.current_game["appId"]), []))
        selected = [dlc for dlc in self.current_game.get("dlc", []) if str(dlc["id"]) in selected_ids]
        self._start_action("install", selected)

    def uninstall_current(self):
        if not self.current_game or (self.action_worker and self.action_worker.isRunning()):
            return
        answer = QMessageBox.question(
            self,
            "Restaurar juego",
            "Se eliminarán los archivos de configuración generados y se restaurarán las DLL originales cuando exista una copia _o.\n\n¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._start_action("uninstall", [])

    def _start_action(self, action: str, selected: List[dict]):
        self.install_button.setEnabled(False)
        self.uninstall_button.setEnabled(False)
        verb = "Instalando" if action == "install" else "Restaurando"
        self._set_status(f"{verb} {self.current_game['name']}…")
        self.action_worker = ActionWorker(action, dict(self.current_game), selected, self.current_unlocker)
        self.action_worker.completed.connect(lambda result, a=action: self.action_finished(a, result))
        self.action_worker.failed.connect(self.action_failed)
        self.action_worker.start()

    def action_finished(self, action: str, result: dict):
        results = result.get("results", [])
        any_ok = any(entry.get("ok") for entry in results)
        if action == "install" and any_ok:
            self.current_game["installed"] = True
            self.current_game["installedUnlocker"] = self.current_unlocker
        elif action == "uninstall":
            self.current_game["installed"] = False
            self.current_game["installedUnlocker"] = None
        ResultDialog(
            f"{'Instalación' if action == 'install' else 'Restauración'} — {self.current_game['name']}",
            results,
            self,
        ).exec()
        self.render_current_game()
        self.apply_filter()
        self._set_status(f"Operación completada: {self.current_game['name']}")
        self.uninstall_button.setEnabled(True)
        self.set_unlocker(self.current_unlocker)

    def action_failed(self, error: str):
        self.uninstall_button.setEnabled(True)
        self.set_unlocker(self.current_unlocker)
        self._set_status(f"Error: {error}")
        QMessageBox.critical(self, "CreamLinux", f"La operación falló:\n\n{error}")

    def show_help(self):
        QMessageBox.information(
            self,
            "CreamLinux — Ayuda",
            "1. Pulsa «Escanear juegos».\n"
            "2. Selecciona un juego.\n"
            "3. En Steam elige CreamAPI o SmokeAPI; en Epic se utiliza ScreamAPI.\n"
            "4. Marca o desmarca los DLC.\n"
            "5. Pulsa «Generar e instalar». Si hay varias instalaciones del mismo juego, se aplicará a todas de una vez.\n\n"
            "La aplicación conserva la DLL original con el sufijo _o antes de sustituirla. "
            "«Desinstalar / restaurar» elimina la configuración generada y recupera la original.",
        )


def main() -> int:
    ensure_dirs()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("CreamLinux")
    app.setDesktopFileName(APP_ID)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())