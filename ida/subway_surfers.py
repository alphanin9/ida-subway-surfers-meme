"""Subway Surfers for IDA: plays a video in a tab so your attention span survives the pwn chall.

Lives in plugins/subway_surfers/ next to ida-plugin.json, subway_player.py and the video.
Open it from View > Subway Surfers (or Ctrl+Shift+Alt+S); close it like any other tab.
"""

import os
import sys

import ida_idaapi
import ida_kernwin
from PySide6 import QtWidgets

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import subway_player  # noqa: E402

TITLE = "Subway Surfers"
ACTION_NAME = "subway_surfers:open"


class SubwayForm(ida_kernwin.PluginForm):
    def OnCreate(self, form):
        parent = self.FormToPyQtWidget(form)
        layout = QtWidgets.QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        self.player = subway_player.make_player(HERE, parent)
        layout.addWidget(self.player)

    def OnClose(self, form):
        self.player.stop()
        SubwayPlugin.form = None


class OpenHandler(ida_kernwin.action_handler_t):
    def activate(self, ctx):
        if SubwayPlugin.form is None:
            SubwayPlugin.form = SubwayForm()
            SubwayPlugin.form.Show(TITLE)
            ida_kernwin.set_dock_pos(TITLE, "IDA View-A", ida_kernwin.DP_TAB)
        else:
            ida_kernwin.activate_widget(ida_kernwin.find_widget(TITLE), True)
        return 1

    def update(self, ctx):
        return ida_kernwin.AST_ENABLE_ALWAYS


class SubwayPlugin(ida_idaapi.plugin_t):
    flags = ida_idaapi.PLUGIN_KEEP | ida_idaapi.PLUGIN_HIDE
    comment = "Subway Surfers in a tab"
    help = ""
    wanted_name = "Subway Surfers"
    wanted_hotkey = ""
    form = None

    def init(self):
        ida_kernwin.register_action(
            ida_kernwin.action_desc_t(
                ACTION_NAME,
                TITLE,
                OpenHandler(),
                "Ctrl+Shift+Alt+S",  # Ctrl+Alt+S is IDA's built-in Stack Trace
                "Open the Subway Surfers tab",
            )
        )
        attached = ida_kernwin.attach_action_to_menu("View/", ACTION_NAME, ida_kernwin.SETMENU_APP)
        cv2 = subway_player.cv2
        print(f"[subway] loaded: cv2={cv2 and cv2.__version__} video={subway_player.find_video(HERE)} menu={attached}")
        return ida_idaapi.PLUGIN_KEEP

    def run(self, arg):
        ida_kernwin.process_ui_action(ACTION_NAME)

    def term(self):
        ida_kernwin.unregister_action(ACTION_NAME)


def PLUGIN_ENTRY():
    return SubwayPlugin()
