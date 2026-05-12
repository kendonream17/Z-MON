import glob
from pathlib import Path

from zayde_monitor import config_dir, theme_preference_file


themes_available = glob.glob("/usr/share/themes/*")
light_themes = []
dark_themes = []

for theme in themes_available:
    theme_name = Path(theme).name
    if "dark" in theme_name.lower() or "black" in theme_name.lower():
        dark_themes.append(theme_name)
    else:
        light_themes.append(theme_name)


def _write_theme_preference(theme_name):
    config_dir.mkdir(parents=True, exist_ok=True)
    theme_preference_file.write_text(f"{theme_name}\n", encoding="utf-8")


def _choose_theme(themes, prompt):
    if not themes:
        raise RuntimeError("No matching GTK themes were found in /usr/share/themes.")

    for index, theme in enumerate(themes):
        print(index, ":", theme)

    index = int(input(prompt))
    if index < 0 or index >= len(themes):
        raise IndexError("Theme index out of range.")
    return themes[index]


def set_theme_default():
    """Revert to the system GTK theme."""
    try:
        if theme_preference_file.exists():
            theme_preference_file.unlink()
        print("Theme preference reset. Zayde Monitor will use the system GTK theme.")
    except OSError as exc:
        print(f"Failed to reset theme preference.\nError: {exc}")


def set_theme_light():
    """Persist a light theme preference."""
    try:
        theme_name = _choose_theme(
            light_themes,
            "Index for the light theme you want to apply?:",
        )
        _write_theme_preference(theme_name)
        print(f"Light theme set to {theme_name}.")
    except (OSError, ValueError, IndexError, RuntimeError) as exc:
        print(f"Failed to set light theme.\nError: {exc}")


def set_theme_dark():
    """Persist a dark theme preference."""
    try:
        theme_name = _choose_theme(
            dark_themes,
            "Index for the dark theme you want to apply?:",
        )
        _write_theme_preference(theme_name)
        print(f"Dark theme set to {theme_name}.")
    except (OSError, ValueError, IndexError, RuntimeError) as exc:
        print(f"Failed to set dark theme.\nError: {exc}")
