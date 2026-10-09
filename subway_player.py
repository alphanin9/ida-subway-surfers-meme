"""Host-agnostic Subway Surfers player widgets (PySide6). Shared by the IDA and Binary Ninja plugins.

By default this paints the ASCII lookalike from subway_ascii.py (no dependencies, no footage).
With SUBWAY_MODE=video it plays `subway_surfers.mp4/.webm/.mkv` via cv2 if it's importable, else
`subway_surfers.gif` via Qt's built-in qgif; override the file with SUBWAY_VIDEO / IDA_SUBWAY_VIDEO.
"""

import os

from PySide6 import QtCore, QtGui, QtWidgets

try:
    from . import subway_ascii  # Binary Ninja: we're inside the plugin package
except ImportError:
    import subway_ascii  # IDA: the plugin dir is on sys.path

try:
    import cv2
except ImportError:
    cv2 = None


def find_video(plugin_dir):
    candidates = [os.environ.get("SUBWAY_VIDEO"), os.environ.get("IDA_SUBWAY_VIDEO")] + [
        os.path.join(plugin_dir, "subway_surfers" + ext) for ext in (".mp4", ".webm", ".mkv", ".gif")
    ]
    for path in candidates:
        if path and os.path.isfile(path) and (cv2 or path.lower().endswith(".gif")):
            return path
    return None


class FitLabel(QtWidgets.QLabel):
    """Black QLabel that ignores its content's size hint so the dock can shrink freely."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setMinimumSize(1, 1)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.setStyleSheet("background: black; color: white;")

    def stop(self):
        pass


class GifLabel(FitLabel):
    """Plays a GIF via QMovie, rescaled to fit while keeping aspect ratio."""

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.movie = QtGui.QMovie(path)
        self.movie.setCacheMode(QtGui.QMovie.CacheAll)
        self.movie.jumpToFrame(0)
        self.native = self.movie.currentImage().size()
        self.setMovie(self.movie)
        self.movie.start()

    def resizeEvent(self, event):
        if not self.native.isEmpty():
            self.movie.setScaledSize(self.native.scaled(self.size(), QtCore.Qt.KeepAspectRatio))
        super().resizeEvent(event)

    def showEvent(self, event):
        self.movie.setPaused(False)
        super().showEvent(event)

    def hideEvent(self, event):
        self.movie.setPaused(True)
        super().hideEvent(event)

    def stop(self):
        self.movie.stop()


class Cv2Label(FitLabel):
    """Decodes frames with cv2 on a QTimer and paints them, looping forever. Pauses while hidden."""

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.cap = cv2.VideoCapture(path)
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(int(1000 / fps))
        self.timer.timeout.connect(self.next_frame)
        self.timer.start()

    def next_frame(self):
        ok, frame = self.cap.read()
        if not ok:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.cap.read()
            if not ok:
                return
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = QtGui.QImage(rgb.data, w, h, rgb.strides[0], QtGui.QImage.Format_RGB888)
        self.setPixmap(
            QtGui.QPixmap.fromImage(img).scaled(
                self.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            )
        )

    def showEvent(self, event):
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def stop(self):
        self.timer.stop()
        self.cap.release()


class AsciiGame(QtWidgets.QWidget):
    """Steps a subway_ascii.Game on a timer and paints its frames as a colored character grid.
    Click it to focus, then arrow keys / WASD to play. Pauses while hidden."""

    KEYS = {
        QtCore.Qt.Key_Left: "left", QtCore.Qt.Key_A: "left",
        QtCore.Qt.Key_Right: "right", QtCore.Qt.Key_D: "right",
        QtCore.Qt.Key_Up: "up", QtCore.Qt.Key_W: "up",
        QtCore.Qt.Key_Down: "down", QtCore.Qt.Key_S: "down",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.game = subway_ascii.Game()
        self.colors = {}
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setMinimumSize(1, 1)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.base_font = QtGui.QFont("Consolas")
        self.base_font.setStyleHint(QtGui.QFont.Monospace)
        self._fit()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(self.game.interval_ms())

    def tick(self):
        self.game.step()
        self.timer.setInterval(self.game.interval_ms())
        self.update()

    def _fit(self):
        """Picks the largest font whose character grid fits the widget, and centers the grid."""
        rows, cols = subway_ascii.HEIGHT + 2, subway_ascii.WIDTH
        font = QtGui.QFont(self.base_font)
        font.setPixelSize(100)
        fm = QtGui.QFontMetricsF(font)
        px = min(self.width() / cols / (fm.horizontalAdvance("M") / 100), self.height() / rows / (fm.height() / 100))
        font.setPixelSize(max(4, int(px)))
        fm = QtGui.QFontMetricsF(font)
        self.font_, self.cw, self.ch, self.ascent = font, fm.horizontalAdvance("M"), fm.height(), fm.ascent()
        self.ox = (self.width() - cols * self.cw) / 2
        self.oy = (self.height() - rows * self.ch) / 2

    def resizeEvent(self, event):
        self._fit()
        super().resizeEvent(event)

    def color(self, name):
        if name not in self.colors:
            self.colors[name] = QtGui.QColor(name)
        return self.colors[name]

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), QtCore.Qt.black)
        p.setFont(self.font_)
        lines = self.game.render().split("\n")
        hud = self.color(subway_ascii.HUD_COLOR)
        for r, line in enumerate(lines):
            y = self.oy + r * self.ch + self.ascent
            is_hud = r in (0, len(lines) - 1)
            # One drawText per char keeps the grid aligned even if a glyph comes from a fallback font.
            for c, char in enumerate(line):
                if char != " ":
                    p.setPen(hud if is_hud else self.color(subway_ascii.color_of(char)))
                    p.drawText(QtCore.QPointF(self.ox + c * self.cw, y), char)
        p.end()

    def keyPressEvent(self, event):
        key = self.KEYS.get(event.key())
        if key:
            self.game.press(key)
            self.update()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event):
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def stop(self):
        self.timer.stop()


def make_player(plugin_dir, parent=None):
    """The ASCII game, or with SUBWAY_MODE=video the clip (falling back to ASCII if there's none)."""
    if os.environ.get("SUBWAY_MODE", "ascii").lower() == "video":
        path = find_video(plugin_dir)
        if path:
            cls = GifLabel if path.lower().endswith(".gif") else Cv2Label
            return cls(path, parent)
    return AsciiGame(parent)
