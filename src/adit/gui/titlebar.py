
from __future__ import annotations

import sys

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, QSize, Qt
from PySide6.QtGui import QColor, QCursor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QApplication, QHBoxLayout, QLabel, QWidget

from adit.config import env_var
from adit.gui.style import current_theme

BUTTON_COLORS = {
    "close": ("#FF5F57", "#D9433D"),
    "minimize": ("#FEBC2E", "#D99A12"),
    "maximize": ("#28C840", "#1A9E2E"),
}
IDLE_COLORS = {"light": "#C4C4CA", "dark": "#5A5A5F"}
TITLE_HEIGHT = 38
RESIZE_MARGIN = 6


def use_custom_frame(setting: str = "auto") -> bool:
    value = (env_var("FRAME") or setting or "auto").lower()
    if value in ("custom", "native"):
        return value == "custom"
    return sys.platform.startswith("linux")


class WindowButton(QAbstractButton):

    DIAMETER = 14

    def __init__(self, kind: str, tooltip: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.kind = kind
        self.hovered = False
        self.setObjectName(f"window_{kind}")
        self.setToolTip(tooltip)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(QSize(22, 22))

    def enterEvent(self, event) -> None:
        self.hovered = True; self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.hovered = False; self.update()
        super().leaveEvent(event)

    def fill_color(self) -> str:
        hover, pressed = BUTTON_COLORS[self.kind]
        if self.isDown():
            return pressed
        if self.hovered:
            return hover
        return IDLE_COLORS["dark" if current_theme() == "dark" else "light"]

    def paintEvent(self, _event) -> None:
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        d = self.DIAMETER
        c = QPointF(self.width() / 2, self.height() / 2)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(self.fill_color()))
        p.drawEllipse(c, d / 2, d / 2)
        if not (self.hovered or self.isDown()):
            return
        pen = QPen(QColor(0, 0, 0, 150), 1.6); pen.setCapStyle(Qt.PenCapStyle.RoundCap); p.setPen(pen)
        a = d * 0.22
        if self.kind == "close":
            p.drawLine(QPointF(c.x() - a, c.y() - a), QPointF(c.x() + a, c.y() + a))
            p.drawLine(QPointF(c.x() - a, c.y() + a), QPointF(c.x() + a, c.y() - a))
        else:
            p.drawLine(QPointF(c.x() - a * 1.2, c.y()), QPointF(c.x() + a * 1.2, c.y()))
            if self.kind == "maximize":
                p.drawLine(QPointF(c.x(), c.y() - a * 1.2), QPointF(c.x(), c.y() + a * 1.2))


class TitleBar(QWidget):

    def __init__(self, window: QWidget, leading: QWidget):
        super().__init__(window)
        self.win = window
        self.setObjectName("titlebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(TITLE_HEIGHT)
        self.btn_close = WindowButton("close", "閉じる")
        self.btn_min = WindowButton("minimize", "最小化")
        self.btn_max = WindowButton("maximize", "最大化 / 元の大きさ")
        self.btn_close.clicked.connect(window.close)
        self.btn_min.clicked.connect(window.showMinimized)
        self.btn_max.clicked.connect(self.toggle_maximized)
        self.leading = leading
        self.title = QLabel(window.windowTitle()); self.title.setObjectName("window_title")
        self.title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        window.windowTitleChanged.connect(self.title.setText)
        lay = QHBoxLayout(self); lay.setContentsMargins(12, 0, 12, 0); lay.setSpacing(2)
        lay.addWidget(leading)
        lay.addStretch(1); lay.addWidget(self.title); lay.addStretch(1)
        lay.addSpacing(14)
        for b in (self.btn_min, self.btn_max, self.btn_close):
            lay.addWidget(b)
        self._drag_offset: QPoint | None = None

    def toggle_maximized(self) -> None:
        if self.win.isMaximized():
            self.win.showNormal()
        else:
            self.win.showMaximized()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        handle = self.win.windowHandle()
        if handle is not None and handle.startSystemMove():
            event.accept(); return
        self._drag_offset = event.globalPosition().toPoint() - self.win.frameGeometry().topLeft()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            if self.win.isMaximized():
                self.win.showNormal()
            self.win.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept(); return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximized(); event.accept(); return
        super().mouseDoubleClickEvent(event)


class EdgeResizer(QObject):

    def __init__(self, window: QWidget, margin: int = RESIZE_MARGIN):
        super().__init__(window)
        self.win, self.margin = window, margin
        self._cursor_set = False
        self._manual: tuple[Qt.Edge, QPoint, QRect] | None = None
        QApplication.instance().installEventFilter(self)

    def edges_at(self, gpos: QPoint) -> Qt.Edge:
        if self.win.isMaximized() or self.win.isFullScreen():
            return Qt.Edge(0)
        r, m = self.win.frameGeometry(), self.margin
        x, y = gpos.x() - r.x(), gpos.y() - r.y()
        if not (0 <= x < r.width() and 0 <= y < r.height()):
            return Qt.Edge(0)
        e = Qt.Edge(0)
        if x < m: e |= Qt.Edge.LeftEdge
        if x >= r.width() - m: e |= Qt.Edge.RightEdge
        if y < m: e |= Qt.Edge.TopEdge
        if y >= r.height() - m: e |= Qt.Edge.BottomEdge
        return e

    @staticmethod
    def _cursor_for(e: Qt.Edge) -> Qt.CursorShape:
        L, R, T, B = Qt.Edge.LeftEdge, Qt.Edge.RightEdge, Qt.Edge.TopEdge, Qt.Edge.BottomEdge
        if e in (L | T, R | B):
            return Qt.CursorShape.SizeFDiagCursor
        if e in (R | T, L | B):
            return Qt.CursorShape.SizeBDiagCursor
        if e & (L | R):
            return Qt.CursorShape.SizeHorCursor
        return Qt.CursorShape.SizeVerCursor

    def _set_cursor(self, e: Qt.Edge) -> None:
        if e != Qt.Edge(0):
            cur = QCursor(self._cursor_for(e))
            if self._cursor_set:
                QApplication.changeOverrideCursor(cur)
            else:
                QApplication.setOverrideCursor(cur); self._cursor_set = True
        elif self._cursor_set:
            QApplication.restoreOverrideCursor(); self._cursor_set = False

    def eventFilter(self, obj, event) -> bool:
        t = event.type()
        if t not in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
            return False
        if not isinstance(obj, QWidget) or obj.window() is not self.win:
            return False
        gpos = event.globalPosition().toPoint()
        if self._manual is not None:
            if t == QEvent.Type.MouseMove:
                self._resize_manually(gpos); return True
            if t == QEvent.Type.MouseButtonRelease:
                self._manual = None; return True
        edges = self.edges_at(gpos)
        if t == QEvent.Type.MouseMove and event.buttons() == Qt.MouseButton.NoButton:
            self._set_cursor(edges)
        elif t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton and edges != Qt.Edge(0):
            handle = self.win.windowHandle()
            if handle is None or not handle.startSystemResize(edges):
                self._manual = (edges, gpos, self.win.geometry())
            return True
        return False

    def _resize_manually(self, gpos: QPoint) -> None:
        edges, start, g0 = self._manual
        dx, dy = gpos.x() - start.x(), gpos.y() - start.y()
        g = QRect(g0)
        mw, mh = self.win.minimumSizeHint().width(), self.win.minimumSizeHint().height()
        if edges & Qt.Edge.LeftEdge: g.setLeft(min(g0.left() + dx, g0.right() - mw))
        if edges & Qt.Edge.RightEdge: g.setRight(max(g0.right() + dx, g0.left() + mw))
        if edges & Qt.Edge.TopEdge: g.setTop(min(g0.top() + dy, g0.bottom() - mh))
        if edges & Qt.Edge.BottomEdge: g.setBottom(max(g0.bottom() + dy, g0.top() + mh))
        self.win.setGeometry(g)


def install(window, leading: QWidget) -> TitleBar:
    window.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    window.setObjectName("adit_frameless")
    bar = TitleBar(window, leading)
    window._edge_resizer = EdgeResizer(window)
    return bar


__all__ = ["BUTTON_COLORS", "IDLE_COLORS", "TitleBar", "WindowButton", "EdgeResizer", "install", "use_custom_frame"]
