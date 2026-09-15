
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
from ase import Atoms

from adit.errors import AditValueError
from adit.lang import L

EXTERNAL_SUFFIXES = {".xtc": ("MDAnalysis", "mdtraj", "chemfiles"), ".trr": ("MDAnalysis", "mdtraj", "chemfiles"),
                     ".dcd": ("MDAnalysis", "mdtraj", "chemfiles"), ".nc": ("MDAnalysis", "mdtraj", "chemfiles"),
                     ".h5": ("mdtraj",), ".h5md": ("MDAnalysis",), ".gsd": ("MDAnalysis",), ".tng": ("MDAnalysis",),
                     ".lammpstrj": ("MDAnalysis", "mdtraj", "chemfiles")}
CONVERT_HINTS = {".xtc": "gmx trjconv -f {name} -o traj.xyz", ".trr": "gmx trjconv -f {name} -o traj.xyz",
                 ".dcd": "vmd -dispdev text -e ...  /  mdconvert {name} -o traj.xyz (MDTraj)",
                 ".nc": "cpptraj -y {name} -x traj.xyz"}


class ExternalTrajectoryError(AditValueError):
    pass


def available() -> list[str]:
    return [name for name in ("MDAnalysis", "mdtraj", "chemfiles") if importlib.util.find_spec(name)]


def needs_external(path: Path) -> bool:
    return Path(path).suffix.lower() in EXTERNAL_SUFFIXES


def _with_mdanalysis(path: Path, topology: Path | None):
    import MDAnalysis as mda

    u = mda.Universe(str(topology), str(path)) if topology else mda.Universe(str(path))
    symbols = _symbols_from(u)
    out = []
    for ts in u.trajectory:
        cell = np.zeros((3, 3))
        pbc = False
        if ts.dimensions is not None and all(ts.dimensions[:3] > 0):
            from MDAnalysis.lib.mdamath import triclinic_vectors

            cell = np.asarray(triclinic_vectors(ts.dimensions), dtype=float)
            pbc = True
        out.append(Atoms(symbols=symbols, positions=np.asarray(ts.positions, dtype=float), cell=cell, pbc=pbc))
    return out, f"MDAnalysis {mda.__version__}"


def _symbols_from(universe) -> list[str]:
    for attr in ("elements", "types", "names"):
        values = getattr(universe.atoms, attr, None)
        if values is None:
            continue
        symbols = [str(v).strip().capitalize()[:2] for v in values]
        from ase.data import chemical_symbols

        if all(s in chemical_symbols for s in symbols):
            return symbols
    return ["X"] * len(universe.atoms)


def _with_mdtraj(path: Path, topology: Path | None):
    import mdtraj

    traj = mdtraj.load(str(path), top=str(topology)) if topology else mdtraj.load(str(path))
    symbols = [a.element.symbol if a.element is not None else "X" for a in traj.topology.atoms]
    out = []
    for i in range(traj.n_frames):
        cell = np.asarray(traj.unitcell_vectors[i] * 10.0, dtype=float) if traj.unitcell_vectors is not None else np.zeros((3, 3))
        out.append(Atoms(symbols=symbols, positions=np.asarray(traj.xyz[i] * 10.0, dtype=float),   # nm → Å
                         cell=cell, pbc=traj.unitcell_vectors is not None))
    return out, f"MDTraj {getattr(mdtraj, '__version__', '?')}"


def _with_chemfiles(path: Path, topology: Path | None):
    import chemfiles

    out = []
    with chemfiles.Trajectory(str(path)) as traj:
        if topology:
            traj.set_topology(str(topology))
        for frame in traj:
            atoms = frame.atoms
            symbols = [a.type or a.name or "X" for a in atoms]
            cell = np.asarray(frame.cell.matrix, dtype=float)
            pbc = bool(np.any(cell))
            out.append(Atoms(symbols=symbols, positions=np.asarray(frame.positions, dtype=float), cell=cell, pbc=pbc))
    return out, f"chemfiles {chemfiles.__version__}"


def read_external(path: Path | str, topology: Path | str | None = None):
    path = Path(path)
    topology = Path(topology) if topology else None
    libs = available()
    if not libs:
        hint = CONVERT_HINTS.get(path.suffix.lower(), "")
        raise ExternalTrajectoryError(L(
            f"{path.name} を読むには MDAnalysis か MDTraj か chemfiles のどれかが要ります "
            "(`pip install MDAnalysis` など)。"
            + (f"入れずに済ませるなら、その軌跡を書いたソフトで変換してください: {hint.format(name=path.name)}" if hint else ""),
            f"reading {path.name} needs MDAnalysis, MDTraj or chemfiles (`pip install MDAnalysis`)."
            + (f" Or convert it with the program that wrote it: {hint.format(name=path.name)}" if hint else "")))
    errors = []
    for lib in libs:
        try:
            return {"MDAnalysis": _with_mdanalysis, "mdtraj": _with_mdtraj, "chemfiles": _with_chemfiles}[lib](path, topology)
        except Exception as ex:
            errors.append(f"{lib}: {ex}")
    raise ExternalTrajectoryError(L(
        f"{path.name} を読めませんでした ({'; '.join(errors)})",
        f"could not read {path.name} ({'; '.join(errors)})"))


def find_topology(run_dir: Path, path: Path) -> Path | None:
    for name in ("conf.gro", "adit.gro", "topology.psf", "system.psf", "coordinates.pdb", "topol.tpr"):
        candidate = Path(run_dir) / name
        if candidate.is_file():
            return candidate
    for pattern in ("*.gro", "*.psf", "*.pdb", "*.prmtop", "*.parm7"):
        for candidate in sorted(Path(run_dir).glob(pattern)):
            if candidate != path:
                return candidate
    return None
