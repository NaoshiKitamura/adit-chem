"""Enumerate structures by substituting R groups into a scaffold SMILES."""

from __future__ import annotations

from adit.errors import AditValueError
import itertools
import re
from dataclasses import dataclass

from ase import Atoms

from adit.lang import L
from adit.structure import StructureError, from_smiles, has_rdkit

LABEL = re.compile(r"\[\*:(\d+)\]")


class EnumerateError(AditValueError):
    pass


@dataclass(frozen=True)
class Product:
    name: str
    smiles: str
    substituents: dict[int, str]
    atoms: Atoms


def _combine(core: str, groups: dict[int, str]) -> str:
    out = core
    for index, smiles in groups.items():
        token = f"[*:{index}]"
        if token not in out:
            raise EnumerateError(L(f"骨格に {token} がありません", f"the core has no {token}"))
        piece = smiles.strip()
        if not piece:
            raise EnumerateError(L("置換基の SMILES が空です", "an empty substituent SMILES was given"))
        wrapped = piece if len(piece) == 1 or piece.startswith("[") and piece.endswith("]") else f"({piece})"
        out = out.replace(token, wrapped)
    return out


def enumerate_substituents(core: str, groups: dict[int, list[str]], *, seed: int = 0) -> list[Product]:
    if not has_rdkit():
        raise EnumerateError(L("RDKit が無いので置換基の列挙はできません", "RDKit is not installed, so substituents cannot be enumerated"))
    labels = sorted({int(x) for x in LABEL.findall(core)})
    if not labels:
        raise EnumerateError(L("骨格に [*:1] のような印がありません", "the core has no [*:1]-style attachment point"))
    missing = [n for n in labels if n not in groups]
    if missing:
        raise EnumerateError(L(f"置換基を指定していない印があります: {missing}",
                               f"no substituents were given for these attachment points: {missing}"))
    extra = [n for n in groups if n not in labels]
    if extra:
        raise EnumerateError(L(f"骨格にない印に置換基が指定されています: {extra}",
                               f"substituents were given for attachment points the core does not have: {extra}"))
    out: list[Product] = []
    for combo in itertools.product(*[groups[n] for n in labels]):
        chosen = dict(zip(labels, combo))
        smiles = _combine(core, chosen)
        try:
            atoms = from_smiles(smiles, seed=seed)
        except StructureError as ex:
            raise EnumerateError(L(f"{smiles} から構造を作れません: {ex}",
                                   f"cannot build a structure from {smiles}: {ex}")) from ex
        name = "_".join(f"r{n}-{groups[n].index(chosen[n]) + 1:02d}" for n in labels)
        out.append(Product(name=name, smiles=smiles, substituents=chosen, atoms=atoms))
    names = [p.name for p in out]
    if len(set(names)) != len(names):
        raise EnumerateError(L("同じ名前の組み合わせができました", "two combinations produced the same name"))
    return out


def parse_groups(texts: list[str]) -> dict[int, list[str]]:
    groups: dict[int, list[str]] = {}
    for text in texts:
        if "=" not in text:
            raise EnumerateError(L(f"置換基は「印の番号=SMILES,SMILES,…」の形で書いてください: {text!r}",
                                   f"write substituents as 'label=SMILES,SMILES,...': {text!r}"))
        label, _, rest = text.partition("=")
        try:
            index = int(label.strip())
        except ValueError as ex:
            raise EnumerateError(L(f"印の番号を数として読めません: {label!r}",
                                   f"the attachment-point label is not a number: {label!r}")) from ex
        values = [v.strip() for v in rest.split(",") if v.strip()]
        if not values:
            raise EnumerateError(L(f"印 {index} の置換基がありません", f"no substituents for attachment point {index}"))
        if index in groups:
            raise EnumerateError(L(f"印 {index} が 2 回書かれています", f"attachment point {index} was given twice"))
        groups[index] = values
    return groups
