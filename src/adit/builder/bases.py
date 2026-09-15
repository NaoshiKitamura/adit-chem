
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
from ase import Atoms

from adit.builder.model import Base, ClusterRef, PolymerRef, RecipeError, TwoD
from adit.lang import L
from adit.mixture import MAX_ATOMS, MixtureError, check_atom_limit

MAX_POLYMER_N = 500
MAX_POLYMER_ATOMS = 500


def limit(n: int, what: str = "") -> None:
    try:
        check_atom_limit(int(n), what)
    except MixtureError as ex:
        raise RecipeError(str(ex)) from ex


def file_sha256(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(Path(path).expanduser(), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def file_base(path: Path | str) -> Base:
    return Base(source="file", ref=str(path), sha256=file_sha256(path))


def build_base(base: Base) -> Atoms:
    from adit import structure as S

    src, ref = base.source, base.ref
    if src in ("2d", "cluster", "polymer"):
        if not isinstance(ref, dict):
            raise RecipeError(L(f"土台 {src} の ref は欄の辞書で書いてください (例 {{\"kind\": ...}})",
                                f"the ref of a {src} base must be an object (e.g. {{\"kind\": ...}})"))
        try:
            model = {"2d": TwoD, "cluster": ClusterRef, "polymer": PolymerRef}[src].model_validate(ref)
        except ValueError as ex:
            raise RecipeError(L(f"土台 {src} の指定を読めません: {ex}", f"cannot read the {src} base: {ex}")) from ex
        return {"2d": build_2d, "cluster": build_cluster, "polymer": build_polymer}[src](model)
    if not isinstance(ref, str):
        raise RecipeError(L(f"土台 {src} の ref は文字列です", f"the ref of a {src} base must be a string"))
    if src == "preset":
        return S.from_preset(ref)
    if src == "smiles":
        return S.from_smiles(ref)
    if src == "file":
        p = Path(ref).expanduser()
        if base.sha256 and p.is_file():
            now = file_sha256(p)
            if now != base.sha256:
                raise RecipeError(L(f"土台のファイル {p.name} の中身が、手順を作ったときから変わっています (SHA-256 が {base.sha256[:12]}… → {now[:12]}…)。"
                                    "いまの構造は保存済みの原子座標のまま使えます。新しい中身で作り直すなら、ファイルを選び直してください",
                                    f"the base file {p.name} has changed since the recipe was made (SHA-256 {base.sha256[:12]}... -> {now[:12]}...). "
                                    "The saved coordinates can still be used. To rebuild from the new file, select it again"))
        return S.from_file(p)
    if src == "bulk":
        return S.from_bulk(ref)
    if src == "surface":
        return S.from_surface(ref)
    if src == "mixture":
        from adit.mixture import MixtureSpec, build_mixture

        try:
            return build_mixture(MixtureSpec.from_ref(ref))
        except MixtureError as ex:
            raise RecipeError(str(ex)) from ex
    raise RecipeError(L(f"未知の土台: {src!r}", f"unknown base: {src!r}"))


def _nanotube_count(n: int, m: int, length: int) -> int:
    return 4 * (n * n + n * m + m * m) // math.gcd(2 * n + m, 2 * m + n) * length


def build_2d(r: TwoD) -> Atoms:
    from ase import build as B

    if r.vacuum <= 0:
        raise RecipeError(L("周期でない方向の真空 (vacuum) は 0 より大きくしてください (0 だと格子が退化します)",
                            "vacuum must be positive (the non-periodic direction would have zero length)"))
    try:
        if r.kind in ("graphene", "mx2"):
            if any(k < 1 for k in r.size):
                raise RecipeError(L(f"繰り返し size は 1 以上です: {r.size}", f"size must be at least 1: {r.size}"))
            per = 3 if r.kind == "mx2" else 2
            limit(per * r.size[0] * r.size[1] * r.size[2])
            if r.kind == "graphene":
                atoms = B.graphene(formula=r.formula or "C2", a=r.a or 2.46, thickness=r.thickness or 0.0, size=r.size, vacuum=r.vacuum)
            else:
                atoms = B.mx2(formula=r.formula or "MoS2", kind=r.mx2_kind, a=r.a or 3.18,
                              thickness=3.19 if r.thickness is None else r.thickness, size=r.size, vacuum=r.vacuum)
        elif r.kind == "nanotube":
            if r.n < 0 or r.m < 0 or (r.n == 0 and r.m == 0) or r.length < 1:
                raise RecipeError(L(f"カイラル指数 (n, m) は 0 以上で両方 0 ではなく、length は 1 以上です: ({r.n}, {r.m}), {r.length}",
                                    f"chiral indices (n, m) must be >= 0 and not both 0, length >= 1: ({r.n}, {r.m}), {r.length}"))
            limit(_nanotube_count(r.n, r.m, r.length))
            atoms = B.nanotube(r.n, r.m, length=r.length, bond=r.bond, symbol=r.symbol, vacuum=r.vacuum)
        else:  # nanoribbon
            if r.n < 1 or r.m < 1:
                raise RecipeError(L(f"ナノリボンの幅 n と長さ m は 1 以上です: ({r.n}, {r.m})", f"ribbon width n and length m must be at least 1: ({r.n}, {r.m})"))
            limit(8 * r.n * r.m + 8 * r.m)
            atoms = B.graphene_nanoribbon(r.n, r.m, type=r.ribbon_type, saturated=r.saturated, C_C=r.bond, vacuum=r.vacuum)
    except RecipeError:
        raise
    except Exception as ex:
        raise RecipeError(L(f"2 次元材料 ({r.kind}) を作れません: {ex}", f"cannot build the 2D material ({r.kind}): {ex}")) from ex
    atoms.pbc = (True, True, True)
    return atoms


def _cluster_bound(r: ClusterRef) -> int:
    if r.kind == "icosahedron":
        n = r.shells
        return (10 * n ** 3 - 15 * n ** 2 + 11 * n - 3) // 3
    if r.kind == "octahedron":
        return (2 * r.length ** 3 + r.length) // 3
    if r.kind == "decahedron":
        return 5 * (r.p + r.r + 1) ** 2 * (r.q + 2 * r.p + r.r)
    return 2 * r.size


def build_cluster(r: ClusterRef) -> Atoms:
    from ase import cluster as C

    for name in ("shells", "p", "q", "length", "size"):
        if getattr(r, name) < 1:
            raise RecipeError(L(f"{name} は 1 以上です", f"{name} must be at least 1"))
    if r.r < 0 or r.cutoff < 0:
        raise RecipeError(L("r と cutoff は 0 以上です", "r and cutoff must be >= 0"))
    bound = _cluster_bound(r)
    if bound > 4 * MAX_ATOMS:
        limit(bound)
    try:
        if r.kind == "icosahedron":
            atoms = C.Icosahedron(r.symbol, r.shells, latticeconstant=r.lattice_constant)
        elif r.kind == "decahedron":
            atoms = C.Decahedron(r.symbol, r.p, r.q, r.r, latticeconstant=r.lattice_constant)
        elif r.kind == "octahedron":
            atoms = C.Octahedron(r.symbol, r.length, cutoff=r.cutoff, latticeconstant=r.lattice_constant)
        else:
            if len(r.surfaces) != len(r.energies) or not r.surfaces:
                raise RecipeError(L("surfaces と energies は同じ数だけ書いてください", "surfaces and energies must have the same length"))
            atoms = C.wulff_construction(r.symbol, r.surfaces, r.energies, r.size, r.structure, latticeconstant=r.lattice_constant)
    except RecipeError:
        raise
    except Exception as ex:
        raise RecipeError(L(f"クラスター ({r.kind}, {r.symbol}) を作れません: {ex}", f"cannot build the cluster ({r.kind}, {r.symbol}): {ex}")) from ex
    limit(len(atoms))
    out = Atoms(symbols=atoms.get_chemical_symbols(), positions=atoms.get_positions())
    return out


def build_polymer(r: PolymerRef) -> Atoms:
    from adit.structure import has_rdkit

    if not has_rdkit():
        raise RecipeError(L("RDKit が無いのでポリマーは作れません", "RDKit is not installed, so polymers cannot be built"))
    from rdkit import Chem
    from rdkit.Chem import AllChem

    if not 1 <= r.n <= MAX_POLYMER_N:
        raise RecipeError(L(f"重合度は 1〜{MAX_POLYMER_N} にしてください (いま {r.n})", f"the degree of polymerization must be 1..{MAX_POLYMER_N} (now {r.n})"))
    unit = Chem.MolFromSmiles(r.unit)
    if unit is None:
        raise RecipeError(L(f"繰り返し単位の SMILES を解釈できません: {r.unit!r}", f"cannot parse the repeat-unit SMILES: {r.unit!r}"))
    dummies = [a for a in unit.GetAtoms() if a.GetAtomicNum() == 0]
    if len(dummies) != 2 or any(d.GetDegree() != 1 for d in dummies):
        raise RecipeError(L(f"繰り返し単位には連結点の * をちょうど 2 つ、それぞれ 1 本の結合で書いてください (例 ポリエチレン *CC*): {r.unit!r}",
                            f"the repeat unit needs exactly two * connection points, each with one bond (e.g. polyethylene *CC*): {r.unit!r}"))
    (h_d, t_d) = dummies
    head_nb, tail_nb = h_d.GetNeighbors()[0].GetIdx(), t_d.GetNeighbors()[0].GetIdx()
    link_type = unit.GetBondBetweenAtoms(t_d.GetIdx(), tail_nb).GetBondType()
    heavy = [a for a in unit.GetAtoms() if a.GetAtomicNum() != 0]
    if not heavy:
        raise RecipeError(L("繰り返し単位に原子がありません", "the repeat unit has no atoms"))
    rw = Chem.RWMol()
    prev_tail = None
    for _ in range(r.n):
        mp = {}
        for a in heavy:
            b = Chem.Atom(a.GetAtomicNum())
            b.SetFormalCharge(a.GetFormalCharge()); b.SetIsAromatic(a.GetIsAromatic())
            b.SetNumExplicitHs(a.GetNumExplicitHs()); b.SetNoImplicit(a.GetNoImplicit())
            mp[a.GetIdx()] = rw.AddAtom(b)
        for bd in unit.GetBonds():
            i, j = bd.GetBeginAtomIdx(), bd.GetEndAtomIdx()
            if i in mp and j in mp:
                rw.AddBond(mp[i], mp[j], bd.GetBondType())
                rw.GetBondBetweenAtoms(mp[i], mp[j]).SetIsAromatic(bd.GetIsAromatic())
        if prev_tail is not None:
            rw.AddBond(prev_tail, mp[head_nb], link_type)
        prev_tail = mp[tail_nb]
    mol = rw.GetMol()
    try:
        Chem.SanitizeMol(mol)
    except Exception as ex:
        raise RecipeError(L(f"つないだ鎖が化学的に解釈できません ({ex})。単位の SMILES と * の位置を確かめてください",
                            f"the joined chain cannot be sanitized ({ex}). Check the unit SMILES and the * positions")) from ex
    mol = Chem.AddHs(mol)
    if mol.GetNumAtoms() > MAX_POLYMER_ATOMS:
        raise RecipeError(L(f"鎖が {mol.GetNumAtoms()} 原子になり、上限 {MAX_POLYMER_ATOMS} を超えます (作る前に止めました)。重合度を下げてください",
                            f"the chain would have {mol.GetNumAtoms()} atoms, above the limit of {MAX_POLYMER_ATOMS} (stopped before building). Lower n"))
    params = AllChem.ETKDGv3()
    params.randomSeed = r.seed
    if mol.GetNumAtoms() > 100:
        params.useRandomCoords = True
    if AllChem.EmbedMolecule(mol, params) != 0:
        raise RecipeError(L(f"ポリマー ({r.unit} × {r.n}) の 3 次元座標を作れませんでした。seed を変えるか重合度を下げてください",
                            f"could not build 3D coordinates for the polymer ({r.unit} x {r.n}). Change the seed or lower n"))
    try:
        AllChem.MMFFOptimizeMolecule(mol, maxIters=200)
    except Exception:
        pass
    conf = mol.GetConformer()
    return Atoms(symbols=[a.GetSymbol() for a in mol.GetAtoms()],
                 positions=np.array([tuple(conf.GetAtomPosition(i)) for i in range(mol.GetNumAtoms())]))
