
from __future__ import annotations

from adit.errors import AditError
from adit.lang import L

import re
from dataclasses import dataclass
from pathlib import Path

_ATTR = re.compile(r'(\w+)="([^"]*)"')
_HEADER = re.compile(r"<PP_HEADER([^>]*)>", re.S)
_HEADER_BYTES = 8000


class UpfError(AditError):
    pass


@dataclass(frozen=True)
class UpfHeader:
    filename: str
    element: str
    z_valence: float
    functional: str
    pseudo_type: str
    wfc_cutoff: float | None
    rho_cutoff: float | None


class UpfLibrary:
    def __init__(self, root: Path | str, pseudo_set: str):
        self.root = Path(root).expanduser()
        self.pseudo_set = pseudo_set
        self.set_dir = self.root / pseudo_set
        if not self.set_dir.is_dir():
            raise UpfError(L(f"擬ポテンシャルのライブラリに {pseudo_set!r} がありません: {self.set_dir}", f"pseudopotential library has no {pseudo_set!r}: {self.set_dir}"))

    @classmethod
    def open_if_present(cls, root: str | None, pseudo_set: str) -> "UpfLibrary | None":
        if not root or not (Path(root).expanduser() / pseudo_set).is_dir():
            return None
        return cls(root, pseudo_set)

    def files_for(self, element: str) -> list[str]:
        out = []
        for p in sorted(self.set_dir.iterdir()):
            if p.suffix.lower() == ".upf" and re.match(rf"^{re.escape(element)}[._-]", p.name, re.I):
                out.append(p.name)
        return out

    def has(self, filename: str) -> bool:
        return (self.set_dir / filename).is_file()

    def path(self, filename: str) -> Path:
        return self.set_dir / filename

    def doc_files(self) -> dict[str, Path]:
        return {n: self.set_dir / n for n in ("LICENSE", "README", "README.md", "LICENSE.txt") if (self.set_dir / n).is_file()}

    def chi_labels(self, filename: str) -> list[str]:
        out = []
        rx = re.compile(r'<PP_CHI\.\d+[^>]*?\blabel="([^"]*)"')
        with open(self.set_dir / filename, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = rx.search(line)
                if m:
                    out.append(m.group(1).strip().upper())
        return out

    def header(self, filename: str) -> UpfHeader:
        return read_upf_header(self.set_dir / filename, name=filename)


def read_upf_header(path: Path | str, name: str | None = None) -> UpfHeader:
    p = Path(path).expanduser()
    if not p.is_file():
        raise UpfError(L(f"UPF がありません: {p}", f"UPF not found: {p}"))
    with open(p, "rb") as f:
        head = f.read(_HEADER_BYTES).decode("utf-8", errors="replace")
    m = _HEADER.search(head)
    if not m:
        raise UpfError(L(f"{p.name} に <PP_HEADER> が見つかりません (UPF v2 の形ではありません)",
                         f"<PP_HEADER> not found in {p.name} (not UPF v2)"))
    attrs = dict(_ATTR.findall(m.group(1)))
    try:
        return UpfHeader(filename=name or p.name, element=attrs["element"].strip(), z_valence=float(attrs["z_valence"]),
                         functional=attrs.get("functional", "").strip(), pseudo_type=attrs.get("pseudo_type", "").strip(),
                         wfc_cutoff=float(attrs["wfc_cutoff"]) if attrs.get("wfc_cutoff") else None,
                         rho_cutoff=float(attrs["rho_cutoff"]) if attrs.get("rho_cutoff") else None)
    except (KeyError, ValueError) as ex:
        raise UpfError(L(f"{p.name} のヘッダに element / z_valence がありません: {ex}",
                         f"header of {p.name} lacks element / z_valence: {ex}")) from ex
