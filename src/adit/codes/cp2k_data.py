
from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

EXECUTABLES = ("cp2k.psmp", "cp2k.ssmp", "cp2k.popt", "cp2k.sopt", "cp2k")
_SYMBOL = re.compile(r"^[A-Z][a-z]?$")
_NUMBER = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eEdD][-+]?\d+)?$")
_Q = re.compile(r"-q(\d+)$")


@dataclass(frozen=True)
class Entry:
    element: str
    names: tuple[str, ...]
    text: str
    valence: int | None

    @property
    def q(self) -> int | None:
        for n in self.names:
            m = _Q.search(n)
            if m:
                return int(m.group(1))
        return None


@lru_cache(maxsize=16)
def _parse(path: str, mtime: float, potential: bool) -> dict[str, tuple[Entry, ...]]:
    out: dict[str, list[Entry]] = {}
    head: list[str] | None = None
    body: list[str] = []

    def flush() -> None:
        if head is None:
            return
        valence = None
        if potential and len(body) > 1:
            first = body[1].split("#", 1)[0].split()
            if first and all(t.isdigit() for t in first):
                valence = sum(int(t) for t in first)
        out.setdefault(head[0], []).append(Entry(head[0], tuple(head[1:]), "\n".join(body), valence))

    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n").rstrip()
            code = line.split("#", 1)[0].split()
            if not code:
                continue
            if _SYMBOL.match(code[0]) and len(code) >= 2 and not _NUMBER.match(code[1]):
                flush()
                head, body = code, [line]
            elif head is not None:
                body.append(line)
    flush()
    return {k: tuple(v) for k, v in out.items()}


class Cp2kData:

    def __init__(self, root: Path | None, source: str = ""):
        self.root = root
        self.source = source

    @classmethod
    def discover(cls, configured: str = "", path: str | None = None) -> "Cp2kData":
        if configured:
            return cls(Path(configured).expanduser(), "cp2k_data")
        env = os.environ.get("CP2K_DATA_DIR", "")
        if env and Path(env).expanduser().is_dir():
            return cls(Path(env).expanduser(), "CP2K_DATA_DIR")
        for exe in EXECUTABLES:
            w = shutil.which(exe, path=path)
            if w:
                d = Path(w).resolve().parent.parent / "share" / "cp2k" / "data"
                if d.is_dir():
                    return cls(d, w)
        return cls(None, "")

    @property
    def found(self) -> bool:
        return self.root is not None and self.root.is_dir()

    def resolve(self, filename: str) -> Path | None:
        p = Path(filename).expanduser()
        if p.is_absolute():
            return p if p.is_file() else None
        if self.root is None:
            return None
        q = self.root / filename
        return q if q.is_file() else None

    def files(self, prefix: str = "") -> list[str]:
        if not self.found:
            return []
        return sorted(p.name for p in self.root.iterdir() if p.is_file() and p.name.startswith(prefix))

    def entries(self, filename: str, element: str, *, potential: bool) -> tuple[Entry, ...]:
        p = self.resolve(filename)
        if p is None:
            return ()
        return _parse(str(p), p.stat().st_mtime, potential).get(element, ())

    def names_for(self, filename: str, element: str, *, potential: bool) -> list[str]:
        return [e.names[0] for e in self.entries(filename, element, potential=potential)]

    def find(self, filename: str, element: str, name: str, *, potential: bool) -> Entry | None:
        return next((e for e in self.entries(filename, element, potential=potential) if name in e.names), None)
