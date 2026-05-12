"""Theme bootstrap helpers."""

import os

from zayde_monitor import theme_preference_file


def theme_agent():
    """Apply the persisted GTK theme preference before Gtk is imported."""
    try:
        if theme_preference_file.exists():
            theme_name = theme_preference_file.read_text(encoding="utf-8").strip()
            if theme_name:
                os.environ["GTK_THEME"] = theme_name
    except OSError:
        # Falling back to the system GTK theme is safe.
        return
