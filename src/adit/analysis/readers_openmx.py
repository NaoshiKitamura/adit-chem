"""Read OpenMX .out files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from ase import Atoms

HARTREE_EV = 27.211386245988
BOHR_ANG = 0.529177210903


@dataclass
class OpenmxOutput:
    energies_ev: list[float] = field(default_factory=list)
    frames: list[Atoms] = field(default_factory=list)
    populations: list[float] = field(default_factory=list)
    eigenvalues_ev: list[float] = field(default_factory=list)
    homo_index: int | None = None
    spin_moment: float | None = None
    note_no_cell: bool = False


def _cell_and_unit(lines: list[str]) -> tuple[np.ndarray | None, str]:
    cell, unit = None, "Ang"
    for i, line in enumerate(lines):
        if line.strip().startswith("Atoms.UnitVectors.Unit"):
            unit = line.split()[1]
        if line.strip().startswith("<Atoms.UnitVectors"):
            rows = []
            for row in lines[i + 1: i + 4]:
                rows.append([float(x) for x in row.split()[:3]])
            cell = np.array(rows)
    if cell is not None and unit.upper().startswith("AU"):
        cell = cell * BOHR_ANG
    return cell, unit


def read_openmx(path: Path) -> OpenmxOutput:
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    out = OpenmxOutput()
    cell, _ = _cell_and_unit(lines)
    symbols: list[str] = []
    frac: list[list[float]] = []
    mode = ""
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("Utot."):
            out.energies_ev.append(float(s.split()[1]) * HARTREE_EV)
            continue
        if "Fractional coordinates of the final structure" in line:
            mode, symbols, frac = "frac", [], []
            continue
        if "Mulliken populations" in line and "Decomposed" not in line:
            mode = "mulliken"
            out.populations = []
            continue
        if s.startswith("HOMO ="):
            out.homo_index = int(s.split("=")[1])
            continue
        if s.startswith("Total spin moment"):
            out.spin_moment = float(s.split()[-1])
            continue
        if mode == "frac":
            parts = s.split()
            if len(parts) == 5 and parts[0].isdigit():
                symbols.append(parts[1])
                frac.append([float(x) for x in parts[2:5]])
            elif symbols and s.startswith("*"):
                mode = ""
            continue
        if mode == "mulliken":
            parts = s.split()
            if len(parts) == 6 and parts[0].isdigit():
                out.populations.append(float(parts[4]))
            elif out.populations and s.startswith("Sum of MulP"):
                mode = ""
            continue
    if symbols and cell is not None:
        out.frames.append(Atoms(symbols=symbols, scaled_positions=np.array(frac), cell=cell, pbc=True))
    elif symbols:
        out.note_no_cell = True
    m = re.search(r"Eigenvalues \(Hartree\) for SCF KS-eq\.", "\n".join(lines))
    if m:
        out.eigenvalues_ev = _eigenvalues(lines)
    return out


def _eigenvalues(lines: list[str]) -> list[float]:
    values: list[float] = []
    reading = False
    for line in lines:
        if "Eigenvalues (Hartree) for SCF KS-eq." in line:
            reading, values = True, []
            continue
        if reading:
            parts = line.split()
            if len(parts) == 3 and parts[0].isdigit():
                values += [float(parts[1]) * HARTREE_EV, float(parts[2]) * HARTREE_EV]
            elif values and line.strip().startswith("*"):
                reading = False
    return values
