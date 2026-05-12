import glob
from pathlib import Path

from z_mon import config_dir, theme_preference_file


themes_available = glob.glob("/usr/share/themes/*")
light_themes = []
dark_themes = []

for theme in themes_available:
    theme_name = Path(theme).name
    if not (Path(theme) / "gtk-3.0").exists():
        continue
    if "dark" in theme_name.lower() or "black" in theme_name.lower():
        dark_themes.append(theme_name)
    else:
        light_themes.append(theme_name)


def _write_theme_preference(theme_name):
    config_dir.mkdir(parents=True, exist_ok=True)
    theme_preference_file.write_text(f"{theme_name}\n", encoding="utf-8")


def _preferred_theme(themes, fallback_names):
    for name in fallback_names:
        if name in themes:
            return name
    return themes[0] if themes else None


def apply_theme_preference(mode):
    """Persist a non-interactive theme preference for the app settings page."""
    if mode == "system":
        if theme_preference_file.exists():
            theme_preference_file.unlink()
        return None

    if mode == "light":
        theme_name = _preferred_theme(light_themes, ("Adwaita", "Default", "Raleigh"))
    elif mode == "dark":
        theme_name = _preferred_theme(dark_themes, ("Adwaita-dark", "Pop-dark"))
    else:
        raise ValueError(f"Unknown theme mode: {mode}")

    if not theme_name:
        raise RuntimeError(f"No {mode} GTK theme was found in /usr/share/themes.")
    _write_theme_preference(theme_name)
    return theme_name


def theme_for_mode(mode):
    """Return the GTK theme that would be used for a non-system mode."""
    if mode == "light":
        return _preferred_theme(light_themes, ("Adwaita", "Default", "Raleigh"))
    if mode == "dark":
        return _preferred_theme(dark_themes, ("Adwaita-dark", "Pop-dark"))
    if mode == "system":
        return None
    raise ValueError(f"Unknown theme mode: {mode}")


def current_theme_mode():
    try:
        if not theme_preference_file.exists():
            return "system"
        theme_name = theme_preference_file.read_text(encoding="utf-8").strip().lower()
    except OSError:
        return "system"
    if "dark" in theme_name or "black" in theme_name:
        return "dark"
    return "light" if theme_name else "system"


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
        print("Theme preference reset. Z-MON will use the system GTK theme.")
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
