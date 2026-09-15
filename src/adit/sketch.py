
from __future__ import annotations

import math
from dataclasses import dataclass, field

from adit.lang import L

BOND_PX = 44.0
CLICK_PX = 10.0
ELEMENTS = ["C", "N", "O", "S", "P", "F", "Cl", "Br", "I", "Si", "B"]
ELEMENT_COLORS = {"C": "#202020", "N": "#2050D0", "O": "#D02020", "S": "#C8A000", "P": "#E07800", "F": "#30A030", "Cl": "#30A030", "Br": "#A03020", "I": "#7030A0", "Si": "#807070", "B": "#D0A080"}
ELEMENT_COLORS_DARK = {"N": "#7FA6FF", "O": "#FF7A7A", "S": "#F0D060", "P": "#FFA850", "F": "#6FD88A", "Cl": "#6FD88A", "Br": "#E8907A", "I": "#C09CFF", "Si": "#C8BEBE", "B": "#EBC8A8"}
TEMPLATES = {"benzene": (6, True), "cyclohexane": (6, False), "cyclopentane": (5, False)}
TEMPLATE_FORMULAS = {"benzene": "C6H6", "cyclohexane": "C6H12", "cyclopentane": "C5H10"}
BOND_SYMBOLS = {1: "—", 2: "=", 3: "≡"}
WINDOW_TITLE = "ADIT Draw"
HISTORY_MAX = 200


@dataclass
class SAtom:
    x: float
    y: float
    elem: str = "C"
    charge: int = 0


@dataclass
class SBond:
    a: int
    b: int
    order: int = 1


@dataclass
class Sketch:
    atoms: list[SAtom] = field(default_factory=list)
    bonds: list[SBond] = field(default_factory=list)

    def bond_between(self, i: int, j: int) -> SBond | None:
        for b in self.bonds:
            if {b.a, b.b} == {i, j}:
                return b
        return None

    def degree(self, i: int) -> int:
        return sum(1 for b in self.bonds if i in (b.a, b.b))

    def component_count(self) -> int:
        unseen = set(range(len(self.atoms))); count = 0
        neighbours = {i: set() for i in unseen}
        for bond in self.bonds:
            neighbours[bond.a].add(bond.b); neighbours[bond.b].add(bond.a)
        while unseen:
            count += 1; stack = [unseen.pop()]
            while stack:
                for other in neighbours[stack.pop()] & unseen:
                    unseen.remove(other); stack.append(other)
        return count

    def h_counts(self) -> list[int]:
        try:
            mol = self.to_mol()
            return [a.GetTotalNumHs() for a in mol.GetAtoms()]
        except Exception:
            return [0] * len(self.atoms)

    def remove_atom(self, i: int) -> None:
        self.bonds = [b for b in self.bonds if i not in (b.a, b.b)]
        for b in self.bonds:
            b.a -= b.a > i; b.b -= b.b > i
        del self.atoms[i]

    # ---- RDKit ----
    def to_mol(self):
        from rdkit import Chem

        m = Chem.RWMol()
        for a in self.atoms:
            at = Chem.Atom(a.elem); at.SetFormalCharge(a.charge); m.AddAtom(at)
        kinds = {1: Chem.BondType.SINGLE, 2: Chem.BondType.DOUBLE, 3: Chem.BondType.TRIPLE}
        for b in self.bonds:
            m.AddBond(b.a, b.b, kinds[b.order])
        mol = m.GetMol()
        Chem.SanitizeMol(mol)
        return mol

    def to_smiles(self) -> str:
        from rdkit import Chem

        if not self.atoms:
            return ""
        return Chem.MolToSmiles(self.to_mol())

    def formula(self) -> str:
        from rdkit.Chem.rdMolDescriptors import CalcMolFormula

        try:
            return CalcMolFormula(self.to_mol()) if self.atoms else ""
        except Exception:
            return ""

    @classmethod
    def from_smiles(cls, smiles: str) -> "Sketch":
        from rdkit import Chem
        from rdkit.Chem import rdDepictor

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError(L(f"SMILES を解釈できません: {smiles!r}", f"cannot parse SMILES: {smiles!r}"))
        Chem.Kekulize(mol, clearAromaticFlags=True)
        rdDepictor.Compute2DCoords(mol)
        conf = mol.GetConformer()
        pts = [conf.GetAtomPosition(k) for k in range(mol.GetNumAtoms())]
        cx = (min(p.x for p in pts) + max(p.x for p in pts)) / 2 if pts else 0.0
        cy = (min(p.y for p in pts) + max(p.y for p in pts)) / 2 if pts else 0.0
        sk = cls()
        for at in mol.GetAtoms():
            p = pts[at.GetIdx()]
            sk.atoms.append(SAtom((p.x - cx) * BOND_PX, -(p.y - cy) * BOND_PX, at.GetSymbol(), at.GetFormalCharge()))
        order_of = {Chem.BondType.SINGLE: 1, Chem.BondType.DOUBLE: 2, Chem.BondType.TRIPLE: 3}
        for b in mol.GetBonds():
            sk.bonds.append(SBond(b.GetBeginAtomIdx(), b.GetEndAtomIdx(), order_of.get(b.GetBondType(), 1)))
        return sk


def ring_atoms(name: str, cx: float, cy: float) -> tuple[list["SAtom"], list["SBond"]]:
    if name not in TEMPLATES:
        raise ValueError(L(f"知らない環です: {name} (あるもの: {', '.join(TEMPLATES)})",
                           f"unknown ring: {name} (known: {', '.join(TEMPLATES)})"))
    n, aromatic = TEMPLATES[name]
    r = BOND_PX / (2 * math.sin(math.pi / n))
    atoms = []
    for k in range(n):
        t = 2 * math.pi * k / n - math.pi / 2
        atoms.append(SAtom(cx + r * math.cos(t), cy + r * math.sin(t), "C"))
    bonds = [SBond(k, (k + 1) % n, 2 if (aromatic and k % 2 == 0) else 1) for k in range(n)]
    return atoms, bonds


def sketch_from_dict(data: dict) -> "Sketch":
    sk = Sketch()
    for a in data.get("atoms") or []:
        elem = str(a.get("elem", "C"))
        if not elem.isalpha() or len(elem) > 2:
            raise ValueError(L(f"元素記号として読めません: {elem!r}", f"not a chemical symbol: {elem!r}"))
        sk.atoms.append(SAtom(float(a.get("x", 0.0)), float(a.get("y", 0.0)), elem, int(a.get("charge", 0))))
    n = len(sk.atoms)
    for b in data.get("bonds") or []:
        i, j, order = int(b.get("a", -1)), int(b.get("b", -1)), int(b.get("order", 1))
        if not (0 <= i < n and 0 <= j < n) or i == j:
            raise ValueError(L(f"結合の相手が範囲の外です: {i}-{j}", f"bond refers to atoms out of range: {i}-{j}"))
        if order not in (1, 2, 3):
            raise ValueError(L(f"結合の次数は 1・2・3 のどれかです: {order}", f"the bond order must be 1, 2 or 3: {order}"))
        sk.bonds.append(SBond(i, j, order))
    return sk


def sketch_to_dict(sk: "Sketch") -> dict:
    return {"atoms": [{"x": round(a.x, 2), "y": round(a.y, 2), "elem": a.elem, "charge": a.charge} for a in sk.atoms],
            "bonds": [{"a": b.a, "b": b.b, "order": b.order} for b in sk.bonds]}
