"""Pure helpers used across the project and in tests."""


UNIT_FACTORS = {
    "K": 1024,
    "M": 1024 ** 2,
    "G": 1024 ** 3,
    "T": 1024 ** 4,
}


def parse_size_to_bytes(value):
    """Convert values like '1.5 MiB' or '10 KiB/s' to a numeric byte count."""
    if isinstance(value, int):
        return value

    if not value or value == "NA":
        return 0.0

    number, unit = value.split()
    factor = UNIT_FACTORS.get(unit[0], 1)
    return float(number) * factor


def normalize_app_id(app_id):
    """Normalize desktop app ids to the icon-theme search form."""
    if not app_id:
        return ""

    desktop_id = app_id if app_id.endswith(".desktop") else f"{app_id}.desktop"
    return desktop_id.replace(".", "-")
