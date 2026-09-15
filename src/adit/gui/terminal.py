"""Terminal widget: draws the screen of a shell session and sends keystrokes to it."""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetricsF, QKeyEvent, QPainter
from PySide6.QtWidgets import QApplication, QWidget

from adit.gui.terminal_backend import ShellSession, TerminalError, available
from adit.lang import L

POLL_MS = 30
PADDING = 6

# xterm の 8 色 + 既定。pyte は色名か 6 桁の 16 進で返す
NAMED = {"black": "#2e3436", "red": "#cc0000", "green": "#4e9a06", "brown": "#c4a000", "yellow": "#c4a000",
         "blue": "#3465a4", "magenta": "#75507b", "cyan": "#06989a", "white": "#d3d7cf"}
BRIGHT = {"black": "#555753", "red": "#ef2929", "green": "#8ae234", "brown": "#fce94f", "yellow": "#fce94f",
          "blue": "#729fcf", "magenta": "#ad7fa8", "cyan": "#34e2e2", "white": "#eeeeec"}


def _color(name: str, default: str, bold: bool = False) -> QColor:
    if not name or name == "default":
        return QColor(default)
    table = BRIGHT if bold else NAMED
    if name in table:
        return QColor(table[name])
    if len(name) == 6:
        return QColor("#" + name)
    return QColor(default)


class TerminalWidget(QWidget):
    """A shell in a widget. Left click focuses it; keys go straight to the shell."""

    finished = Signal()

    def __init__(self, cwd=None, command=None, dark: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.dark = dark
        self.session: ShellSession | None = None
        self.error = ""
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSizeF(max(9.0, font.pointSizeF()))
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self._metrics = QFontMetricsF(font)
        self._cw = max(1.0, self._metrics.horizontalAdvance("M"))
        self._ch = max(1.0, self._metrics.height())
        ok, missing = available()
        if not ok:
            self.error = L(f"ターミナルを開けません ({missing} が入っていません)",
                           f"cannot open a terminal ({missing} is not installed)")
        else:
            try:
                self.session = ShellSession(cwd=cwd, command=command, rows=self.rows(), cols=self.cols())
            except TerminalError as ex:
                self.error = L(f"シェルを起動できません: {ex}", f"cannot start a shell: {ex}")
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(POLL_MS)

    # ---- size in characters ----
    def cols(self) -> int:
        return max(20, int((self.width() - 2 * PADDING) / self._cw))

    def rows(self) -> int:
        return max(4, int((self.height() - 2 * PADDING) / self._ch))

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt)
        super().resizeEvent(event)
        if self.session is not None:
            self.session.resize(self.rows(), self.cols())
            self.update()

    # ---- running ----
    def _poll(self) -> None:
        if self.session is None:
            return
        if self.session.drain():
            self.update()
        if not self.session.alive:
            self._timer.stop()
            self.finished.emit()
            self.update()

    def send(self, text: str) -> None:
        """Type text into the shell (used by the buttons that paste a command)."""
        if self.session is not None:
            self.session.write(text)

    def close_session(self) -> None:
        self._timer.stop()
        if self.session is not None:
            self.session.close()
            self.session = None

    # ---- drawing ----
    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt)
        p = QPainter(self)
        back = QColor("#1e1e1e") if self.dark else QColor("#ffffff")
        fore = "#d7d7d7" if self.dark else "#1e1e1e"
        p.fillRect(self.rect(), back)
        p.setFont(self.font())
        if self.session is None:
            p.setPen(QColor("#b00020"))
            p.drawText(self.rect().adjusted(PADDING, PADDING, -PADDING, -PADDING),
                       int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
                       self.error)
            p.end()
            return
        ascent = self._metrics.ascent()
        for y, row in enumerate(self.session.lines()):
            x = 0
            while x < len(row):
                cell = row[x]
                if cell.text == "":            # 全角文字が使っている 2 桁目
                    x += 1
                    continue
                run, start = cell.text, x
                x += 1
                while x < len(row) and row[x].fg == cell.fg and row[x].bg == cell.bg and row[x].bold == cell.bold \
                        and row[x].reverse == cell.reverse:
                    run += row[x].text         # 空文字ならそのまま (全角の 2 桁目は詰めない)
                    x += 1
                fg = _color(cell.fg, fore, cell.bold)
                bg = _color(cell.bg, back.name())
                if cell.reverse:
                    fg, bg = bg, fg
                left = PADDING + start * self._cw
                top = PADDING + y * self._ch
                if bg != back:
                    p.fillRect(QRect(int(left), int(top), int(len(run) * self._cw) + 1, int(self._ch) + 1), bg)
                if run.strip():
                    p.setPen(fg)
                    f = p.font()
                    f.setBold(cell.bold)
                    p.setFont(f)
                    p.drawText(int(left), int(top + ascent), run)
        cy, cx = self.session.cursor
        if self.hasFocus():
            p.fillRect(QRect(int(PADDING + cx * self._cw), int(PADDING + cy * self._ch),
                             max(2, int(self._cw)), int(self._ch)), QColor(fore))
        p.end()

    # ---- keyboard ----
    KEYS = {Qt.Key.Key_Return: "\r", Qt.Key.Key_Enter: "\r", Qt.Key.Key_Backspace: "\x7f",
            Qt.Key.Key_Tab: "\t", Qt.Key.Key_Escape: "\x1b", Qt.Key.Key_Delete: "\x1b[3~",
            Qt.Key.Key_Up: "\x1b[A", Qt.Key.Key_Down: "\x1b[B", Qt.Key.Key_Right: "\x1b[C", Qt.Key.Key_Left: "\x1b[D",
            Qt.Key.Key_Home: "\x1b[H", Qt.Key.Key_End: "\x1b[F",
            Qt.Key.Key_PageUp: "\x1b[5~", Qt.Key.Key_PageDown: "\x1b[6~"}

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (Qt)
        if self.session is None:
            return
        mods, key = event.modifiers(), event.key()
        if mods & Qt.KeyboardModifier.ControlModifier and mods & Qt.KeyboardModifier.ShiftModifier and key == Qt.Key.Key_C:
            QApplication.clipboard().setText(self.session.text())     # 画面をコピー
            return
        if mods & Qt.KeyboardModifier.ControlModifier and mods & Qt.KeyboardModifier.ShiftModifier and key == Qt.Key.Key_V:
            self.send(QApplication.clipboard().text())
            return
        if key in self.KEYS:
            self.send(self.KEYS[key])
            return
        if mods & Qt.KeyboardModifier.ControlModifier and Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            self.send(chr(key - Qt.Key.Key_A + 1))                    # Ctrl+C なら \x03
            return
        if event.text():
            self.send(event.text())

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt)
        """ホイールで、流れていった行をさかのぼる。"""
        if self.session is None:
            return
        steps = event.angleDelta().y()
        screen = self.session.screen
        for _ in range(max(1, abs(steps) // 120)):
            (screen.prev_page if steps > 0 else screen.next_page)()
        self.update()

    def restart(self, cwd=None) -> None:
        """終わったシェルを、もう一度起動する。"""
        self.close_session()
        try:
            self.session = ShellSession(cwd=cwd, rows=self.rows(), cols=self.cols())
            self.error = ""
        except TerminalError as ex:
            self.error = L(f"シェルを起動できません: {ex}", f"cannot start a shell: {ex}")
        self._timer.start(POLL_MS)
        self.update()

    def focusInEvent(self, event) -> None:  # noqa: N802 (Qt)
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event) -> None:  # noqa: N802 (Qt)
        super().focusOutEvent(event)
        self.update()
