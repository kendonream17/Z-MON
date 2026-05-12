import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from z_mon.utils import normalize_app_id, parse_size_to_bytes


class UtilsTest(unittest.TestCase):
    def test_parse_size_to_bytes_handles_human_units(self):
        self.assertEqual(parse_size_to_bytes("1.0 KiB"), 1024.0)
        self.assertEqual(parse_size_to_bytes("2.0 MiB/s"), 2.0 * 1024 * 1024)
        self.assertEqual(parse_size_to_bytes("NA"), 0.0)

    def test_parse_size_to_bytes_keeps_integer_values(self):
        self.assertEqual(parse_size_to_bytes(42), 42)

    def test_normalize_app_id(self):
        self.assertEqual(normalize_app_id("org.gnome.Terminal"), "org-gnome-Terminal-desktop")
        self.assertEqual(normalize_app_id("firefox.desktop"), "firefox-desktop")
        self.assertEqual(normalize_app_id(""), "")


if __name__ == "__main__":
    unittest.main()
