from pathlib import Path

from setuptools import find_packages, setup


PROJECT_ROOT = Path(__file__).resolve().parent
README_PATH = PROJECT_ROOT / "README.md"


def get_data_files():
    return [
        (
            "/usr/share/zayde-monitor/glade_files",
            [
                "glade_files/disk.glade",
                "glade_files/diskSidepane.glade",
                "glade_files/gpu.glade",
                "glade_files/gpuSidepane.glade",
                "glade_files/net.glade",
                "glade_files/netSidepane.glade",
                "glade_files/zayde_monitor.glade",
                "glade_files/filter_dialog.glade",
            ],
        ),
        (
            "/usr/share/zayde-monitor/icons",
            [
                "icons/ZaydeMonitor.png",
                "icons/choose_color.png",
                "icons/hide.png",
                "icons/reset-color.png",
                "icons/show.png",
            ],
        ),
        ("/usr/share/doc/zayde-monitor", ["AUTHORS", "README.md", "LICENSE"]),
        ("/usr/share/applications", ["zayde-monitor.desktop"]),
        (
            "/usr/share/glib-2.0/schemas",
            ["com.github.kendonream.zaydemonitor.gschema.xml"],
        ),
    ]


setup(
    name="zayde-monitor",
    version="1.0.0",
    description="System Monitor With UI Like Windows",
    url="https://www.Zaydeindustries.com",
    author="Kendon Ream",
    author_email="Kendonream@gmail.com",
    license="BSD-3-Clause",
    long_description=README_PATH.read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
        "Topic :: System :: Monitoring",
    ],
    include_package_data=True,
    exclude_package_data={"": ["__pycache__/*", "*.py[cod]"]},
    data_files=get_data_files(),
    install_requires=["psutil>=5.7.2", "PyGObject", "pycairo"],
    packages=find_packages(exclude=["*.__pycache__", "*.tests", "*.tests.*", "tests", "tests.*"]),
    entry_points={
        "console_scripts": [
            "zayde-monitor=zayde_monitor.zayde_monitor:start",
            "zayde-monitor.set_default=zayde_monitor.theme_setter:set_theme_default",
            "zayde-monitor.set_light=zayde_monitor.theme_setter:set_theme_light",
            "zayde-monitor.set_dark=zayde_monitor.theme_setter:set_theme_dark",
        ]
    },
)
