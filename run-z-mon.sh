#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA_FILE="$ROOT_DIR/com.github.kendonream17.zmon.gschema.xml"
COMPILED_SCHEMA="$ROOT_DIR/gschemas.compiled"
export GSETTINGS_SCHEMA_DIR="$ROOT_DIR"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$ROOT_DIR"

# VS Code installed via Snap leaks runtime library variables into the integrated terminal.
# Clear them so system Python loads the host glibc/GTK stack instead of Snap's copies.
unset SNAP SNAP_ARCH SNAP_COMMON SNAP_CONTEXT SNAP_COOKIE SNAP_DATA SNAP_EUID
unset SNAP_INSTANCE_NAME SNAP_LAUNCHER_ARCH_TRIPLET SNAP_LIBRARY_PATH SNAP_NAME
unset SNAP_REAL_HOME SNAP_REVISION SNAP_UID SNAP_USER_COMMON SNAP_USER_DATA
unset SNAP_VERSION GTK_EXE_PREFIX GTK_IM_MODULE_FILE GTK_PATH GIO_MODULE_DIR
unset GDK_PIXBUF_MODULE_FILE GDK_PIXBUF_MODULEDIR GTK_MODULES LOCPATH
unset GIO_LAUNCHED_DESKTOP_FILE GIO_LAUNCHED_DESKTOP_FILE_PID
unset LD_LIBRARY_PATH LD_PRELOAD
if [[ -n "${XDG_DATA_DIRS_VSCODE_SNAP_ORIG:-}" ]]; then
  export XDG_DATA_DIRS="$XDG_DATA_DIRS_VSCODE_SNAP_ORIG"
fi

if [[ -f "$SCHEMA_FILE" && ( ! -f "$COMPILED_SCHEMA" || "$SCHEMA_FILE" -nt "$COMPILED_SCHEMA" ) ]]; then
  glib-compile-schemas "$ROOT_DIR"
fi

exec /usr/bin/python3 -m z_mon.z_mon "$@"
