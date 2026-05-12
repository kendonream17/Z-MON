"""Shared package metadata and filesystem helpers for Z-MON."""

from pathlib import Path
import os
import sys


APP_NAME = "z-mon"
APP_DISPLAY_NAME = "Z-MON"
SETTINGS_SCHEMA_ID = "com.github.kendonream17.zmon"

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
SCHEMA_FILENAME = "com.github.kendonream17.zmon.gschema.xml"


def _data_roots():
    roots = []
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        roots.append(Path(xdg_data_home))
    roots.append(Path.home() / ".local" / "share")
    roots.append(Path(sys.prefix) / "share")
    roots.append(Path("/usr/local/share"))
    roots.append(Path("/usr/share"))
    return roots


def _resolve_resource_dir(dirname):
    candidates = [PROJECT_ROOT / dirname, PACKAGE_ROOT / dirname]
    for root in _data_roots():
        candidates.append(root / APP_NAME / dirname)

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return str(candidates[0])


files_dir = _resolve_resource_dir("glade_files")
icon_file = _resolve_resource_dir("icons")

config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME
theme_preference_file = config_dir / "theme.conf"
log_dir = Path.home() / "z_mon_log"
