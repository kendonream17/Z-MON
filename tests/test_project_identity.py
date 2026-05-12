import unittest

from z_mon import APP_DISPLAY_NAME, APP_NAME, SCHEMA_FILENAME, SETTINGS_SCHEMA_ID, config_dir, files_dir, icon_file, log_dir


class ProjectIdentityTest(unittest.TestCase):
    def test_clean_break_identity(self):
        self.assertEqual(APP_NAME, "z-mon")
        self.assertEqual(APP_DISPLAY_NAME, "Z-MON")
        self.assertEqual(SETTINGS_SCHEMA_ID, "com.github.kendonream17.zmon")
        self.assertEqual(SCHEMA_FILENAME, "com.github.kendonream17.zmon.gschema.xml")
        self.assertTrue(str(config_dir).endswith(".config/z-mon"))
        self.assertTrue(str(log_dir).endswith("z_mon_log"))

    def test_resource_resolution_points_at_current_assets(self):
        self.assertTrue(files_dir.endswith("glade_files"))
        self.assertTrue(icon_file.endswith("icons"))


if __name__ == "__main__":
    unittest.main()
