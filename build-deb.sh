#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_NAME="zayde-monitor"
PACKAGE_VERSION="1.0.0"
ARCHITECTURE="all"

BUILD_ROOT="$PROJECT_ROOT/.deb-build"
PACKAGE_ROOT="$BUILD_ROOT/${PACKAGE_NAME}_${PACKAGE_VERSION}_${ARCHITECTURE}"
DEBIAN_DIR="$PACKAGE_ROOT/DEBIAN"
DIST_DIR="$PROJECT_ROOT/dist"
OUTPUT_DEB="$DIST_DIR/${PACKAGE_NAME}_${PACKAGE_VERSION}_${ARCHITECTURE}.deb"

rm -rf "$BUILD_ROOT"
mkdir -p "$DEBIAN_DIR"
mkdir -p \
  "$PACKAGE_ROOT/usr/bin" \
  "$PACKAGE_ROOT/usr/lib/python3/dist-packages" \
  "$PACKAGE_ROOT/usr/share/$PACKAGE_NAME" \
  "$PACKAGE_ROOT/usr/share/doc/$PACKAGE_NAME" \
  "$PACKAGE_ROOT/usr/share/applications" \
  "$PACKAGE_ROOT/usr/share/glib-2.0/schemas"

cp -r "$PROJECT_ROOT/zayde_monitor" "$PACKAGE_ROOT/usr/lib/python3/dist-packages/"
find "$PACKAGE_ROOT/usr/lib/python3/dist-packages/zayde_monitor" \
  \( -name '__pycache__' -o -name '*.pyc' -o -name '*.pyo' \) -prune -exec rm -rf {} +

cp -r "$PROJECT_ROOT/glade_files" "$PACKAGE_ROOT/usr/share/$PACKAGE_NAME/"
cp -r "$PROJECT_ROOT/icons" "$PACKAGE_ROOT/usr/share/$PACKAGE_NAME/"
cp "$PROJECT_ROOT/zayde-monitor.desktop" "$PACKAGE_ROOT/usr/share/applications/"
cp "$PROJECT_ROOT/com.github.kendonream.zaydemonitor.gschema.xml" \
  "$PACKAGE_ROOT/usr/share/glib-2.0/schemas/"
cp "$PROJECT_ROOT/README.md" "$PACKAGE_ROOT/usr/share/doc/$PACKAGE_NAME/"
cp "$PROJECT_ROOT/AUTHORS" "$PACKAGE_ROOT/usr/share/doc/$PACKAGE_NAME/"
cp "$PROJECT_ROOT/LICENSE" "$PACKAGE_ROOT/usr/share/doc/$PACKAGE_NAME/copyright"

cat > "$PACKAGE_ROOT/usr/bin/zayde-monitor" <<'EOF'
#!/usr/bin/env bash
exec python3 -m zayde_monitor.zayde_monitor "$@"
EOF

cat > "$PACKAGE_ROOT/usr/bin/zayde-monitor.set_default" <<'EOF'
#!/usr/bin/env bash
exec python3 -c 'from zayde_monitor.theme_setter import set_theme_default; set_theme_default()' "$@"
EOF

cat > "$PACKAGE_ROOT/usr/bin/zayde-monitor.set_light" <<'EOF'
#!/usr/bin/env bash
exec python3 -c 'from zayde_monitor.theme_setter import set_theme_light; set_theme_light()' "$@"
EOF

cat > "$PACKAGE_ROOT/usr/bin/zayde-monitor.set_dark" <<'EOF'
#!/usr/bin/env bash
exec python3 -c 'from zayde_monitor.theme_setter import set_theme_dark; set_theme_dark()' "$@"
EOF

chmod 0755 \
  "$PACKAGE_ROOT/usr/bin/zayde-monitor" \
  "$PACKAGE_ROOT/usr/bin/zayde-monitor.set_default" \
  "$PACKAGE_ROOT/usr/bin/zayde-monitor.set_light" \
  "$PACKAGE_ROOT/usr/bin/zayde-monitor.set_dark" \
  "$PACKAGE_ROOT/usr/lib/python3/dist-packages/zayde_monitor/proc-kill.sh"

cat > "$DEBIAN_DIR/control" <<'EOF'
Package: zayde-monitor
Version: 1.0.0
Section: utils
Priority: optional
Architecture: all
Maintainer: Kendon Ream <Kendonream@gmail.com>
Depends: python3, python3-psutil, python3-gi, python3-gi-cairo, python3-cairo, gir1.2-gtk-3.0, gir1.2-wnck-3.0, lshw, dmidecode, pkexec | policykit-1
Homepage: https://www.zaydeindustries.com
Description: System monitor with a Windows-style interface
 Zayde Monitor is a Linux system monitor with CPU, memory, disk,
 network, GPU, and process views in a task-manager style interface.
EOF

cat > "$DEBIAN_DIR/postinst" <<'EOF'
#!/bin/sh
set -e

if command -v glib-compile-schemas >/dev/null 2>&1; then
    glib-compile-schemas /usr/share/glib-2.0/schemas || true
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi
EOF

cat > "$DEBIAN_DIR/postrm" <<'EOF'
#!/bin/sh
set -e

if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    if command -v glib-compile-schemas >/dev/null 2>&1; then
        glib-compile-schemas /usr/share/glib-2.0/schemas || true
    fi

    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
    fi
fi
EOF

chmod 0755 "$DEBIAN_DIR/postinst" "$DEBIAN_DIR/postrm"

mkdir -p "$DIST_DIR"
dpkg-deb --build --root-owner-group "$PACKAGE_ROOT" "$OUTPUT_DEB"
echo "Built $OUTPUT_DEB"
