import unittest
from unittest import mock

from z_mon.task_pages import ServiceEntry, StartupEntry, collect_services, collect_startup_entries


class TaskPagesDataTest(unittest.TestCase):
    @mock.patch("z_mon.task_pages.shutil.which", return_value=None)
    def test_collect_services_handles_missing_systemctl(self, _which):
        rows, warning = collect_services()

        self.assertEqual(rows, [])
        self.assertIn("unsupported", warning.lower())

    @mock.patch("z_mon.task_pages.Path.exists", return_value=False)
    @mock.patch("z_mon.task_pages.shutil.which", return_value=None)
    def test_collect_startup_entries_handles_no_sources(self, _which, _exists):
        self.assertEqual(collect_startup_entries(), [])

    def test_dataclass_shapes(self):
        startup = StartupEntry("App", "Desktop app", "Enabled", "app", "/tmp/app.desktop")
        service = ServiceEntry("demo.service", "loaded", "active", "running", "Demo")

        self.assertEqual(startup.name, "App")
        self.assertEqual(service.unit, "demo.service")


if __name__ == "__main__":
    unittest.main()
