
from __future__ import annotations

from pathlib import Path

import numpy as np
from ase import Atoms
from ase.io import write

from adit.analysis.compute import MoleculeUnwrapper
from adit.lang import L

EXPORT_SUBDIR = "export"
FILES = ("trajectory.extxyz", "trajectory.xyz", "trajectory.pdb", "view.vmd", "ovito_pipeline.py", "export_README.txt")
_PDB_ATOM = "ATOM  %5d %4s %4s %4d    %8.3f%8.3f%8.3f%6.2f%6.2f          %2s  \n"


class TrajectoryExporter:

    def __init__(self, out_dir: Path, *, unwrap_molecules: bool = False):
        self.dir = Path(out_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.unwrap = unwrap_molecules
        self._fe = open(self.dir / "trajectory.extxyz", "w", encoding="utf-8", newline="\n")
        self._fx = open(self.dir / "trajectory.xyz", "w", encoding="utf-8", newline="\n")
        self._fp = open(self.dir / "trajectory.pdb", "w", encoding="utf-8", newline="\n")
        self.n = 0
        self.first: Atoms | None = None
        self.last_cell = None
        self.cell_varies = False
        self.mol: MoleculeUnwrapper | None = None

    def add(self, fr: Atoms) -> None:
        if self.first is None:
            self.first = fr.copy()
            self.mol = MoleculeUnwrapper(fr)
        a = self.mol.apply(fr) if self.unwrap and self.mol is not None else fr
        periodic = bool(any(a.pbc)) and a.cell.rank == 3
        if periodic:
            c = np.asarray(a.cell, dtype=float)
            if self.last_cell is not None and not np.allclose(c, self.last_cell, atol=1e-6):
                self.cell_varies = True
            self.last_cell = c
        b = a.copy()
        b.calc = None
        write(self._fe, b, format="extxyz")
        self._fx.write(f"{len(a)}\n{L('フレーム', 'frame')} {self.n} (ADIT)\n")
        for s, p in zip(a.get_chemical_symbols(), a.get_positions()):
            self._fx.write(f"{s:<2s} {p[0]:16.8f} {p[1]:16.8f} {p[2]:16.8f}\n")
        self._write_pdb_model(a, periodic)
        self.n += 1

    def _write_pdb_model(self, a: Atoms, periodic: bool) -> None:
        p = a.get_positions()
        if periodic:
            cp = a.cell.cellpar()
            _, rot = a.cell.standard_form()
            p = p @ rot.T
            self._fp.write("CRYST1%9.3f%9.3f%9.3f%7.2f%7.2f%7.2f P 1\n" % tuple(cp))
        self._fp.write(f"MODEL     {self.n + 1}\n")
        labels = self.mol.labels if self.mol is not None else np.zeros(len(a), int)
        for i, (s, (x, y, z)) in enumerate(zip(a.get_chemical_symbols(), p)):
            self._fp.write(_PDB_ATOM % ((i + 1) % 100000, s, "MOL ", (labels[i] + 1) % 10000, x, y, z, 1.0, 0.0, s.upper()))
        self._fp.write("ENDMDL\n")

    def close(self, *, run_dir: Path, code: str, source: str, dt_frame_fs: float | None, stride: int, skip: int, n_total: int | None,
              rdf_cutoff: float, extra_lines: list[str] | None = None) -> dict:
        self.extra_lines = list(extra_lines or [])
        for f in (self._fe, self._fx, self._fp):
            f.close()
        info = {"dir": str(self.dir), "files": [str(self.dir / f) for f in FILES], "n_frames": self.n, "stride": stride, "skip": skip,
                "dt_frame_fs": dt_frame_fs, "cell_varies": self.cell_varies, "unwrap_requested": self.unwrap,
                "unwrap_molecules": bool(self.unwrap and self.mol is not None and self.mol.active)}
        a = self.first
        if a is None:
            return info
        periodic = bool(any(a.pbc)) and a.cell.rank == 3
        if self.mol is not None:
            info.update(n_molecules=self.mol.n_molecules, largest_molecule_atoms=int(self.mol.sizes.max()) if len(self.mol.sizes) else 0,
                        periodic_networks=int(self.mol.network.sum()))
        if periodic:
            info["cell_A"] = [float(x) for x in a.cell.cellpar()]
        (self.dir / "view.vmd").write_text(_vmd_text(a, periodic, self.cell_varies), encoding="utf-8", newline="\n")
        (self.dir / "ovito_pipeline.py").write_text(_ovito_text(rdf_cutoff), encoding="utf-8", newline="\n")
        text = _readme_text(a, info, run_dir=run_dir, code=code, source=source, n_total=n_total)
        if self.extra_lines:
            text += "\n".join(self.extra_lines) + "\n"
        (self.dir / "export_README.txt").write_text(text, encoding="utf-8", newline="\n")
        return info


def _vmd_text(a: Atoms, periodic: bool, cell_varies: bool) -> str:
    lines = [L("# ADIT が書いた VMD の読み込みスクリプト。使い方: このディレクトリで  vmd -e view.vmd",
               "# VMD script written by ADIT. Usage: in this directory,  vmd -e view.vmd"),
             "mol new trajectory.xyz type xyz waitfor all"]
    if periodic:
        cp = a.cell.cellpar()
        if cell_varies:
            lines.append(L("# セルはフレームごとに変わります。ここでは最初のフレームのセルを全フレームに付けます (各フレームのセルは trajectory.extxyz / trajectory.pdb)",
                           "# The cell changes from frame to frame. The first frame's cell is applied to all frames here (per-frame cells are in trajectory.extxyz / trajectory.pdb)"))
        lines += [L("# セル: a b c [Å] と alpha beta gamma [度] (PBCTools。VMD 1.8.6 から同梱)", "# cell: a b c [Å] and alpha beta gamma [deg] (PBCTools, bundled since VMD 1.8.6)"),
                  "pbc set {%.6f %.6f %.6f %.4f %.4f %.4f} -all" % tuple(cp), "pbc box"]
    lines += ["mol modstyle 0 [molinfo top] CPK", ""]
    return "\n".join(lines)


_OVITO_TEMPLATE = '''#!/usr/bin/env python
"""{doc}"""
import sys
from pathlib import Path

from ovito.io import export_file, import_file
import ovito.modifiers as om

here = Path(__file__).resolve().parent
cutoff = float(sys.argv[1]) if len(sys.argv) > 1 else {cutoff:.4f}  # Å
pipeline = import_file(str(here / "trajectory.extxyz"))  # {cell_comment}
if hasattr(om, "RadialDistributionFunctionModifier"):  # {new_comment}
    pipeline.modifiers.append(om.RadialDistributionFunctionModifier(cutoff=cutoff, number_of_bins=200, partial=True))
else:  # {old_comment}
    pipeline.modifiers.append(om.CoordinationAnalysisModifier(cutoff=cutoff, number_of_bins=200, partial=True))
data = pipeline.compute()
key = next((k for k in ("rdf", "coordination-rdf") if k in data.tables), None)
if key is not None:
    export_file(pipeline, str(here / "ovito_rdf.*.txt"), "txt/table", key=key, multiple_frames=True)
    print("{wrote_rdf}", here / "ovito_rdf.*.txt")
if "Coordination" in data.particles.keys():
    export_file(pipeline, str(here / "ovito_coordination.xyz"), "xyz", multiple_frames=True,
                columns=["Particle Type", "Position.X", "Position.Y", "Position.Z", "Coordination"])
    print("{wrote_cn}", here / "ovito_coordination.xyz")
else:
    print("{no_cn}")
'''


def _ovito_text(cutoff: float) -> str:
    return _OVITO_TEMPLATE.format(
        doc=L("ADIT が書いた OVITO の Python スクリプト。ovito の Python パッケージ (MIT、pip install ovito) で動く。ADIT では実行を確かめていない。\n"
              "trajectory.extxyz を読み、元素の組ごとの動径分布関数と、原子ごとの配位数 (カットオフ以内の原子の数) を求めて書き出す。\n"
              "使い方: python ovito_pipeline.py [カットオフ Å]",
              "OVITO Python script written by ADIT. Runs with the ovito Python package (MIT, pip install ovito). Not run by ADIT.\n"
              "Reads trajectory.extxyz and writes partial radial distribution functions and per-atom coordination numbers (atoms within the cutoff).\n"
              "Usage: python ovito_pipeline.py [cutoff in Å]"),
        cutoff=cutoff,
        cell_comment=L("拡張 xyz の Lattice= と pbc= をセルとして読む", "the Lattice= and pbc= keys of extended XYZ become the cell"),
        new_comment=L("新しいバージョンの名前", "name in recent versions"),
        old_comment=L("古いバージョンの名前 (原子ごとの配位数 Coordination も出す)", "name in older versions (also outputs per-atom Coordination)"),
        wrote_rdf=L("動径分布関数:", "RDF:"), wrote_cn=L("配位数:", "coordination:"),
        no_cn=L("このバージョンの OVITO は原子ごとの配位数を出しません。ADIT の analysis/rdf.json の n と n_reverse (配位数の曲線) を使ってください",
                "this OVITO version does not output per-atom coordination; use n and n_reverse (coordination curves) in ADIT's analysis/rdf.json"))


def _readme_text(a: Atoms, info: dict, *, run_dir: Path, code: str, source: str, n_total: int | None) -> str:
    syms = a.get_chemical_symbols()
    counts = {s: syms.count(s) for s in dict.fromkeys(syms)}
    elems = ", ".join(f"{s} {n}" for s, n in counts.items())
    periodic = bool(any(a.pbc)) and a.cell.rank == 3
    dt = info.get("dt_frame_fs")
    stride = info["stride"]
    out = [L("ADIT が書き出した軌跡 (TRAVIS・OVITO・VMD 用)", "Trajectory exported by ADIT (for TRAVIS, OVITO and VMD)"), "",
           L(f"元の計算: {run_dir} ({code}、{source})", f"source calculation: {run_dir} ({code}, {source})"),
           L(f"フレーム数: {info['n_frames']} (元の軌跡 {n_total if n_total is not None else '?'} フレームのうち、先頭 {info['skip']} フレームを除き、{stride} フレームに 1 回)",
             f"frames: {info['n_frames']} (of {n_total if n_total is not None else '?'} in the original trajectory; first {info['skip']} skipped, every {stride})")]
    if dt:
        out.append(L(f"1 フレームあたりの時間: {dt * stride:g} fs (元の書き出しの間隔 {dt:g} fs × 間引き {stride})",
                     f"time per frame: {dt * stride:g} fs (original output interval {dt:g} fs x stride {stride})"))
    else:
        out.append(L("1 フレームあたりの時間: 不明 (出力から読めません。MD でない計算かもしれません)",
                     "time per frame: unknown (not readable from the output; perhaps not an MD run)"))
    out.append(L(f"元素: {elems} (合計 {len(a)} 原子)", f"elements: {elems} ({len(a)} atoms in total)"))
    if periodic:
        c = a.cell.cellpar()
        out += [L("セル (最初のフレーム):", "cell (first frame):"),
                f"  a = {c[0]:.6f} Å = {c[0] * 100:.4f} pm", f"  b = {c[1]:.6f} Å = {c[1] * 100:.4f} pm", f"  c = {c[2]:.6f} Å = {c[2] * 100:.4f} pm",
                f"  alpha = {c[3]:.4f}°, beta = {c[4]:.4f}°, gamma = {c[5]:.4f}°",
                L("  ベクトル [Å]:", "  vectors [Å]:")] + [f"    {v[0]:14.8f} {v[1]:14.8f} {v[2]:14.8f}" for v in np.asarray(a.cell)]
        if info.get("cell_varies"):
            out.append(L("  セルはフレームごとに変わります。trajectory.extxyz と trajectory.pdb には各フレームのセルがあり、trajectory.xyz には入りません",
                         "  the cell changes between frames; trajectory.extxyz and trajectory.pdb hold each frame's cell, trajectory.xyz has none"))
    else:
        out.append(L("セル: なし (周期境界の無い分子の計算)", "cell: none (non-periodic molecular calculation)"))
    if "n_molecules" in info:
        largest = info["largest_molecule_atoms"]
        s = L(f"距離による原子グループの推定 (最初のフレームで共有結合半径の和 × 1.2 以内): {info['n_molecules']} 個、最大 {largest} 原子。伸びた結合は別グループになる場合があります",
              f"distance-based atom groups (within 1.2 x the sum of covalent radii in the first frame): {info['n_molecules']}; "
              f"largest group: {largest} {'atom' if largest == 1 else 'atoms'}. Stretched bonds may be split into separate groups")
        out.append(s)
        if info["unwrap_molecules"]:
            out.append(L("  書き出す前に、分子を周期境界でつなぎ直しました (分子の中心がセルの中に来る位置へ)。区切りは最初のフレームのものを最後まで使います",
                         "  molecules were made whole across periodic boundaries before writing (each placed with its center inside the cell); the partition of the first frame is kept throughout"))
            if info.get("periodic_networks"):
                out.append(L(f"  周期的につながった集まり {info['periodic_networks']} 個 (結晶など) はつなぎ直さず、元の位置のままです",
                             f"  {info['periodic_networks']} periodically connected groups (e.g. crystals) were left as they were"))
        elif not periodic and info["unwrap_requested"]:
            out.append(L("  非周期軌跡のため、周期境界でのつなぎ直しは行っていません",
                         "  no periodic unwrapping was performed because this trajectory is non-periodic"))
        elif periodic:
            out.append(L("  つなぎ直しはしていません (座標は計算コードが書いたまま)。つなぎ直すには adit-analyze --export --unwrap-molecules",
                         "  molecules were not made whole (coordinates as written by the code); use adit-analyze --export --unwrap-molecules"))
        out.append(L("  trajectory.pdb の残基番号は、この推定グループの番号 (1 から)",
                     "  residue numbers in trajectory.pdb are these estimated group numbers (from 1)"))
    out += ["", L("ファイル:", "files:"),
            (L("  trajectory.extxyz  拡張 xyz (コメント行に Lattice= と pbc=)。OVITO・ASE で開く", "  trajectory.extxyz  extended XYZ (Lattice= and pbc= in the comment line); open with OVITO or ASE")
             if periodic else L("  trajectory.extxyz  拡張 xyz (セル・周期境界なし)。OVITO・ASE で開く",
                                "  trajectory.extxyz  extended XYZ (no cell or periodic boundaries); open with OVITO or ASE")),
            L("  trajectory.xyz     素の xyz (セルなし)。TRAVIS・VMD で開く", "  trajectory.xyz     plain XYZ (no cell); open with TRAVIS or VMD"),
            (L("  trajectory.pdb     複数モデルの PDB (各モデルに CRYST1)", "  trajectory.pdb     multi-model PDB (CRYST1 in each model)")
             if periodic else L("  trajectory.pdb     複数モデルの PDB (セル情報なし)", "  trajectory.pdb     multi-model PDB (no cell information)")),
            (L("  view.vmd           VMD の読み込みとセル", "  view.vmd           VMD loading and cell")
             if periodic else L("  view.vmd           VMD の読み込み", "  view.vmd           VMD loading")),
            L("  ovito_pipeline.py  OVITO の Python スクリプト (ADIT では実行を確かめていない)", "  ovito_pipeline.py  OVITO Python script (not run by ADIT)"),
            "", L("開き方:", "how to open:"),
            L("  TRAVIS:  travis -p trajectory.xyz", "  TRAVIS:  travis -p trajectory.xyz")]
    if periodic:
        c = a.cell.cellpar()
        out.append(L(f"           対話でセルの大きさを聞かれたら pm で答える: {c[0] * 100:.2f} {c[1] * 100:.2f} {c[2] * 100:.2f}"
                     + (" (直方体でないセルの答え方は TRAVIS のバージョンの説明を見てください)" if not np.allclose(c[3:], 90.0) else ""),
                     f"           when asked for the cell size, answer in pm: {c[0] * 100:.2f} {c[1] * 100:.2f} {c[2] * 100:.2f}"
                     + (" (for non-orthogonal cells, see the documentation of your TRAVIS version)" if not np.allclose(c[3:], 90.0) else "")))
    if dt:
        out.append(L(f"           時間の刻みを聞かれたら 1 フレームあたり {dt * stride:g} fs", f"           when asked for the time step, {dt * stride:g} fs per frame"))
    out += [L("           対話の答えを 1 行ずつ書いたファイルを -i で渡すと、同じ解析を繰り返せます: travis -p trajectory.xyz -i <答えのファイル> (TRAVIS の man page の -i)",
              "           a file with the interactive answers, one per line, can be passed with -i to repeat the analysis: travis -p trajectory.xyz -i <answers file> (-i in the TRAVIS man page)"),
            L("  VMD:     vmd -e view.vmd   (このディレクトリで)", "  VMD:     vmd -e view.vmd   (in this directory)"),
            (L("  OVITO:   GUI で trajectory.extxyz を開く (セルと周期境界も読まれる)。または pip install ovito のあと python ovito_pipeline.py",
               "  OVITO:   open trajectory.extxyz in the GUI (cell and periodicity are read), or pip install ovito and run python ovito_pipeline.py")
             if periodic else L("  OVITO:   GUI で trajectory.extxyz を開く (セルと周期境界はありません)。または pip install ovito のあと python ovito_pipeline.py",
                                "  OVITO:   open trajectory.extxyz in the GUI (no cell or periodic boundaries), or pip install ovito and run python ovito_pipeline.py")),
            ""]
    return "\n".join(out)
