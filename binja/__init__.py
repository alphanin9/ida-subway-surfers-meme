"""Subway Surfers for Binary Ninja: plays a video in a sidebar panel.

Lives in plugins/subway_surfers/ next to subway_player.py and the video. Click the play icon
in the right sidebar to show it; playback pauses while the panel is hidden.
"""

import os

import binaryninja

if binaryninja.core_ui_enabled():
    from binaryninjaui import Sidebar, SidebarContextSensitivity, SidebarWidget, SidebarWidgetLocation, SidebarWidgetType
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QImage, QPainter, QPolygonF
    from PySide6.QtWidgets import QVBoxLayout

    from . import subway_player

    HERE = os.path.dirname(os.path.abspath(__file__))
    TITLE = "Subway Surfers"

    class SubwaySidebarWidget(SidebarWidget):
        def __init__(self, name, frame, data):
            SidebarWidget.__init__(self, name)
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            self.player = subway_player.make_player(HERE, self)
            layout.addWidget(self.player)

    class SubwaySidebarWidgetType(SidebarWidgetType):
        def __init__(self):
            # Grayscale 56x56 icon, white = shape; Binja tints it for the theme. A play triangle.
            icon = QImage(56, 56, QImage.Format_RGB32)
            icon.fill(0)
            p = QPainter(icon)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255))
            p.drawPolygon(QPolygonF([QPointF(16, 10), QPointF(46, 28), QPointF(16, 46)]))
            p.end()
            SidebarWidgetType.__init__(self, icon, TITLE)

        def createWidget(self, frame, data):
            return SubwaySidebarWidget(TITLE, frame, data)

        def defaultLocation(self):
            return SidebarWidgetLocation.RightContent

        def contextSensitivity(self):
            # One player for the whole window, not one per open binary.
            return SidebarContextSensitivity.SelfManagedSidebarContext

    Sidebar.addSidebarWidgetType(SubwaySidebarWidgetType())
    cv2 = subway_player.cv2
    binaryninja.log_info(
        f"[subway] loaded: cv2={cv2 and cv2.__version__} video={subway_player.find_video(HERE)}"
    )
