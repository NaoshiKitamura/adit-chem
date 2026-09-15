
from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from adit.gui.flow_layout import FlowLayout
from adit.gui.viewer3d import Viewer3D
from adit.lang import L
from adit.spec import Structure
from adit.structure import pretty_formula

ROTATIONS = {"-60x,30y,0z": "x+y+z 方向から", "0x,0y,0z": "z 軸から", "-90x,0y,0z": "y 軸から", "0x,90y,0z": "x 軸から"}


class StructureViewPanel(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._structure: Structure | None = None
        self._tmp = Path(tempfile.mkdtemp(prefix="adit_view_"))
        self.info = QLabel(""); self.info.setObjectName("hint"); self.info.setWordWrap(True)
        self.rotation = QComboBox()
        for k, v in ROTATIONS.items():
            self.rotation.addItem(v, k)
        self.repeat = QComboBox(); self.repeat.addItems(["1×1×1", "2×2×1", "2×2×2", "3×3×1"])
        self.asegui = QPushButton("ASE GUI で開く"); self.asegui.setObjectName("link")
        from adit.gui.copy_save import copy_button, save_button

        self.btn_copy = copy_button(self)
        self.btn_save = save_button(self)
        self.viewer = Viewer3D()
        self.image = self.viewer
        hint = QLabel("左ドラッグで回転、ホイールで拡大縮小、右ドラッグで移動、ダブルクリックでリセット"); hint.setObjectName("hint"); hint.setWordWrap(True)
        top = FlowLayout()
        for w in (QLabel("視点"), self.rotation, QLabel("繰り返し数"), self.repeat, self.btn_copy, self.btn_save, self.asegui):
            top.addWidget(w)
        lay = QVBoxLayout(self); lay.setContentsMargins(12, 12, 12, 12); lay.setSpacing(8)
        lay.addLayout(top); lay.addWidget(self.viewer, 1); lay.addWidget(hint); lay.addWidget(self.info)
        self.rotation.currentIndexChanged.connect(lambda *_: self.viewer.set_view(self.rotation.currentData()))
        self.repeat.currentIndexChanged.connect(self._render)
        self.repeat.activated.connect(self._on_user_repeat)
        self._user_repeat = False
        self.asegui.clicked.connect(self._open_ase_gui)
        self.btn_copy.clicked.connect(self._copy_image)
        self.btn_save.clicked.connect(self._save_image)

    def set_dark(self, dark: bool) -> None:
        self.viewer.dark = dark; self.viewer.update()

    def set_structure(self, st: Structure | None, error: str = "") -> None:
        self._structure = st
        if st is None:
            self.viewer.set_atoms(None)
            self.info.setText(L(f"構造がありません: {error}", f"no structure: {error}")); self.asegui.setEnabled(False)
            return
        self.asegui.setEnabled(True)
        a = st.atoms.to_ase()
        per = L("周期系", "periodic") if any(a.pbc) else L("分子 (非周期)", "molecule (non-periodic)")
        cell = ""
        if any(a.pbc):
            la, lb, lc = a.cell.lengths(); cell = L(f"、セル {la:.3f} × {lb:.3f} × {lc:.3f} Å", f", cell {la:.3f} × {lb:.3f} × {lc:.3f} Å")
        elems = " ".join(sorted(set(a.get_chemical_symbols())))
        if not self._user_repeat:
            want = "2×2×2" if any(a.pbc) and len(a) < 8 else "1×1×1"
            if self.repeat.currentText() != want:
                self.repeat.blockSignals(True); self.repeat.setCurrentText(want); self.repeat.blockSignals(False)
        shown = ""
        if any(a.pbc) and self.repeat.currentText() != "1×1×1":
            shown = L(f"。表示は基本セルを {self.repeat.currentText()} 並べたもの (計算するのは基本セル {len(a)} 原子)",
                      f". Shown as {self.repeat.currentText()} copies of the cell (the calculation uses the {len(a)}-atom cell)")
        self.info.setText(L(f"{pretty_formula(a.get_chemical_formula())}、{len(a)} 原子、元素: {elems}、{per}{cell}{shown}", f"{pretty_formula(a.get_chemical_formula())}, {len(a)} atoms, elements: {elems}, {per}{cell}{shown}"))
        self._render()

    def _on_user_repeat(self, *_) -> None:
        self._user_repeat = True
        if self._structure is not None:
            self.set_structure(self._structure)

    def _render(self, *_) -> None:
        if self._structure is None:
            return
        a = self._structure.atoms.to_ase()
        rep = tuple(int(x) for x in self.repeat.currentText().split("×"))
        if any(a.pbc) and rep != (1, 1, 1):
            a = a * rep
        self.viewer.set_atoms(a)

    def _open_ase_gui(self) -> None:
        if self._structure is None:
            return
        import subprocess, sys
        from ase.io import write

        path = self._tmp / "structure.xyz"
        write(str(path), self._structure.atoms.to_ase())
        subprocess.Popen([sys.executable, "-m", "ase", "gui", str(path)])

    def _scene_svg(self) -> str | None:
        from adit.export_image import scene_to_svg
        from adit.web.structure3d import scene_from_atoms

        atoms = self.viewer.atoms() if hasattr(self.viewer, "atoms") else getattr(self.viewer, "_atoms", None)
        if atoms is None or len(atoms) == 0:
            return None
        scene = scene_from_atoms(atoms)
        rot = getattr(self.viewer, "_rot", None)
        try:
            return scene_to_svg(scene)
        except ValueError:
            return None

    def _copy_image(self) -> None:
        from adit.gui.copy_save import copy_widget

        copy_widget(self.viewer)

    def _save_image(self) -> None:
        from adit.gui.copy_save import save_dialog

        save_dialog(self, "structure.svg", svg_text=self._scene_svg(), widget=self.viewer)
