"""Linux-backed pages that mirror Windows Task Manager sections."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import configparser
import os
import shlex
import shutil
import subprocess
from typing import Iterable

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk as g
from gi.repository import Gdk
import psutil as ps

from z_mon import APP_DISPLAY_NAME, config_dir
from z_mon.theme_setter import apply_theme_preference, current_theme_mode


OPTIONAL_TOOL_STATUS = {
    "dmidecode": "optional memory slot/speed details",
    "lshw": "optional network adapter vendor details",
    "nvidia-smi": "NVIDIA GPU metrics",
    "systemctl": "services and startup service details",
}

LIGHT_THEME_CSS = b"""
* {
  background-image: none;
  text-shadow: none;
  -gtk-icon-shadow: none;
}
window, .task-content, .task-page, viewport, scrolledwindow, notebook, stack, box, grid, paned {
  background-color: #f7f7f7;
  color: #1f1f1f;
}
label {
  color: #1f1f1f;
}
treeview.view, treeview.view header button {
  background-color: #ffffff;
  color: #1f1f1f;
}
treeview.view:selected {
  background-color: #cfe8ff;
  color: #111111;
}
button, button.flat, .app-button, menubar, menu, menuitem, checkbutton, radiobutton {
  background-color: #ffffff;
  color: #1f1f1f;
  border-color: rgba(0, 0, 0, 0.18);
}
button:hover, .app-button:hover, menuitem:hover {
  background-color: #eeeeee;
}
button:active, button:checked, .app-button:active, .app-button.selected, checkbutton:checked, radiobutton:checked {
  background-color: #dceeff;
  color: #111111;
  border-color: #6aa7df;
}
button:disabled, .app-button:disabled {
  background-color: #eeeeee;
  color: #777777;
}
.task-sidebar {
  background-color: #f0f0f0;
  border-right-color: rgba(0, 0, 0, 0.16);
}
.nav-button.selected {
  background-color: #dceeff;
  border-color: #6aa7df;
}
.command-bar {
  background-color: #f7f7f7;
  border-bottom-color: rgba(0, 0, 0, 0.14);
}
entry {
  background-color: #ffffff;
  color: #1f1f1f;
}
popover, dialog {
  background-color: #f7f7f7;
  color: #1f1f1f;
}
"""

DARK_THEME_CSS = b"""
* {
  background-image: none;
  text-shadow: none;
  -gtk-icon-shadow: none;
}
window, .task-content, .task-page, viewport, scrolledwindow, notebook, stack, box, grid, paned {
  background-color: #202020;
  color: #f2f2f2;
}
label {
  color: #f2f2f2;
}
treeview.view, treeview.view header button {
  background-color: #1b1b1b;
  color: #f2f2f2;
}
treeview.view:selected {
  background-color: #27496d;
  color: #ffffff;
}
button, button.flat, .app-button, menubar, menu, menuitem, checkbutton, radiobutton {
  background-color: #2d2d2d;
  color: #f2f2f2;
  border-color: rgba(255, 255, 255, 0.18);
}
button:hover, .app-button:hover, menuitem:hover {
  background-color: #383838;
}
button:active, button:checked, .app-button:active, .app-button.selected, checkbutton:checked, radiobutton:checked {
  background-color: #27384a;
  color: #ffffff;
  border-color: #5d9bd3;
}
button:disabled, .app-button:disabled {
  background-color: #242424;
  color: #8c8c8c;
}
.task-sidebar {
  background-color: #181818;
  border-right-color: rgba(255, 255, 255, 0.14);
}
.nav-button.selected {
  background-color: #27384a;
  border-color: #5d9bd3;
}
.command-bar {
  background-color: #202020;
  border-bottom-color: rgba(255, 255, 255, 0.12);
}
entry {
  background-color: #2d2d2d;
  color: #f2f2f2;
}
popover, dialog {
  background-color: #202020;
  color: #f2f2f2;
}
"""


def collect_runtime_diagnostics() -> list[tuple[str, str, str]]:
    rows = []
    for command, purpose in OPTIONAL_TOOL_STATUS.items():
        rows.append((command, "Available" if shutil.which(command) else "Missing", purpose))
    rows.append(("display", "Available" if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY") else "Missing", "GTK application display"))
    return rows


def byte_to_human(value, persec=True):
    if value > 1024:
        if value > 1048576:
            if value > 1073741824:
                if value > 1073741824 * 1024:
                    scalefactor = 1073741824 * 1024
                    suffix = "TiB"
                else:
                    scalefactor = 1073741824
                    suffix = "GiB"
            else:
                scalefactor = 1048576
                suffix = "MiB"
        else:
            scalefactor = 1024
            suffix = "KiB"
    else:
        return "{:.1f} ".format(0) + ("KiB/s" if persec else "KiB")

    if persec:
        suffix += "/s"
    return "{:.1f} ".format(value / scalefactor) + suffix


CPU_HISTORY_SECONDS = 60
CPU_HISTORY_FILE = config_dir / "app_history.tsv"


@dataclass
class StartupEntry:
    name: str
    kind: str
    enabled: str
    command: str
    source: str


@dataclass
class ServiceEntry:
    unit: str
    load: str
    active: str
    sub: str
    description: str


def _safe_text(value) -> str:
    if value is None:
        return ""
    return str(value)


def _run(command: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(command, check=False, capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return None


def _iter_processes(attrs: Iterable[str]):
    for proc in ps.process_iter(attrs):
        try:
            yield proc
        except (ps.NoSuchProcess, ps.ZombieProcess):
            continue


def _process_name(proc: ps.Process) -> str:
    try:
        return proc.info.get("name") or proc.name() or str(proc.pid)
    except (ps.Error, OSError):
        return str(getattr(proc, "pid", ""))


def _process_command(proc: ps.Process) -> str:
    try:
        cmdline = proc.info.get("cmdline") if hasattr(proc, "info") else proc.cmdline()
        if cmdline:
            return shlex.join(cmdline)
    except (ps.Error, OSError):
        pass
    return _process_name(proc)


def _read_app_history() -> dict[str, tuple[float, int, int]]:
    history: dict[str, tuple[float, int, int]] = {}
    if not CPU_HISTORY_FILE.exists():
        return history

    try:
        for line in CPU_HISTORY_FILE.read_text(encoding="utf-8").splitlines():
            name, cpu, read_bytes, write_bytes = line.split("\t", 3)
            history[name] = (float(cpu), int(read_bytes), int(write_bytes))
    except (OSError, ValueError):
        return {}
    return history


def _write_app_history(history: dict[str, tuple[float, int, int]]) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{name}\t{cpu:.2f}\t{read_bytes}\t{write_bytes}"
        for name, (cpu, read_bytes, write_bytes) in sorted(history.items())
    ]
    CPU_HISTORY_FILE.write_text("\n".join(lines), encoding="utf-8")


def collect_app_history() -> list[tuple[str, str, str, str]]:
    history = _read_app_history()
    current = defaultdict(lambda: [0.0, 0, 0])

    for proc in _iter_processes(["name", "cpu_percent"]):
        name = _process_name(proc)
        try:
            current[name][0] += float(proc.cpu_percent(interval=None)) / max(ps.cpu_count() or 1, 1)
            io = proc.io_counters()
            current[name][1] += int(io.read_bytes)
            current[name][2] += int(io.write_bytes)
        except (ps.AccessDenied, ps.NoSuchProcess, ps.ZombieProcess, OSError):
            continue

    for name, (cpu, read_bytes, write_bytes) in current.items():
        old_cpu, old_read, old_write = history.get(name, (0.0, 0, 0))
        history[name] = (old_cpu + cpu, max(old_read, read_bytes), max(old_write, write_bytes))

    _write_app_history(history)
    return [
        (name, f"{cpu / CPU_HISTORY_SECONDS:.1f}%", byte_to_human(read_bytes, False), byte_to_human(write_bytes, False))
        for name, (cpu, read_bytes, write_bytes) in sorted(history.items(), key=lambda item: item[1][0], reverse=True)
    ]


def collect_startup_entries() -> list[StartupEntry]:
    entries: list[StartupEntry] = []
    locations = [
        Path("/etc/xdg/autostart"),
        Path.home() / ".config" / "autostart",
    ]

    for directory in locations:
        if not directory.exists():
            continue
        for desktop_file in sorted(directory.glob("*.desktop")):
            parser = configparser.ConfigParser(interpolation=None)
            try:
                parser.read(desktop_file, encoding="utf-8")
                section = parser["Desktop Entry"]
            except (configparser.Error, KeyError, OSError):
                continue
            name = section.get("Name", desktop_file.stem)
            command = section.get("Exec", "")
            enabled = "Disabled" if section.getboolean("Hidden", fallback=False) else "Enabled"
            entries.append(StartupEntry(name, "Desktop app", enabled, command, str(desktop_file)))

    systemctl = shutil.which("systemctl")
    if systemctl:
        result = _run([systemctl, "--user", "list-unit-files", "--type=service", "--no-legend", "--no-pager"])
        if result and result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1] in {"enabled", "disabled", "static"}:
                    entries.append(StartupEntry(parts[0], "User service", parts[1].title(), "", "systemd --user"))

    return entries


def collect_users() -> list[tuple[str, str, str, str, str]]:
    sessions = defaultdict(set)
    for user in ps.users():
        sessions[user.name].add(user.terminal or user.host or "local")

    totals = defaultdict(lambda: [0.0, 0, 0])
    for proc in _iter_processes(["username", "memory_info", "cpu_percent"]):
        try:
            username = proc.info.get("username") or "unknown"
            totals[username][0] += float(proc.cpu_percent(interval=None)) / max(ps.cpu_count() or 1, 1)
            totals[username][1] += int(proc.info["memory_info"].rss)
            totals[username][2] += 1
        except (ps.AccessDenied, ps.NoSuchProcess, ps.ZombieProcess, OSError, KeyError):
            continue

    names = sorted(set(sessions) | set(totals))
    return [
        (
            name,
            ", ".join(sorted(sessions.get(name, {"no active session"}))),
            str(totals[name][2]),
            f"{totals[name][0]:.1f}%",
            byte_to_human(totals[name][1], False),
        )
        for name in names
    ]


def collect_details() -> list[tuple[int, str, str, str, str, str, str, str]]:
    rows = []
    for proc in _iter_processes(["pid", "name", "username", "status", "memory_info", "cpu_percent", "nice", "cmdline"]):
        try:
            rows.append(
                (
                    proc.pid,
                    _process_name(proc),
                    _safe_text(proc.info.get("status")),
                    _safe_text(proc.info.get("username")),
                    f"{float(proc.cpu_percent(interval=None)) / max(ps.cpu_count() or 1, 1):.1f}%",
                    byte_to_human(proc.info["memory_info"].rss, False),
                    _safe_text(proc.info.get("nice")),
                    _process_command(proc),
                )
            )
        except (ps.AccessDenied, ps.NoSuchProcess, ps.ZombieProcess, OSError, KeyError):
            continue
    return sorted(rows, key=lambda row: row[0])


def collect_services() -> tuple[list[ServiceEntry], str | None]:
    systemctl = shutil.which("systemctl")
    if not systemctl:
        return [], "systemctl is not installed; service management is unsupported on this system."

    result = _run([systemctl, "list-units", "--type=service", "--all", "--no-legend", "--no-pager"])
    if not result or result.returncode != 0:
        return [], "systemd services are unavailable or cannot be queried in this session."

    services: list[ServiceEntry] = []
    for line in result.stdout.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        services.append(ServiceEntry(parts[0], parts[1], parts[2], parts[3], parts[4]))
    return services, None


def _make_store(columns: tuple[type, ...]) -> g.ListStore:
    return g.ListStore(*columns)


def _make_tree(store: g.ListStore, columns: list[tuple[str, int]], selectable: bool = True) -> g.TreeView:
    tree = g.TreeView(model=store)
    tree.set_headers_visible(True)
    tree.set_grid_lines(g.TreeViewGridLines.HORIZONTAL)
    tree.get_selection().set_mode(g.SelectionMode.SINGLE if selectable else g.SelectionMode.NONE)
    for title, index in columns:
        renderer = g.CellRendererText()
        renderer.props.ellipsize = 3
        column = g.TreeViewColumn(title, renderer, text=index)
        column.set_resizable(True)
        column.set_min_width(110)
        tree.append_column(column)
    return tree


def _page_shell(title: str) -> tuple[g.Box, g.Box]:
    page = g.Box(orientation=g.Orientation.VERTICAL, spacing=8)
    page.get_style_context().add_class("task-page")
    header = g.Box(orientation=g.Orientation.HORIZONTAL, spacing=8)
    header.set_margin_start(12)
    header.set_margin_end(12)
    header.set_margin_top(12)
    label = g.Label(label=title)
    label.set_halign(g.Align.START)
    label.get_style_context().add_class("task-page-title")
    header.pack_start(label, True, True, 0)
    page.pack_start(header, False, False, 0)
    return page, header


def _append_tree_page(notebook: g.Notebook, title: str, store: g.ListStore, columns: list[tuple[str, int]]) -> tuple[g.Box, g.TreeView, g.Button]:
    page, header = _page_shell(title)
    refresh = g.Button(label="Refresh")
    refresh.get_style_context().add_class("app-button")
    header.pack_end(refresh, False, False, 0)
    scroller = g.ScrolledWindow()
    scroller.set_hexpand(True)
    scroller.set_vexpand(True)
    tree = _make_tree(store, columns)
    scroller.add(tree)
    page.pack_start(scroller, True, True, 0)
    notebook.append_page(page, g.Label(label=title))
    page.show_all()
    return page, tree, refresh


class TaskPages:
    """Owns the added Task Manager parity pages."""

    def __init__(self, window, notebook: g.Notebook):
        self.window = window
        self.notebook = notebook
        gtk_settings = g.Settings.get_default()
        self.system_theme_name = self._detect_system_theme_name(gtk_settings)
        self.system_prefer_dark = bool(gtk_settings.get_property("gtk-application-prefer-dark-theme")) if gtk_settings else False
        self.theme_css_provider = None

        self.app_history_store = _make_store((str, str, str, str))
        self.startup_store = _make_store((str, str, str, str, str))
        self.users_store = _make_store((str, str, str, str, str))
        self.details_store = _make_store((int, str, str, str, str, str, str, str))
        self.services_store = _make_store((str, str, str, str, str))
        self.diagnostics_store = _make_store((str, str, str))

        _page, _tree, refresh = _append_tree_page(
            notebook,
            "App history",
            self.app_history_store,
            [("Name", 0), ("CPU time", 1), ("Reads", 2), ("Writes", 3)],
        )
        refresh.connect("clicked", lambda _button: self.refresh_app_history())
        _page, _tree, refresh = _append_tree_page(
            notebook,
            "Startup apps",
            self.startup_store,
            [("Name", 0), ("Type", 1), ("Status", 2), ("Command", 3), ("Source", 4)],
        )
        refresh.connect("clicked", lambda _button: self.refresh_startup())
        _page, _tree, refresh = _append_tree_page(
            notebook,
            "Users",
            self.users_store,
            [("User", 0), ("Session", 1), ("Processes", 2), ("CPU", 3), ("Memory", 4)],
        )
        refresh.connect("clicked", lambda _button: self.refresh_users())
        _page, self.details_tree, refresh = _append_tree_page(
            notebook,
            "Details",
            self.details_store,
            [("PID", 0), ("Name", 1), ("Status", 2), ("User", 3), ("CPU", 4), ("Memory", 5), ("Nice", 6), ("Command", 7)],
        )
        refresh.connect("clicked", lambda _button: self.refresh_details())
        _page, self.services_tree, refresh = _append_tree_page(
            notebook,
            "Services",
            self.services_store,
            [("Unit", 0), ("Load", 1), ("Active", 2), ("Sub", 3), ("Description", 4)],
        )
        refresh.connect("clicked", lambda _button: self.refresh_services())
        self._append_settings_page()
        _page, _tree, refresh = _append_tree_page(
            notebook,
            "Diagnostics",
            self.diagnostics_store,
            [("Backend", 0), ("Status", 1), ("Used for", 2)],
        )
        refresh.connect("clicked", lambda _button: self.refresh_diagnostics())
        self._attach_actions()
        self.refresh_all()

    def _detect_system_theme_name(self, gtk_settings):
        result = _run(["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"])
        if result and result.returncode == 0:
            theme_name = result.stdout.strip().strip("'")
            if theme_name:
                return theme_name
        if gtk_settings:
            return gtk_settings.get_property("gtk-theme-name")
        return None

    def _attach_actions(self) -> None:
        self._add_action_button("Details", "End task", self.end_selected_process)
        self._add_action_button("Details", "Efficiency mode", self.efficiency_selected_process)
        self._add_action_button("Details", "Open file location", self.open_selected_process_location)
        self._add_action_button("Details", "Run new task", self.run_new_task)
        self._add_action_button("Services", "Start", lambda: self.service_action("start"))
        self._add_action_button("Services", "Stop", lambda: self.service_action("stop"))
        self._add_action_button("Services", "Restart", lambda: self.service_action("restart"))

    def _add_action_button(self, page_title: str, label: str, callback) -> None:
        page_num = {
            self.notebook.get_tab_label_text(self.notebook.get_nth_page(index)): index
            for index in range(self.notebook.get_n_pages())
        }.get(page_title)
        if page_num is None:
            return
        page = self.notebook.get_nth_page(page_num)
        header = page.get_children()[0]
        button = g.Button(label=label)
        button.get_style_context().add_class("app-button")
        button.connect("clicked", lambda _button: callback())
        header.pack_end(button, False, False, 0)
        header.show_all()

    def _append_settings_page(self) -> None:
        page, _header = _page_shell("Settings")
        grid = g.Grid(column_spacing=16, row_spacing=12)
        grid.set_margin_start(16)
        grid.set_margin_end(16)
        grid.set_margin_top(8)
        settings = [
            ("Default start page", "Processes"),
            ("Update speed", "Controlled from View > Update Speed"),
            ("Data directory", str(config_dir)),
            ("Linux backend", "psutil, XDG autostart, systemd when available"),
            ("Diagnostics", "See Diagnostics for optional backend availability"),
        ]
        row = 0
        self._loading_theme_controls = True
        theme_label = g.Label(label="Theme")
        theme_label.set_halign(g.Align.START)
        theme_label.get_style_context().add_class("settings-key")
        theme_box = g.Box(orientation=g.Orientation.HORIZONTAL, spacing=8)
        self.theme_buttons = {}
        first_button = None
        for mode, label in (("system", "System"), ("light", "Light"), ("dark", "Dark")):
            button = g.RadioButton.new_with_label_from_widget(first_button, label)
            if first_button is None:
                first_button = button
            button.connect("toggled", self._on_theme_mode_toggled, mode)
            theme_box.pack_start(button, False, False, 0)
            self.theme_buttons[mode] = button
        active_mode = current_theme_mode()
        self.theme_buttons.get(active_mode, self.theme_buttons["system"]).set_active(True)
        self._loading_theme_controls = False
        grid.attach(theme_label, 0, row, 1, 1)
        grid.attach(theme_box, 1, row, 1, 1)
        row += 1
        self.theme_status_label = g.Label(label="Theme changes apply immediately.")
        self.theme_status_label.set_halign(g.Align.START)
        grid.attach(g.Label(label=""), 0, row, 1, 1)
        grid.attach(self.theme_status_label, 1, row, 1, 1)
        row += 1

        for name, value in settings:
            left = g.Label(label=name)
            left.set_halign(g.Align.START)
            left.get_style_context().add_class("settings-key")
            right = g.Label(label=value)
            right.set_halign(g.Align.START)
            right.set_selectable(True)
            grid.attach(left, 0, row, 1, 1)
            grid.attach(right, 1, row, 1, 1)
            row += 1
        page.pack_start(grid, False, False, 0)
        self.notebook.append_page(page, g.Label(label="Settings"))
        page.show_all()

    def _on_theme_mode_toggled(self, button, mode):
        if not button.get_active() or getattr(self, "_loading_theme_controls", False):
            return
        try:
            theme_name = apply_theme_preference(mode)
        except (OSError, RuntimeError, ValueError) as exc:
            self.theme_status_label.set_text(f"Unable to set theme mode: {exc}")
            return
        self._apply_theme_live(mode, theme_name)
        if mode == "system":
            self.theme_status_label.set_text("Theme set to System.")
        else:
            self.theme_status_label.set_text(f"Theme set to {theme_name}.")

    def _apply_theme_live(self, mode, theme_name):
        gtk_settings = g.Settings.get_default()
        if not gtk_settings:
            return
        if mode == "system":
            if self.system_theme_name:
                gtk_settings.set_property("gtk-theme-name", self.system_theme_name)
            gtk_settings.set_property("gtk-application-prefer-dark-theme", self.system_prefer_dark)
            self._remove_app_theme_css()
            self._force_style_refresh()
            return
        if mode == "dark":
            gtk_settings.set_property("gtk-application-prefer-dark-theme", True)
        gtk_settings.set_property("gtk-theme-name", theme_name)
        gtk_settings.set_property("gtk-application-prefer-dark-theme", mode == "dark")
        self._apply_app_theme_css(mode)
        self._force_style_refresh()

    def _apply_app_theme_css(self, mode):
        self._remove_app_theme_css()
        screen = Gdk.Screen.get_default()
        if not screen:
            return
        css = DARK_THEME_CSS if mode == "dark" else LIGHT_THEME_CSS
        provider = g.CssProvider()
        provider.load_from_data(css)
        g.StyleContext.add_provider_for_screen(screen, provider, g.STYLE_PROVIDER_PRIORITY_USER)
        self.theme_css_provider = provider

    def _remove_app_theme_css(self):
        screen = Gdk.Screen.get_default()
        if screen and self.theme_css_provider:
            g.StyleContext.remove_provider_for_screen(screen, self.theme_css_provider)
        self.theme_css_provider = None

    def _force_style_refresh(self):
        while g.events_pending():
            g.main_iteration_do(False)
        if self.window:
            self.window.queue_draw()
        screen = Gdk.Screen.get_default()
        if screen:
            for gtk_window in g.Window.list_toplevels():
                gtk_window.queue_draw()

    def refresh_all(self) -> None:
        self.refresh_app_history()
        self.refresh_startup()
        self.refresh_users()
        self.refresh_details()
        self.refresh_services()
        self.refresh_diagnostics()

    def refresh_visible(self) -> None:
        page = self.notebook.get_current_page()
        title = self.notebook.get_tab_label_text(self.notebook.get_nth_page(page))
        {
            "App history": self.refresh_app_history,
            "Startup apps": self.refresh_startup,
            "Users": self.refresh_users,
            "Details": self.refresh_details,
            "Services": self.refresh_services,
            "Diagnostics": self.refresh_diagnostics,
        }.get(title, lambda: None)()

    def _replace_rows(self, store: g.ListStore, rows: Iterable[tuple]) -> None:
        store.clear()
        for row in rows:
            store.append(row)

    def refresh_app_history(self) -> None:
        self._replace_rows(self.app_history_store, collect_app_history())

    def refresh_startup(self) -> None:
        self._replace_rows(self.startup_store, [(e.name, e.kind, e.enabled, e.command, e.source) for e in collect_startup_entries()])

    def refresh_users(self) -> None:
        self._replace_rows(self.users_store, collect_users())

    def refresh_details(self) -> None:
        self._replace_rows(self.details_store, collect_details())

    def refresh_services(self) -> None:
        services, warning = collect_services()
        if warning:
            self._replace_rows(self.services_store, [("Unsupported", "", "", "", warning)])
        else:
            self._replace_rows(self.services_store, [(s.unit, s.load, s.active, s.sub, s.description) for s in services])

    def refresh_diagnostics(self) -> None:
        self._replace_rows(self.diagnostics_store, collect_runtime_diagnostics())

    def _selected_details_pid(self) -> int | None:
        model, iterator = self.details_tree.get_selection().get_selected()
        if iterator is None:
            return None
        return int(model[iterator][0])

    def _selected_service(self) -> str | None:
        model, iterator = self.services_tree.get_selection().get_selected()
        if iterator is None:
            return None
        unit = str(model[iterator][0])
        return unit if unit and unit != "Unsupported" else None

    def end_selected_process(self) -> None:
        pid = self._selected_details_pid()
        if pid is None:
            return
        try:
            ps.Process(pid).terminate()
        except (ps.Error, OSError) as exc:
            self._message(f"Unable to end process {pid}: {exc}")
        self.refresh_details()

    def efficiency_selected_process(self) -> None:
        pid = self._selected_details_pid()
        if pid is None:
            return
        try:
            ps.Process(pid).nice(10)
            ionice = shutil.which("ionice")
            if ionice:
                _run([ionice, "-c", "3", "-p", str(pid)])
        except (ps.Error, OSError) as exc:
            self._message(f"Unable to lower priority for process {pid}: {exc}")
        self.refresh_details()

    def open_selected_process_location(self) -> None:
        pid = self._selected_details_pid()
        if pid is None:
            return
        try:
            exe = ps.Process(pid).exe()
            folder = str(Path(exe).parent)
        except (ps.Error, OSError) as exc:
            self._message(f"Unable to resolve process location: {exc}")
            return
        opener = shutil.which("xdg-open")
        if opener:
            subprocess.Popen([opener, folder], start_new_session=True)
        else:
            self._message(f"Process location: {folder}")

    def run_new_task(self) -> None:
        dialog = g.Dialog(title="Run new task", transient_for=self.window, modal=True)
        dialog.add_buttons("Cancel", g.ResponseType.CANCEL, "Run", g.ResponseType.OK)
        entry = g.Entry()
        entry.set_activates_default(True)
        entry.set_placeholder_text("Command")
        dialog.get_content_area().add(entry)
        dialog.set_default_response(g.ResponseType.OK)
        dialog.show_all()
        response = dialog.run()
        command = entry.get_text().strip()
        dialog.destroy()
        if response == g.ResponseType.OK and command:
            try:
                subprocess.Popen(shlex.split(command), start_new_session=True)
            except (OSError, ValueError) as exc:
                self._message(f"Unable to run task: {exc}")

    def service_action(self, action: str) -> None:
        unit = self._selected_service()
        systemctl = shutil.which("systemctl")
        if not unit or not systemctl:
            return
        result = _run([systemctl, action, unit])
        if not result or result.returncode != 0:
            message = result.stderr.strip() if result else "systemctl is unavailable"
            self._message(f"Unable to {action} {unit}: {message}")
        self.refresh_services()

    def _message(self, text: str) -> None:
        dialog = g.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=g.MessageType.INFO,
            buttons=g.ButtonsType.OK,
            text=APP_DISPLAY_NAME,
        )
        dialog.format_secondary_text(text)
        dialog.run()
        dialog.destroy()
