
from __future__ import annotations

from adit.lang import L

import itertools
import re
from dataclasses import dataclass, field
from pathlib import Path

_SKF_NAME = re.compile(r"^([A-Z][a-z]?)-([A-Z][a-z]?)\.skf$")
_SHELLS = re.compile(r"<Shells>\s*([^<]*?)\s*</Shells>", re.IGNORECASE)
_ELEM_VALUE = re.compile(r"^\s*([A-Z][a-z]?)\s*=\s*(-?\d+(?:\.\d+)?)\s*$")
_ZETA = re.compile(r"zeta\s*=\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
_ELEM_HEADER = re.compile(r"^\s*([A-Z][a-z]?)\s*:\s*$")
_L_OF = {"s": 0, "p": 1, "d": 2, "f": 3}
_NAME_OF_L = {v: k for k, v in _L_OF.items()}

REQUIRED_DOCS = ("LICENSE", "README")


class SKSetError(Exception):
    pass


@dataclass
class SKSet:
    name: str
    root: Path
    pairs: dict[tuple[str, str], Path] = field(default_factory=dict)

    @classmethod
    def from_dir(cls, root: Path | str, name: str | None = None) -> "SKSet":
        root = Path(root)
        if not root.is_dir():
            raise SKSetError(L(f"SK セットのディレクトリがありません: {root}", f"Slater-Koster set directory not found: {root}"))
        pairs: dict[tuple[str, str], Path] = {}
        for p in sorted(root.iterdir()):
            m = _SKF_NAME.match(p.name)
            if m:
                pairs[(m.group(1), m.group(2))] = p
        if not pairs:
            raise SKSetError(L(f"*.skf が 1 つもありません: {root}", f"no *.skf files in {root}"))
        return cls(name=name or root.name, root=root, pairs=pairs)

    @property
    def elements(self) -> list[str]:
        return sorted({a for (a, b) in self.pairs if a == b})

    def missing_pairs(self, elements: list[str]) -> list[tuple[str, str]]:
        return [(a, b) for a, b in itertools.product(elements, repeat=2) if (a, b) not in self.pairs]

    def required_files(self, elements: list[str]) -> dict[tuple[str, str], Path]:
        missing = self.missing_pairs(elements)
        if missing:
            raise SKSetError(L(f"セット {self.name} に無いペアがあります: {missing}", f"pairs missing from set {self.name}: {missing}"))
        return {(a, b): self.pairs[(a, b)] for a, b in itertools.product(elements, repeat=2)}

    def doc_files(self) -> dict[str, Path]:
        return {n: self.root / n for n in REQUIRED_DOCS if (self.root / n).is_file()}

    def max_angular_momentum(self, element: str) -> str:
        path = self.pairs.get((element, element))
        if path is None:
            raise SKSetError(L(f"{element}-{element}.skf がありません", f"{element}-{element}.skf not found"))
        text = path.read_text(encoding="utf-8", errors="replace")
        m = _SHELLS.search(text)
        if not m:
            raise SKSetError(L(f"{path.name} の文書に <Shells> が無く、角運動量を決められません", f"{path.name} has no <Shells> in its documentation; cannot decide the angular momentum"))
        shells = m.group(1).split()
        ls = [_L_OF[s[-1].lower()] for s in shells if s[-1].lower() in _L_OF]
        if not ls:
            raise SKSetError(L(f"{path.name} の <Shells> を解釈できません: {m.group(1)!r}", f"cannot parse <Shells> of {path.name}: {m.group(1)!r}"))
        return _NAME_OF_L[max(ls)]


    def hubbard_derivs(self) -> dict[str, float] | None:
        readme = self.root / "README"
        if not readme.is_file():
            return None
        lines = readme.read_text(encoding="utf-8", errors="replace").splitlines()
        start = next((i for i, l in enumerate(lines) if "hubbard derivative" in l.lower()), None)
        if start is None:
            return None
        out: dict[str, float] = {}
        for l in lines[start + 1:]:
            m = _ELEM_VALUE.match(l)
            if m:
                out[m.group(1)] = float(m.group(2))
            elif out and l.strip() == "":
                break
        return out or None

    def damping_exponent(self) -> float | None:
        readme = self.root / "README"
        if not readme.is_file():
            return None
        m = _ZETA.search(readme.read_text(encoding="utf-8", errors="replace"))
        return float(m.group(1)) if m else None

    def spin_constants(self) -> dict[str, float] | None:
        f = self.root / "spinw.txt"
        if not f.is_file():
            return None
        out: dict[str, float] = {}
        current: str | None = None
        rows: list[list[float]] = []

        def flush() -> None:
            if current and rows:
                n = len(rows)
                if any(len(r) != n for r in rows):
                    raise SKSetError(L(f"spinw.txt の {current} が正方行列ではありません", f"{current} in spinw.txt is not a square matrix"))
                out[current] = rows[-1][-1]

        for l in f.read_text(encoding="utf-8", errors="replace").splitlines():
            m = _ELEM_HEADER.match(l)
            if m:
                flush(); current, rows = m.group(1), []
            elif l.strip() and current:
                rows.append([float(x) for x in l.split()])
        flush()
        return out or None


def discover_sets(sk_root: Path | str) -> dict[str, SKSet]:
    sk_root = Path(sk_root)
    found: dict[str, SKSet] = {}
    if not sk_root.is_dir():
        return found
    for d in sorted(sk_root.iterdir()):
        if d.is_dir():
            try:
                found[d.name] = SKSet.from_dir(d)
            except SKSetError:
                continue
    return found
