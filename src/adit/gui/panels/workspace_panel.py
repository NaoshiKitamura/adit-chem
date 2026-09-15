"""Workspace tab: a file tree, a text editor and a terminal on the same screen."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDir, QModelIndex, Qt, Signal
from PySide6.QtGui import QFont, QFontDatabase, QKeySequence, QShortcut
from PySide6.QtWidgets import (QFileSystemModel, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMenu, QMessageBox,
                               QPlainTextEdit, QPushButton, QSplitter, QTreeView, QVBoxLayout, QWidget)

from adit.gui.style import GROUP_SPACING, PANEL_MARGIN
from adit.gui.terminal import TerminalWidget
from adit.lang import L

MAX_EDIT_BYTES = 2_000_000
TEXT_SUFFIXES = {".txt", ".md", ".json", ".toml", ".yaml", ".yml", ".sh", ".py", ".hsd", ".gen", ".xyz", ".extxyz",
                 ".in", ".inp", ".out", ".log", ".dat", ".csv", ".cfg", ".conf", ".ini", ".gjf", ".com", ".nw",
                 ".control", ".mdp", ".top", ".itp", ".gro", ".pdb", ".cif", ".POSCAR", ".KPOINTS", ".INCAR"}
NAME_ONLY = {"INCAR", "POSCAR", "CONTCAR", "KPOINTS", "POTCAR", "OUTCAR", "README", "LICENSE", "Makefile"}


def _looks_like_text(path: Path) -> bool:
    if path.name in NAME_ONLY or path.suffix.lower() in TEXT_SUFFIXES:
        return True
    try:
        chunk = path.open("rb").read(4096)
    except OSError:
        return False
    return b"\0" not in chunk


class Editor(QPlainTextEdit):
    """Plain text editor for one file at a time."""

    dirty_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.path: Path | None = None
        self._dirty = False
        self.textChanged.connect(self._on_changed)

    def _on_changed(self) -> None:
        if self.path is not None and not self._dirty:
            self._dirty = True
            self.dirty_changed.emit(True)

    @property
    def dirty(self) -> bool:
        return self._dirty

    def open_file(self, path: Path) -> str:
        """Show the file. Returns an empty string, or the reason it cannot be shown."""
        if path.stat().st_size > MAX_EDIT_BYTES:
            return L(f"大きすぎて開けません ({path.stat().st_size // 1024} KB)。ターミナルで開いてください",
                     f"too large to open ({path.stat().st_size // 1024} KB); open it in the terminal")
        if not _looks_like_text(path):
            return L("テキストではないので開けません", "not a text file")
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as ex:
            return str(ex)
        self.path = None                      # 読み込み中の textChanged を「変更」と数えない
        self.setPlainText(text)
        self.path, self._dirty = path, False
        self.dirty_changed.emit(False)
        return ""

    def save(self) -> str:
        if self.path is None:
            return L("開いているファイルがありません", "no file is open")
        try:
            self.path.write_text(self.toPlainText(), encoding="utf-8")
        except OSError as ex:
            return str(ex)
        self._dirty = False
        self.dirty_changed.emit(False)
        return ""


class WorkspacePanel(QWidget):
    """File tree on the left, editor above the terminal on the right."""

    def __init__(self, root: Path | str | None = None, dark: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.root = Path(root).expanduser() if root else Path.home()

        self.model = QFileSystemModel(self)
        self.model.setRootPath(str(self.root))
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot | QDir.Filter.Hidden)
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(str(self.root)))
        for column in (1, 2, 3):
            self.tree.hideColumn(column)
        self.tree.setHeaderHidden(True)
        self.tree.setDragDropMode(QTreeView.DragDropMode.InternalMove)   # ドラッグで移動できる
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu)
        self.tree.doubleClicked.connect(self._open_index)

        self.path_label = QLabel(str(self.root))
        self.path_label.setObjectName("hint")
        self.btn_up = QPushButton(L("上へ", "Up"))
        self.btn_up.clicked.connect(lambda: self.set_root(self.root.parent))

        self.editor = Editor()
        self.file_label = QLabel(L("ファイルを選ぶと、ここで編集できます", "pick a file to edit it here"))
        self.file_label.setObjectName("hint")
        self.btn_save = QPushButton(L("保存", "Save"))
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.save)
        self.editor.dirty_changed.connect(self._on_dirty)

        self.terminal = TerminalWidget(cwd=self.root, dark=dark)
        self.btn_here = QPushButton(L("ここへ移動 (cd)", "cd here"))
        self.btn_here.clicked.connect(lambda: self.terminal.send(f"cd {self._quoted(self.root)}\n"))
        self.btn_restart = QPushButton(L("シェルを起動し直す", "Restart the shell"))
        self.btn_restart.setVisible(False)
        self.btn_restart.clicked.connect(lambda: (self.terminal.restart(self.root), self.btn_restart.setVisible(False)))
        self.terminal.finished.connect(lambda: self.btn_restart.setVisible(True))

        save = QShortcut(QKeySequence.StandardKey.Save, self)      # Ctrl+S
        save.activated.connect(self.save)

        left = QWidget()
        ll = QVBoxLayout(left); ll.setContentsMargins(0, 0, 0, 0); ll.setSpacing(4)
        top = QHBoxLayout(); top.addWidget(self.btn_up); top.addWidget(self.path_label, 1)
        ll.addLayout(top); ll.addWidget(self.tree, 1)

        right = QSplitter(Qt.Orientation.Vertical)
        edit_box = QWidget()
        el = QVBoxLayout(edit_box); el.setContentsMargins(0, 0, 0, 0); el.setSpacing(4)
        head = QHBoxLayout(); head.addWidget(self.file_label, 1); head.addWidget(self.btn_save)
        el.addLayout(head); el.addWidget(self.editor, 1)
        term_box = QWidget()
        tl = QVBoxLayout(term_box); tl.setContentsMargins(0, 0, 0, 0); tl.setSpacing(4)
        thead = QHBoxLayout()
        label = QLabel(L("ターミナル", "Terminal")); label.setObjectName("section")
        thead.addWidget(label); thead.addStretch(); thead.addWidget(self.btn_restart); thead.addWidget(self.btn_here)
        tl.addLayout(thead); tl.addWidget(self.terminal, 1)
        right.addWidget(edit_box); right.addWidget(term_box); right.setSizes([420, 380])

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(left); split.addWidget(right); split.setSizes([320, 900])
        lay = QVBoxLayout(self)
        lay.setContentsMargins(PANEL_MARGIN, 8, PANEL_MARGIN, PANEL_MARGIN); lay.setSpacing(GROUP_SPACING)
        lay.addWidget(split)

    # ---- helpers ----
    @staticmethod
    def _quoted(path: Path) -> str:
        import shlex

        return shlex.quote(str(path))

    def _selected(self) -> Path | None:
        index = self.tree.currentIndex()
        return Path(self.model.filePath(index)) if index.isValid() else None

    def set_root(self, path: Path | str) -> None:
        path = Path(path).expanduser()
        if not path.is_dir():
            return
        self.root = path
        self.model.setRootPath(str(path))
        self.tree.setRootIndex(self.model.index(str(path)))
        self.path_label.setText(str(path))

    def set_dark(self, dark: bool) -> None:
        self.terminal.dark = dark
        self.terminal.update()

    # ---- editor ----
    def _open_index(self, index: QModelIndex) -> None:
        path = Path(self.model.filePath(index))
        if path.is_dir():
            self.set_root(path)
            return
        self.open_file(path)

    def open_file(self, path: Path) -> str:
        if self.editor.dirty and not self._ask_discard():
            return ""
        why = self.editor.open_file(path)
        if why:
            self.file_label.setText(f"{path.name}: {why}")
            return why
        self.file_label.setText(str(path))
        return ""

    def _ask_discard(self) -> bool:
        answer = QMessageBox.question(self, L("保存していません", "Not saved"),
                                      L("編集した内容を保存していません。捨ててよいですか?",
                                        "The file has unsaved changes. Discard them?"))
        return answer == QMessageBox.StandardButton.Yes

    def _on_dirty(self, dirty: bool) -> None:
        self.btn_save.setEnabled(dirty)
        if self.editor.path is not None:
            self.file_label.setText(("* " if dirty else "") + str(self.editor.path))

    def save(self) -> str:
        why = self.editor.save()
        if why:
            QMessageBox.warning(self, L("保存できません", "Cannot save"), why)
        return why

    # ---- file operations ----
    def _menu(self, point) -> None:
        path = self._selected()
        if path is None:
            return
        menu = QMenu(self)
        act_open = menu.addAction(L("開く", "Open"))
        act_term = menu.addAction(L("ターミナルでここへ移動", "cd here in the terminal"))
        act_rename = menu.addAction(L("名前を変える…", "Rename…"))
        act_new = menu.addAction(L("フォルダを作る…", "New folder…"))
        chosen = menu.exec(self.tree.viewport().mapToGlobal(point))
        if chosen is act_open:
            self._open_index(self.tree.currentIndex())
        elif chosen is act_term:
            self.terminal.send(f"cd {self._quoted(path if path.is_dir() else path.parent)}\n")
        elif chosen is act_rename:
            name, ok = QInputDialog.getText(self, L("名前を変える", "Rename"), L("新しい名前", "New name"),
                                            QLineEdit.EchoMode.Normal, path.name)
            if ok and name.strip():
                try:
                    path.rename(path.with_name(name.strip()))
                except OSError as ex:
                    QMessageBox.warning(self, L("変えられません", "Cannot rename"), str(ex))
        elif chosen is act_new:
            name, ok = QInputDialog.getText(self, L("フォルダを作る", "New folder"), L("名前", "Name"))
            if ok and name.strip():
                base = path if path.is_dir() else path.parent
                try:
                    (base / name.strip()).mkdir()
                except OSError as ex:
                    QMessageBox.warning(self, L("作れません", "Cannot create"), str(ex))

    def close_session(self) -> None:
        self.terminal.close_session()
