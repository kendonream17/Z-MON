#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export GSETTINGS_SCHEMA_DIR="$ROOT_DIR"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$ROOT_DIR"

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

glib-compile-schemas --strict "$ROOT_DIR"
python3 -m unittest discover -s "$ROOT_DIR/tests" -t "$ROOT_DIR"
python3 -m compileall "$ROOT_DIR/z_mon" "$ROOT_DIR/tests"

if command -v xvfb-run >/dev/null 2>&1; then
  timeout 8s xvfb-run -a python3 -m z_mon.z_mon || status=$?
  if [[ "${status:-0}" != "0" && "${status:-0}" != "124" ]]; then
    exit "$status"
  fi
else
  echo "xvfb-run not found; skipped graphical launch smoke test."
fi
