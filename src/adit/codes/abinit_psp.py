
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from adit.errors import AditError
from adit.lang import L

SUFFIXES = (".pspnc", ".psp8", ".psp", ".fhi", ".upf" )
TEXT_SUFFIXES = (".pspnc", ".psp8", ".psp", ".fhi")


class AbinitPspError(AditError):
    pass


@dataclass(frozen=True)
class AbinitPspHeader:
    title: str
    zatom: float
    zion: float
    pspdat: str
    pspcod: int
    pspxc: int
    source: Path


def read_psp_header(path: Path | str) -> AbinitPspHeader:
    p = Path(path).expanduser()
    if not p.is_file():
        raise AbinitPspError(L(f"ファイルがありません: {p}", f"file not found: {p}"))
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()[:3]
    if len(lines) < 3:
        raise AbinitPspError(L(f"{p.name} は 3 行に満たないので、ヘッダを読めません",
                               f"{p.name} has fewer than three lines, so its header cannot be read"))
    try:
        zatom, zion = (float(v) for v in lines[1].split()[:2])
        pspdat = lines[1].split()[2] if len(lines[1].split()) > 2 else ""
        numbers = lines[2].split()
        pspcod, pspxc = int(numbers[0]), int(numbers[1])
    except (ValueError, IndexError) as ex:
        raise AbinitPspError(L(f"{p.name} のヘッダ (2・3 行目) を数として読めません: {ex}",
                               f"cannot read the header (lines 2 and 3) of {p.name} as numbers: {ex}")) from ex
    return AbinitPspHeader(title=lines[0].strip(), zatom=zatom, zion=zion, pspdat=pspdat,
                           pspcod=pspcod, pspxc=pspxc, source=p)


def describe(head: AbinitPspHeader) -> str:
    return L(f"価電子 {head.zion:g}、原子番号 {head.zatom:g}、形式 pspcod={head.pspcod}、交換相関 pspxc={head.pspxc} "
             "(番号は ABINIT の ixc の約束。汎関数の名前は入力の ixc と配布元の説明で確かめてください)",
             f"valence {head.zion:g}, atomic number {head.zatom:g}, format pspcod={head.pspcod}, "
             f"exchange-correlation pspxc={head.pspxc} (the number follows ABINIT's ixc convention; "
             "confirm the functional name against ixc in the input and the distributor's documentation)")
