from pathlib import Path

from setuptools import find_packages, setup


PROJECT_ROOT = Path(__file__).resolve().parent
README_PATH = PROJECT_ROOT / "README.md"


def get_data_files():
    return [
        (
            "/usr/share/z-mon/glade_files",
            [
                "glade_files/disk.glade",
                "glade_files/diskSidepane.glade",
                "glade_files/gpu.glade",
                "glade_files/gpuSidepane.glade",
                "glade_files/net.glade",
                "glade_files/netSidepane.glade",
                "glade_files/z_mon.glade",
                "glade_files/filter_dialog.glade",
            ],
        ),
        (
            "/usr/share/z-mon/icons",
            [
                "icons/Z-MON.png",
                "icons/choose_color.png",
                "icons/hide.png",
                "icons/reset-color.png",
                "icons/show.png",
            ],
        ),
        ("/usr/share/doc/z-mon", ["AUTHORS", "README.md", "LICENSE"]),
        ("/usr/share/applications", ["z-mon.desktop"]),
        (
            "/usr/share/glib-2.0/schemas",
            ["com.github.kendonream17.zmon.gschema.xml"],
        ),
    ]


setup(
    name="z-mon",
    version="1.0.0",
    description="System Monitor With UI Like Windows",
    url="https://github.com/kendonream17/Z-MON",
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
            "z-mon=z_mon.z_mon:start",
            "z-mon.set_default=z_mon.theme_setter:set_theme_default",
            "z-mon.set_light=z_mon.theme_setter:set_theme_light",
            "z-mon.set_dark=z_mon.theme_setter:set_theme_dark",
        ]
    },
)
