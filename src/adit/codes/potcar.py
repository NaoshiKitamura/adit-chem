
from __future__ import annotations

from adit.errors import AditError
from adit.lang import L

import re
from dataclasses import dataclass
from pathlib import Path

_TITEL = re.compile(r"^\s*TITEL\s*=\s*(.+?)\s*$", re.M)
_ZVAL = re.compile(r"\bZVAL\s*=\s*([0-9.]+)")
_ENMAX = re.compile(r"\bENMAX\s*=\s*([0-9.]+)")
_HEADER_BYTES = 4000


class PotcarError(AditError):
    pass


@dataclass(frozen=True)
class PotcarHeader:
    name: str
    titel: str
    zval: float
    enmax: float  # eV


class PotcarLibrary:

    def __init__(self, root: Path | str, potcar_set: str):
        self.root = Path(root).expanduser()
        self.potcar_set = potcar_set
        self.set_dir = self.root / potcar_set
        if not self.set_dir.is_dir():
            raise PotcarError(L(f"POTCAR ライブラリに {potcar_set!r} がありません: {self.set_dir}", f"POTCAR library has no {potcar_set!r}: {self.set_dir}"))

    @classmethod
    def open_if_present(cls, root: str | None, potcar_set: str) -> "PotcarLibrary | None":
        if not root or not (Path(root).expanduser() / potcar_set).is_dir():
            return None
        return cls(root, potcar_set)

    def names_for(self, element: str) -> list[str]:
        out = []
        for d in sorted(self.set_dir.iterdir()):
            if d.is_dir() and (d / "POTCAR").is_file() and (d.name == element or d.name.startswith(element + "_")):
                out.append(d.name)
        return out

    def has(self, name: str) -> bool:
        return (self.set_dir / name / "POTCAR").is_file()

    def header(self, name: str) -> PotcarHeader:
        return read_potcar_header(self.set_dir / name / "POTCAR", name=name)


def read_potcar_header(path: Path | str, name: str | None = None) -> PotcarHeader:
    p = Path(path).expanduser()
    if not p.is_file():
        raise PotcarError(L(f"POTCAR がありません: {p}", f"POTCAR not found: {p}"))
    with open(p, "rb") as f:
        head = f.read(_HEADER_BYTES).decode("utf-8", errors="replace")
    t, z, e = _TITEL.search(head), _ZVAL.search(head), _ENMAX.search(head)
    if not (t and z and e):
        raise PotcarError(L(f"{p} のヘッダに TITEL / ZVAL / ENMAX が見つかりません",
                            f"TITEL / ZVAL / ENMAX not found in the header of {p}"))
    return PotcarHeader(name=name or p.parent.name, titel=t.group(1), zval=float(z.group(1)), enmax=float(e.group(1)))
