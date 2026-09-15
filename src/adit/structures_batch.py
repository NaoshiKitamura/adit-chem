"""Generate the same settings for many structures at once."""

from __future__ import annotations

from adit.errors import AditValueError
import json
import re
from dataclasses import dataclass
from pathlib import Path

from ase import Atoms

from adit.batch import Item, with_comment, write_items, write_top
from adit.lang import L
from adit.spec import AtomsData, CalculationSpec

STRUCTURES_FILE = "structures.json"


class StructuresError(AditValueError):
    pass


@dataclass(frozen=True)
class Loaded:
    name: str
    source: str
    atoms: Atoms


def _safe(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z._+-]+", "_", name).strip("_") or "structure"


def expand_paths(patterns: list[str]) -> list[Path]:
    found: list[Path] = []
    for pattern in patterns:
        p = Path(pattern).expanduser()
        if p.is_file():
            found.append(p)
            continue
        if p.is_dir():
            raise StructuresError(L(f"{p} はディレクトリです。ファイルの名前か、* を使った書き方で指定してください "
                                    f"(例 {p}/*.xyz)",
                                    f"{p} is a directory; give file names or a pattern such as {p}/*.xyz"))
        matches = sorted(Path().glob(pattern)) if not p.is_absolute() else sorted(Path(p.anchor).glob(str(p.relative_to(p.anchor))))
        if not matches:
            raise StructuresError(L(f"構造のファイルが見つかりません: {pattern}", f"no structure file matches: {pattern}"))
        found += [m for m in matches if m.is_file()]
    if not found:
        raise StructuresError(L("構造のファイルが 1 つもありません", "no structure files were given"))
    return found


def load_structures(patterns: list[str]) -> list[Loaded]:
    from ase.io import read

    out: list[Loaded] = []
    for path in expand_paths(patterns):
        try:
            frames = read(path, index=":")
        except Exception as ex:
            raise StructuresError(L(f"{path} を構造として読めません: {ex}",
                                    f"cannot read {path} as a structure: {ex}")) from ex
        frames = frames if isinstance(frames, list) else [frames]
        if not frames:
            raise StructuresError(L(f"{path} に構造がありません", f"{path} contains no structure"))
        for i, atoms in enumerate(frames):
            if not len(atoms):
                raise StructuresError(L(f"{path} の {i + 1} 番目の構造に原子がありません",
                                        f"structure {i + 1} in {path} has no atoms"))
            name = _safe(path.stem) if len(frames) == 1 else f"{_safe(path.stem)}_{i + 1:03d}"
            source = str(path) if len(frames) == 1 else f"{path} [{i + 1}]"
            out.append(Loaded(name=name, source=source, atoms=atoms))
    names = [x.name for x in out]
    duplicated = sorted({n for n in names if names.count(n) > 1})
    if duplicated:
        raise StructuresError(L(f"同じ名前になる構造があります: {', '.join(duplicated)}。ファイル名を分けてください",
                                f"these structures would share a directory name: {', '.join(duplicated)}; rename the files"))
    return out


def items_for(spec: CalculationSpec, loaded: list[Loaded]) -> list[Item]:
    items: list[Item] = []
    for one in loaded:
        structure = spec.structure.model_copy(update={
            "source": "file", "source_ref": one.source, "atoms": AtomsData.from_ase(one.atoms),
            "fixed_atoms": [], "fixed_axes": {}, "velocities": None})
        new = spec.model_copy(update={"structure": structure})
        note = L(f"構造の一括生成: {one.source} を読み込みました (条件は元の spec.json のまま)",
                 f"batch over structures: read from {one.source} (all other settings come from the original spec.json)")
        items.append(Item(dir=one.name, spec=with_comment(new, note), readme=["  " + note]))
    return items


def write_enumerated(spec: CalculationSpec, cfg, out_dir: Path | str, core: str, group_texts: list[str], *,
                     overwrite: bool = False, seed: int = 0) -> list[Path]:
    from adit.enumerate_r import enumerate_substituents, parse_groups

    products = enumerate_substituents(core, parse_groups(group_texts), seed=seed)
    loaded = [Loaded(name=p.name, source=f"SMILES {p.smiles}", atoms=p.atoms) for p in products]
    items = items_for(spec, loaded)
    for item, product in zip(items, products):
        item.spec = item.spec.model_copy(update={"structure": item.spec.structure.model_copy(
            update={"source": "smiles", "source_ref": product.smiles})})
    out = Path(out_dir).expanduser()
    dirs = write_items(items, cfg, out, overwrite=overwrite)
    try:
        from rdkit import rdBase

        rdkit_version = rdBase.rdkitVersion
    except Exception:
        rdkit_version = ""
    (out / STRUCTURES_FILE).write_text(json.dumps(
        {"core": core, "groups": parse_groups(group_texts), "seed": seed, "rdkit_version": rdkit_version,
         "coordinates": "RDKit ETKDG + MMFF (adit.structure.from_smiles)",
         "structures": [{"dir": p.name, "smiles": p.smiles, "substituents": {str(k): v for k, v in p.substituents.items()},
                         "formula": p.atoms.get_chemical_formula(), "natoms": len(p.atoms)} for p in products]},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_top(out, cfg, spec, dirs,
              [L(f"  骨格 {core} に置換基を差し込んだ {len(dirs)} 個の計算です (組み合わせは {STRUCTURES_FILE})。",
                 f"  {len(dirs)} calculations built by substituting into the core {core} (the combinations are in {STRUCTURES_FILE})."),
               L(f"  座標は RDKit {rdkit_version or '(バージョン不明)'} が乱数の種 {seed} で作ったものです (同じ種なら同じ座標)。",
                 f"  The coordinates come from RDKit {rdkit_version or '(unknown version)'} with random seed {seed} (the same seed gives the same coordinates)."),
               L("  座標は RDKit (ETKDG + MMFF) が作った 1 つの配座です。配座を探すなら adit-gen --conformers を使います。",
                 "  The coordinates are one conformer from RDKit (ETKDG + MMFF); use adit-gen --conformers to search conformers.")],
              "置換基の列挙", "substituent enumeration")
    return dirs


def write_structures(spec: CalculationSpec, cfg, out_dir: Path | str, patterns: list[str], *,
                     overwrite: bool = False) -> list[Path]:
    """Write one directory per structure. Nothing is written if any of them fails to assemble."""
    loaded = load_structures(patterns)
    items = items_for(spec, loaded)
    out = Path(out_dir).expanduser()
    dirs = write_items(items, cfg, out, overwrite=overwrite)
    (out / STRUCTURES_FILE).write_text(json.dumps(
        {"structures": [{"dir": one.name, "source": one.source, "formula": one.atoms.get_chemical_formula(),
                         "natoms": len(one.atoms)} for one in loaded]},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_top(out, cfg, spec, dirs,
              [L(f"  同じ条件で {len(dirs)} 個の構造を計算します (構造の出典は {STRUCTURES_FILE})。",
                 f"  {len(dirs)} structures are calculated with the same settings (their sources are in {STRUCTURES_FILE})."),
               L("  実行したあとは adit-report <この親ディレクトリ>/*/ --results-csv results.csv で結果を 1 枚の表にできます。",
                 "  After running them, adit-report <this parent>/*/ --results-csv results.csv puts the results in one table.")],
              "構造の一括生成", "batch over structures")
    return dirs
