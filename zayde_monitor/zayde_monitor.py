#!/usr/bin/env python3

from gi import require_version

require_version("Gtk", "3.0")
require_version("Wnck", "3.0")
require_version("Gdk", "3.0")
import gi
try:
    gi.require_foreign("cairo")
except ImportError as exc:
    raise RuntimeError(
        "Cairo GI bindings are missing. Install the system package "
        "'python3-gi-cairo' and relaunch Zayde Monitor."
    ) from exc

try:
    from rooter import theme_agent
except ImportError:
    from zayde_monitor.rooter import theme_agent

theme_agent()

import os
import subprocess
import sys
import time

from gi.repository import Gdk, GdkPixbuf, Gio, GLib as go, Gtk as g
import psutil as ps

from zayde_monitor import PROJECT_ROOT, SCHEMA_FILENAME, SETTINGS_SCHEMA_ID, files_dir, icon_file, log_dir
from zayde_monitor.cpu import cpuInit, cpuUpdate
from zayde_monitor.disk import diskTabUpdate, diskinit
from zayde_monitor.filter_prefs import filter_init
from zayde_monitor.gproc import (
    column_button_press,
    column_header_selection,
    kill_process,
    procInit,
    procUpdate,
    row_selected,
)
from zayde_monitor.gpu import gpuUpdate, gpuinit
from zayde_monitor.mem import memoryTabUpdate, memorytabinit
from zayde_monitor.net import netUpdate, netinit
from zayde_monitor.sidepane import (
    color_profile_initializer,
    device_show_hide_menu_callback,
    feature_setup,
    sidePaneUpdate,
    sidepaneinit,
)


MIN_PSUTIL_VERSION = (5, 7, 2)
VERSION_INT = 2

if "GSETTINGS_SCHEMA_DIR" not in os.environ and (PROJECT_ROOT / SCHEMA_FILENAME).exists():
    os.environ["GSETTINGS_SCHEMA_DIR"] = str(PROJECT_ROOT)


def _parse_version(version_text):
    parts = []
    for item in version_text.split("."):
        digits = "".join(ch for ch in item if ch.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def _bind_component_handlers(instance):
    handlers = {
        "cpuInit": cpuInit,
        "cpuUpdate": cpuUpdate,
        "memoryinitalisation": memorytabinit,
        "memoryTab": memoryTabUpdate,
        "sidepaneinitialisation": sidepaneinit,
        "sidepaneUpdate": sidePaneUpdate,
        "diskinitialisation": diskinit,
        "disktabUpdate": diskTabUpdate,
        "netinitialisation": netinit,
        "netTabUpdate": netUpdate,
        "gpuinitialisation": gpuinit,
        "gpuTabUpdate": gpuUpdate,
        "procinitialisation": procInit,
        "procUpdate": procUpdate,
        "row_selected": row_selected,
        "kill_process": kill_process,
        "column_button_press": column_button_press,
        "column_header_selection": column_header_selection,
        "filter_init": filter_init,
    }

    for name, func in handlers.items():
        setattr(instance, name, func.__get__(instance, instance.__class__))


def _queue_draw(widget):
    if widget is not None:
        widget.queue_draw()


def _queue_widget_graphs(widget, attributes):
    for attribute in attributes:
        _queue_draw(getattr(widget, attribute, None))


def _draw_graph(cr, width, height, values, maximum, color, rectangle_color, fill_alpha=0.2):
    scalingfactor = height / maximum if maximum else 0

    cr.set_source_rgba(*rectangle_color, 1)
    cr.set_line_width(3)
    cr.rectangle(0, 0, width, height)
    cr.stroke()

    stepsize = width / 99.0

    cr.set_line_width(1.5)
    cr.set_source_rgba(*color, 1)
    cr.move_to(0, scalingfactor * (maximum - values[0]))
    for i in range(0, 99):
        cr.line_to((i + 1) * stepsize, scalingfactor * (maximum - values[i + 1]))
    cr.stroke_preserve()

    cr.set_source_rgba(*color, fill_alpha)
    cr.line_to(width, height)
    cr.line_to(0, height)
    cr.move_to(0, scalingfactor * (maximum - values[0]))
    cr.fill()
    cr.stroke()


class whatsnew_notice_dialog(g.Dialog):
    """Class for the What's New dialog."""

    def __init__(self, parentWindow, parent):
        g.Dialog.__init__(self, "What's New", parentWindow, g.DialogFlags.MODAL)
        self.set_border_width(20)
        content_area = self.get_content_area()
        label = g.Label()
        label.set_markup(
            """
        <b><span size='20000'>New Feature #v1.x.x </span></b>
          * <b><big>Color Customizations</big></b>
              Color for each devices can be changed.
          * <b><big>Hide/Show Devices</big></b>
              Now each device can be hide permanantly.
          * <b><big>Bug fixes and Small Visual Improvements</big></b>
              For details visit:<a href='https://github.com/KendonReam/Zayde-Monitor'>https://github.com/KendonReam/Zayde-Monitor/</a>
            -------------------------------------------------------------------------------------------------
            <b>Previous highlights</b>
            -------------------------------------------------------------------------------------------------
          * <b><big>Filter Dialog</big></b>
              Can be accessed through : view->filter
              User can define his/her own filtering words to exclude the unwanted processes.
              Filter Dialog follow <b><big>strict semantic and formating rules</big></b> for adding a new entry.
              For more information of rules and filter dialog, visit:
              <a href='https://github.com/KendonReam/Zayde-Monitor/blob/master/DOCS.md#filter-dialog-view-filter'>https://github.com/KendonReam/Zayde-Monitor/blob/master/DOCS.md</a>
          * <b><big>Process Log Record</big></b>(at lower right corner in process tab)
          * <b><big>Log plotter</big></b>(Tools->Log_plot)
          * Bug fixes, optimisation and support for all desktop enviornments.
        """
        )
        content_area.add(label)
        self.show_all()


class MainWindow:
    """The main application controller."""

    flag = 0
    resizerflag = 0

    def __init__(self):
        stt = time.time()
        _bind_component_handlers(self)

        self.settings = Gio.Settings.new(SETTINGS_SCHEMA_ID)

        style_provider = g.CssProvider()
        with open(f"{os.path.dirname(os.path.abspath(__file__))}/style.css", "rb") as css:
            style_provider.load_from_data(css.read())

        g.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            g.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        self.builder = g.Builder()
        self.builder.add_from_file(os.path.join(files_dir, "zayde_monitor.glade"))
        self.builder.connect_signals(self)

        self.Window = self.builder.get_object("main_window")
        self.quit = self.builder.get_object("quit")
        self.quit.connect("activate", self.on_quit_activate)
        self.Window.set_icon_from_file(os.path.join(icon_file, "ZaydeMonitor.png"))

        self.performanceStack = self.builder.get_object("performancestack")
        self.process_tab_box = self.builder.get_object("process_tab_box")
        self.sidepaneBox = self.builder.get_object("sidepanebox")
        self.stack_counter = 2
        self.current_stack = 0
        self.device_stack_page_lookup = {"cpu": 0, "memory": 1}

        color_profile_initializer(self)

        self.cpuInit()
        self.memoryinitalisation()
        self.diskinitialisation()
        self.netinitialisation()
        self.gpuinitialisation()
        self.filter_init()
        self.procinitialisation()

        self.aboutdialog = self.builder.get_object("aboutdialog")
        about_logo_path = os.path.join(icon_file, "ZaydeMonitor.png")
        if os.path.exists(about_logo_path):
            self.aboutdialog.set_logo(GdkPixbuf.Pixbuf.new_from_file(about_logo_path))
        self.notebook = self.builder.get_object("notebook")
        self.notebook.set_current_page(self.settings.get_int("current-tab"))

        if self.notebook.get_current_page() != 0:
            self.process_tree_search_entry.hide()

        default_time_interval = 850
        self.timehandler = go.timeout_add(default_time_interval, self.updater)
        self.Processtimehandler = go.timeout_add(2000, self.procUpdate)

        self.update_dir_right = self.builder.get_object("update_right")
        self.update_dir_left = self.builder.get_object("update_left")
        self.update_dir_left.connect("toggled", self.on_set_left_update)
        self.update_dir_right.connect("toggled", self.on_set_right_update)
        self.update_graph_direction = 1
        self.update_dir_right.set_active(True)

        self.update_speed_low = self.builder.get_object("low")
        self.update_speed_normal = self.builder.get_object("normal")
        self.update_speed_high = self.builder.get_object("high")
        self.update_speed_paused = self.builder.get_object("paused")
        self.update_speed_low.connect("toggled", self.on_update_speed_change)
        self.update_speed_normal.connect("toggled", self.on_update_speed_change)
        self.update_speed_high.connect("toggled", self.on_update_speed_change)
        self.update_speed_paused.connect("toggled", self.on_update_speed_change)
        self.update_speed_normal.set_active(True)

        self.filter_button = self.builder.get_object("filter_button")
        self.filter_button.connect("activate", self.on_filter_dialog_activate)

        self.refreshing = 0
        feature_setup(self)
        self.post_init()
        self.sidepaneinitialisation()

        self.Window.show()

        position = self.settings.get_value("window-position")
        self.Window.move(position[0], position[1])

        size = self.settings.get_value("window-size")
        self.Window.resize(size[0], size[1])

        self.log_plot = self.builder.get_object("log_plot")
        self.notebook.connect("switch-page", self.on_notebook_page_change)

        if self.settings.get_int("version-int") != VERSION_INT:
            dialog = whatsnew_notice_dialog(self.Window, self)
            dialog.run()
            dialog.destroy()
            self.settings.set_int("version-int", VERSION_INT)

        if os.environ.get("ZAYDE_MONITOR_DEBUG"):
            print("total window", time.time() - stt)

    def post_init(self):
        self.grouping_for_color_profile = {
            "cpu": "cpu",
            "memory": "memory",
        }
        if self.isNvidiagpu:
            self.grouping_for_color_profile[self.gpuName] = "gpu"
        for i in self.disklist:
            self.grouping_for_color_profile[i] = "disk"
        for i in self.netNameList:
            self.grouping_for_color_profile[i] = "network"

        self.reverse_device_stack_page_lookup = {}
        for key in self.device_stack_page_lookup:
            self.reverse_device_stack_page_lookup[self.device_stack_page_lookup[key]] = key

        self.hidden_stack_page_numbers = []
        device_list = self.settings.get_value("hidden-device-list")
        for i in device_list:
            self.hidden_stack_page_numbers.append(self.device_stack_page_lookup[i])

        self.device_menu_items = {}
        self.show_hide_menu = self.builder.get_object("devices_menu")
        sub_menu = g.Menu()
        self.show_hide_menu.set_submenu(sub_menu)

        for key in self.device_stack_page_lookup:
            value = self.device_stack_page_lookup[key]
            item = g.CheckMenuItem(label=key)
            item.set_name(key)
            if value not in self.hidden_stack_page_numbers:
                item.set_active(True)
            else:
                item.set_active(False)
            item.connect("toggled", device_show_hide_menu_callback, self)
            self.device_menu_items[value] = item
            sub_menu.append(item)
        sub_menu.show_all()

    def on_log_plot_activate(self, widget):
        file_dialog = g.FileChooserDialog(
            title="Select Log File",
            parent=self.Window,
            action=g.FileChooserAction.OPEN,
            buttons=("Cancel", g.ResponseType.CANCEL, "Open", g.ResponseType.OK),
        )
        file_dialog.set_current_folder(str(log_dir))

        response = file_dialog.run()

        if response == g.ResponseType.OK:
            filename = file_dialog.get_filename()
            file_dialog.destroy()

            subprocess.Popen(
                [
                    sys.executable,
                    os.path.join(os.path.abspath(os.path.dirname(__file__)), "log_plotter.py"),
                    filename,
                ],
                start_new_session=True,
            )
        else:
            file_dialog.destroy()

    def on_notebook_page_change(self, object, page, page_num):
        if page_num != 0:
            self.process_tree_search_entry.hide()
        else:
            self.process_tree_search_entry.show()

    def on_menu_whatsnew(self, widget):
        dialog = whatsnew_notice_dialog(self.Window, self)
        dialog.run()
        dialog.destroy()

    def on_set_left_update(self, widget):
        if widget.get_active():
            self.update_dir_right.set_active(False)
            self.update_graph_direction = 0

            self.cpuUtilArray.reverse()
            for i in range(self.cpu_logical_cores):
                self.cpu_logical_cores_util_arrays[i].reverse()

            self.memUsedArray1.reverse()

            for i in range(self.numOfDisks):
                self.diskActiveArray[i].reverse()
                self.diskReadArray[i].reverse()
                self.diskWriteArray[i].reverse()

            for i in range(self.numOfNets):
                self.netSendArray[i].reverse()
                self.netReceiveArray[i].reverse()

            self.gpuUtilArray.reverse()
            self.gpuVramArray.reverse()
            self.gpuEncodingArray.reverse()
            self.gpuDecodingArray.reverse()

    def on_set_right_update(self, widget):
        if widget.get_active():
            self.update_dir_left.set_active(False)
            self.update_graph_direction = 1

            self.cpuUtilArray.reverse()
            for i in range(self.cpu_logical_cores):
                self.cpu_logical_cores_util_arrays[i].reverse()

            self.memUsedArray1.reverse()

            for i in range(self.numOfDisks):
                self.diskActiveArray[i].reverse()
                self.diskReadArray[i].reverse()
                self.diskWriteArray[i].reverse()

            for i in range(self.numOfNets):
                self.netSendArray[i].reverse()
                self.netReceiveArray[i].reverse()

            self.gpuUtilArray.reverse()
            self.gpuVramArray.reverse()
            self.gpuEncodingArray.reverse()
            self.gpuDecodingArray.reverse()

    def on_main_window_destroy(self, widget, data=None):
        self.settings.set_value("window-position", go.Variant("(ii)", self.Window.get_position()))
        self.settings.set_value("window-size", go.Variant("(ii)", self.Window.get_size()))
        self.settings.set_int("current-tab", self.notebook.get_current_page())

        l = []
        for i, row in enumerate(self.filter_list_store):
            l.append([])
            l[i] += [str(row[0]), row[1], str(row[2]), str(row[3])]
        self.settings.set_value("process-filter", go.Variant("aas", l))

        l.clear()
        for i in self.hidden_stack_page_numbers:
            l.append(self.reverse_device_stack_page_lookup[i])
        self.settings.set_value("hidden-device-list", go.Variant("as", l))

        l.clear()
        for i in self.color_profile:
            l.append(self.color_profile[i][0])
        self.settings.set_value("color-profile", go.Variant("a(ddd)", l))

        if self.log_file:
            self.log_file.close()

        g.main_quit()

    def on_quit_activate(self, menuitem, data=None):
        self.on_main_window_destroy(menuitem)

    def on_refresh_activate(self, menuitem, data=None):
        self.refreshing = 1

    def on_about_activate(self, menuitem, data=None):
        self.aboutdialog.run()
        self.aboutdialog.hide()

    def on_filter_dialog_activate(self, menuitem, data=None):
        self.filter_dialog.run()
        self.filter_dialog.hide()

    def updater(self):
        if self.refreshing:
            self.post_init()
            self.refreshing = 0

        if self.update_speed_paused.get_active():
            return True
        if self.notebook.get_current_page() != 0:
            self.cpuUpdate()
            self.memoryTab()
            self.disktabUpdate()
            self.netTabUpdate()
            self.gpuTabUpdate()
            self.sidepaneUpdate()

            _queue_draw(self.cpuDrawArea)
            _queue_draw(self.memDrawArea1)
            _queue_draw(self.memDrawArea2)
            _queue_draw(self.cpuSidePaneDrawArea)
            _queue_draw(self.memSidePaneDrawArea)
            for draw_area in getattr(self, "cpu_logical_cores_draw_areas", []):
                _queue_draw(draw_area)
            for widget in getattr(self, "diskWidgetList", {}).values():
                _queue_widget_graphs(widget, ("diskdrawarea1", "diskdrawarea2"))
            for widget in getattr(self, "netWidgetList", {}).values():
                _queue_widget_graphs(widget, ("netdrawarea",))
            _queue_widget_graphs(
                getattr(self, "gpuWidget", None),
                (
                    "gpuutildrawarea",
                    "gpuvramdrawarea",
                    "gpuencodingdrawarea",
                    "gpudecodingdrawarea",
                ),
            )
            for widget in getattr(self, "diskSidepaneWidgetList", {}).values():
                _queue_widget_graphs(widget, ("disksidepanedrawarea",))
            for widget in getattr(self, "netSidepaneWidgetList", {}).values():
                _queue_widget_graphs(widget, ("netsidepanedrawarea",))
            _queue_widget_graphs(getattr(self, "gpuSidePaneWidget", None), ("gpusidepanedrawarea",))
        return True

    def on_update_speed_change(self, widget):
        speed = 850
        if self.update_speed_low.get_active():
            speed = 1400
            self.update_speed_high.set_active(False)
            self.update_speed_normal.set_active(False)
            self.update_speed_paused.set_active(False)
        elif self.update_speed_normal.get_active():
            speed = 850
            self.update_speed_low.set_active(False)
            self.update_speed_high.set_active(False)
            self.update_speed_paused.set_active(False)
        elif self.update_speed_high.get_active():
            speed = 500
            self.update_speed_low.set_active(False)
            self.update_speed_normal.set_active(False)
            self.update_speed_paused.set_active(False)
        elif self.update_speed_paused.get_active():
            self.update_speed_low.set_active(False)
            self.update_speed_normal.set_active(False)
            self.update_speed_high.set_active(False)

        if not self.update_speed_paused.get_active():
            go.source_remove(self.timehandler)
            self.timehandler = go.timeout_add(speed, self.updater)

    def on_cpuDrawArea_draw(self, dr, cr):
        cr.set_line_width(2)
        color = self.color_profile["cpu"][0]
        rectangle_color = self.color_profile["cpu"][1]
        width = self.cpuDrawArea.get_allocated_width()
        height = self.cpuDrawArea.get_allocated_height()
        _draw_graph(cr, width, height, self.cpuUtilArray, 100.0, color, rectangle_color)
        return False

    def on_cpu_logical_drawing(self, dr, cr):
        index = int(dr.get_name())
        color = self.color_profile["cpu"][0]
        rectangle_color = self.color_profile["cpu"][1]
        width = dr.get_allocated_width()
        height = dr.get_allocated_height()
        _draw_graph(
            cr,
            width,
            height,
            self.cpu_logical_cores_util_arrays[index],
            100.0,
            color,
            rectangle_color,
            fill_alpha=0.15,
        )
        return False

    def on_memDrawArea1_draw(self, dr, cr):
        cr.set_line_width(2)
        color = self.color_profile["memory"][0]
        rectangle_color = self.color_profile["memory"][1]
        width = self.memDrawArea1.get_allocated_width()
        height = self.memDrawArea1.get_allocated_height()
        _draw_graph(cr, width, height, self.memUsedArray1, self.memTotal, color, rectangle_color)
        return False

    def on_memDrawArea2_draw(self, dr, cr):
        color = self.color_profile["memory"][0]
        rectangle_color = self.color_profile["memory"][1]
        width = self.memDrawArea2.get_allocated_width()
        height = self.memDrawArea2.get_allocated_height()

        used_ratio = 0 if not self.memTotal else min(max(self.usedd / self.memTotal, 0), 1)

        cr.set_source_rgba(*rectangle_color, 1)
        cr.set_line_width(3)
        cr.rectangle(0, 0, width, height)
        cr.stroke()

        cr.set_source_rgba(*color, 0.25)
        cr.rectangle(0, 0, width * used_ratio, height)
        cr.fill()

        cr.set_source_rgba(*color, 1)
        cr.set_line_width(1.5)
        cr.rectangle(0, 0, width * used_ratio, height)
        cr.stroke()
        return False

    def on_cpuSidePaneDrawArea_draw(self, dr, cr):
        cr.set_line_width(2)
        color = self.color_profile["cpu"][0]
        rectangle_color = self.color_profile["cpu"][1]
        width = self.cpuSidePaneDrawArea.get_allocated_width()
        height = self.cpuSidePaneDrawArea.get_allocated_height()
        _draw_graph(cr, width, height, self.cpuUtilArray, 100.0, color, rectangle_color, fill_alpha=0.25)
        return False

    def on_memSidePaneDrawArea_draw(self, dr, cr):
        cr.set_line_width(2)
        color = self.color_profile["memory"][0]
        rectangle_color = self.color_profile["memory"][1]
        width = self.memSidePaneDrawArea.get_allocated_width()
        height = self.memSidePaneDrawArea.get_allocated_height()
        _draw_graph(cr, width, height, self.memUsedArray1, self.memTotal, color, rectangle_color)
        return False


def validate_runtime():
    version = _parse_version(ps.__version__)
    if version and version < MIN_PSUTIL_VERSION:
        raise RuntimeError(
            f"psutil>={'.'.join(map(str, MIN_PSUTIL_VERSION))} is required, found {ps.__version__}."
        )


def start():
    validate_runtime()
    MainWindow()
    g.main()


if __name__ == "__main__":
    start()
