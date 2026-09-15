
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from adit.lang import L

BATCH_KINDS = ("compare", "conformers", "neb", "phonons", "elastic", "ts")
COMPARE_KINDS = ("adsorption", "reaction", "solvation")
RX_ROWS_MAX = 20
RX_ROWS_DEFAULT = 3
TS_MODES = ("ts", "irc", "ts+irc", "sella")


class BatchError(ValueError):
    pass


LABELS: dict[str, tuple[str, str]] = {
    "out": ("保存先", "Output directory"),
    "cmp_kind": ("組の種類", "Set kind"),
    "cmp_box": ("分子の箱", "Molecule box"),
    "cmp_slab": ("スラブの構造", "Slab structure"),
    "cmp_mol": ("分子の構造", "Molecule structure"),
    "cmp_ads": ("吸着した構造", "Adsorbed structure"),
    "cmp_slab_fixed": ("スラブの固定原子", "Fixed atoms of the slab"),
    "cmp_ads_fixed": ("吸着した構造の固定原子", "Fixed atoms of the adsorbed structure"),
    "cmp_structure_tools": ("画面の構造", "Screen structure"),
    "cmp_rows": ("反応に出てくる計算", "Runs of the reaction"),
    "cmp_solvent": ("溶媒側で変える手法の項目", "Method items changed for the solvated run"),
    "cmp_gas": ("気相側で変える手法の項目", "Method items changed for the gas-phase run"),
    "cmp_set_file": ("組の定義ファイル (set.json)", "Set file (set.json)"),
    "conf_n": ("作る配座の数", "Number of conformers to embed"),
    "conf_rmsd": ("重複とみなす RMSD [Å]", "RMSD for duplicates [Å]"),
    "conf_seed": ("乱数の種", "Random seed"),
    "conf_ff": ("力場", "Force field"),
    "conf_iters": ("反復の上限", "Max iterations"),
    "conf_all": ("全原子で測る", "All atoms"),
    "conf_keep": ("残す数", "Keep"),
    "conf_smiles": ("配座を作る SMILES", "SMILES for the conformers"),
    "neb_start": ("始状態の構造", "Initial-state structure"),
    "neb_end": ("終状態の構造", "Final-state structure"),
    "neb_images": ("中間の像の数", "Number of intermediate images"),
    "neb_mode": ("NEB の作り方", "NEB mode"),
    "neb_interp": ("補間", "Interpolation"),
    "neb_climb": ("climbing image", "Climbing image"),
    "neb_spring": ("SPRING (VASP)", "SPRING (VASP)"),
    "neb_kspring": ("K_SPRING (CP2K)", "K_SPRING (CP2K)"),
    "neb_opt": ("opt_scheme (QE)", "opt_scheme (QE)"),
    "ph_dim": ("超格子の倍率", "Supercell"),
    "ph_disp": ("変位の大きさ [Å]", "Displacement [Å]"),
    "ph_backend": ("変位の作り方", "How displacements are made"),
    "ph_dos_mesh": ("DOS の q 点のメッシュ", "DOS q-point mesh"),
    "ph_dos_width": ("DOS の幅 [THz]", "DOS width [THz]"),
    "el_strains": ("歪みの大きさ", "Strain magnitudes"),
    "el_comps": ("歪みを与える成分", "Strain components"),
    "ts_mode": ("作るもの", "What to generate"),
    "ts_irc": ("IRC もたどる (Sella)", "Also follow the IRC (Sella)"),
}


def lab(key: str) -> str:
    ja, en = LABELS[key]
    return L(ja, en)


def kind_title(kind: str) -> str:
    return {
        "compare": L("比べる計算の組", "Set of runs to compare"),
        "conformers": L("配座の候補", "Conformer candidates"),
        "neb": L("反応経路 (NEB)", "Reaction path (NEB)"),
        "phonons": L("フォノン (有限変位)", "Phonons (finite displacements)"),
        "elastic": L("弾性定数 (歪み)", "Elastic constants (strains)"),
        "ts": L("遷移状態と IRC", "Transition state and IRC"),
    }[kind]


def kind_note(kind: str) -> str:
    return {
        "compare": L("同じ条件のまま、吸着・反応・溶媒和の組の計算をまとめて作り、条件の違いを compare.json に書きます。",
                     "Creates the runs of an adsorption, reaction or solvation set with identical settings and records the differing settings in compare.json."),
        "conformers": L("RDKit の ETKDG で配座を作り、力場で最適化して重複を除き、残った配座ごとの計算にします (分子の構造で使います)。",
                        "Embeds conformers with RDKit ETKDG, optimizes them with a force field, drops duplicates, and makes one run per remaining conformer (molecules only)."),
        "neb": L("始状態と終状態の構造から中間の像を作ります。計算コードの NEB (VASP / QE / CP2K) か、像ごとの一点計算のどちらかです。",
                 "Interpolates images between two end points, either as the code's own NEB (VASP / QE / CP2K) or as one single point per image."),
        "phonons": L("超格子に有限変位を入れた計算を並べます (DFTB+ / VASP / QE、3 方向とも周期の構造)。実行したあと力を集めます。",
                     "Creates the finite-displacement runs of a supercell (DFTB+ / VASP / QE, periodic in all three directions); the forces are collected after running."),
        "elastic": L("成分ごとに歪みを与えた計算を並べます (DFTB+ / VASP / QE、3 方向とも周期の構造)。実行したあと応力を集めます。",
                     "Creates one run per strained component (DFTB+ / VASP / QE, periodic in all three directions); the stress is collected after running."),
        "ts": L("ORCA は遷移状態の探索 (OptTS) と IRC を、xtb と機械学習ポテンシャルは ASE + Sella のスクリプトを作ります。",
                "For ORCA it writes the transition-state search (OptTS) and the IRC; for xtb and machine-learning potentials it writes an ASE + Sella script."),
    }[kind]


def kind_names() -> list[tuple[str, str]]:
    return [(k, kind_title(k)) for k in BATCH_KINDS]


def compare_kind_names() -> list[tuple[str, str]]:
    return [("adsorption", L("吸着 (スラブ + 分子 → 吸着した構造)", "Adsorption (slab + molecule → adsorbed)")),
            ("reaction", L("反応 (係数を付けた計算の組)", "Reaction (runs with coefficients)")),
            ("solvation", L("溶媒和 (気相 ↔ 溶媒)", "Solvation (gas phase ↔ solvent)"))]


def box_names() -> list[tuple[str, str]]:
    return [("as_is", L("そのまま", "as is")), ("slab_cell", L("スラブと同じセルの中心に置く", "centered in the slab cell"))]


def ff_names() -> list[tuple[str, str]]:
    from adit.conformers import FORCE_FIELDS
    return [(x, x) for x in FORCE_FIELDS]


def neb_mode_names() -> list[tuple[str, str]]:
    return [("native", L("計算コードの NEB (VASP / QE / CP2K)", "the code's own NEB (VASP / QE / CP2K)")),
            ("images", L("像ごとの一点計算 (どのコードでも)", "one single point per image (any code)"))]


def interp_names() -> list[tuple[str, str]]:
    return [("idpp", "idpp"), ("linear", L("直線 (linear)", "linear"))]


def backend_names() -> list[tuple[str, str]]:
    return [("auto", L("自動 (phonopy があれば phonopy)", "automatic (phonopy if installed)")), ("phonopy", "phonopy"), ("ase", L("ASE の Phonons", "ASE Phonons"))]


def qe_opt_names() -> list[tuple[str, str]]:
    from adit.neb_setup import QE_OPT_SCHEMES
    return [("", L("(neb.x の既定)", "(neb.x default)"))] + [(x, x) for x in QE_OPT_SCHEMES]


MLIP_PACKAGES = {"mace_mp": "mace-torch", "mace_off": "mace-torch", "chgnet": "chgnet"}


def mlip_pip_line(family: str) -> str:
    pkg = MLIP_PACKAGES.get(family, "")
    if not pkg:
        return L("種類を選ぶと、実行する環境に入れるパッケージ (pip) を出します。", "Choose a potential to see the package to install with pip.")
    return L(f"実行する環境に入れるもの:  pip install ase {pkg}   (PyTorch を一緒に入れるので数 GB になります)",
             f"Install in the environment that runs it:  pip install ase {pkg}   (it pulls in PyTorch, several GB)")


def ts_mode_names() -> list[tuple[str, str]]:
    return [("ts", L("ORCA: 遷移状態の探索 (! OptTS)", "ORCA: transition-state search (! OptTS)")),
            ("irc", L("ORCA: IRC (! Freq IRC)", "ORCA: IRC (! Freq IRC)")),
            ("ts+irc", L("ORCA: 段階に分けて OptTS → IRC", "ORCA: OptTS then IRC as two stages")),
            ("sella", L("ASE + Sella のスクリプト (xtb・機械学習ポテンシャル)", "ASE + Sella script (xtb, machine-learning potentials)"))]


def _s(values: dict, key: str, default: str = "") -> str:
    return str(values.get(key, default) or default).strip()


def _b(values: dict, key: str) -> bool:
    return str(values.get(key, "") or "").strip().lower() in ("1", "on", "true", "yes")


def _num(values: dict, key: str, default: float | None = None) -> float | None:
    text = _s(values, key)
    if not text:
        if default is None:
            return None
        return default
    try:
        return float(text)
    except ValueError as ex:
        raise BatchError(L(f"{lab(key)}: 数値として読めません: {text!r}", f"{lab(key)}: not a number: {text!r}")) from ex


def _int(values: dict, key: str, default: int | None = None) -> int | None:
    x = _num(values, key, None if default is None else float(default))
    if x is None:
        return None
    if x != int(x):
        raise BatchError(L(f"{lab(key)}: 整数にしてください", f"{lab(key)}: must be an integer"))
    return int(x)


def _required(values: dict, key: str) -> str:
    text = _s(values, key)
    if not text:
        raise BatchError(L(f"{lab(key)}: 入れてください (既定値はありません)", f"{lab(key)}: required (there is no default)"))
    return text


def atom_numbers(text: str, what: str) -> list[int]:
    out: list[int] = []
    for part in str(text or "").replace(" ", "").split(","):
        if not part:
            continue
        try:
            if "-" in part[1:]:
                a, _, b = part.partition("-")
                lo, hi = int(a), int(b)
                if lo < 1 or hi < lo:
                    raise ValueError
                out += list(range(lo - 1, hi))
            else:
                n = int(part)
                if n < 1:
                    raise ValueError
                out.append(n - 1)
        except ValueError as ex:
            raise BatchError(L(f"{what}: 1 始まりの番号で書いてください (例 1-4,7): {part!r}",
                               f"{what}: write 1-based numbers (e.g. 1-4,7): {part!r}")) from ex
    return sorted(set(out))


def _member(values: dict, file_key: str, fixed_key: str | None = None) -> dict:
    m: dict = {"structure": _s(values, file_key) or "base"}
    if fixed_key and _s(values, fixed_key):
        m["fixed_atoms"] = atom_numbers(_s(values, fixed_key), lab(fixed_key))
    return m


def _method_overrides(values: dict, key: str, required: bool) -> dict | None:
    text = _s(values, key)
    if not text:
        if required:
            raise BatchError(L(f'{lab(key)}: 変える項目を {{"solvation": "alpb", "solvent": "water"}} のような JSON で書いてください',
                               f'{lab(key)}: write the items to change as JSON, e.g. {{"solvation": "alpb", "solvent": "water"}}'))
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as ex:
        raise BatchError(L(f"{lab(key)}: JSON として読めません ({ex.msg})", f"{lab(key)}: not valid JSON ({ex.msg})")) from ex
    if not isinstance(data, dict):
        raise BatchError(L(f'{lab(key)}: {{"項目": "値"}} の形にしてください', f'{lab(key)}: must look like {{"item": "value"}}'))
    return {"method": data}


def reaction_rows(values: dict) -> list[dict[str, str]]:
    n = _int(values, "cmp_rx_rows", RX_ROWS_DEFAULT) or RX_ROWS_DEFAULT
    n = max(1, min(n, RX_ROWS_MAX))
    return [{c: _s(values, f"cmp_rx{i}_{c}") for c in ("name", "file", "nu", "charge", "mult")} for i in range(1, n + 1)]


def compare_data(values: dict) -> tuple[dict, Path]:
    from adit.compare_sets import load_set

    if _s(values, "cmp_set_file"):
        return load_set(_s(values, "cmp_set_file"))
    kind = _s(values, "cmp_kind", "adsorption")
    if kind not in COMPARE_KINDS:
        raise BatchError(L(f"{lab('cmp_kind')}: {kind!r} は使えません", f"{lab('cmp_kind')}: unknown kind {kind!r}"))
    where = Path.cwd()
    if kind == "adsorption":
        return {"kind": "adsorption", "molecule_box": _s(values, "cmp_box", "as_is"),
                "slab": _member(values, "cmp_slab", "cmp_slab_fixed"),
                "molecule": _member(values, "cmp_mol"),
                "adsorbed": _member(values, "cmp_ads", "cmp_ads_fixed")}, where
    if kind == "reaction":
        members = []
        for row in reaction_rows(values):
            if not any(row.values()):
                continue
            if not row["name"]:
                raise BatchError(L(f"{lab('cmp_rows')}: 名前を入れてください (ディレクトリの名前になります)",
                                   f"{lab('cmp_rows')}: enter a name (it becomes a directory name)"))
            m: dict = {"name": row["name"], "structure": row["file"] or "base", "nu": row["nu"]}
            try:
                m["nu"] = float(row["nu"]) if row["nu"] else 0.0
            except ValueError as ex:
                raise BatchError(L(f"{lab('cmp_rows')}: {row['name']} の係数 ν が数値として読めません: {row['nu']!r}",
                                   f"{lab('cmp_rows')}: coefficient ν of {row['name']} is not a number: {row['nu']!r}")) from ex
            for key, name in (("charge", "charge"), ("mult", "multiplicity")):
                if row[key]:
                    try:
                        m[name] = int(float(row[key]))
                    except ValueError as ex:
                        raise BatchError(L(f"{lab('cmp_rows')}: {row['name']} の {key} が整数として読めません: {row[key]!r}",
                                           f"{lab('cmp_rows')}: {key} of {row['name']} is not an integer: {row[key]!r}")) from ex
            members.append(m)
        return {"kind": "reaction", "members": members}, where
    data: dict = {"kind": "solvation", "structure": "base", "solvent": _method_overrides(values, "cmp_solvent", True)}
    gas = _method_overrides(values, "cmp_gas", False)
    if gas is not None:
        data["gas"] = gas
    return data, where


def components(values: dict) -> list[int]:
    text = _s(values, "el_comps")
    if text:
        try:
            out = [int(x) for x in text.replace(" ", "").split(",") if x]
        except ValueError as ex:
            raise BatchError(L(f"{lab('el_comps')}: 1〜6 の整数をカンマで区切って書いてください: {text!r}",
                               f"{lab('el_comps')}: write integers 1..6 separated by commas: {text!r}")) from ex
    else:
        out = [j for j in range(1, 7) if _b(values, f"el_c{j}")]
    if not out:
        raise BatchError(L(f"{lab('el_comps')}: 成分を 1 つ以上選んでください", f"{lab('el_comps')}: choose at least one component"))
    return out


@dataclass
class BatchResult:
    kind: str
    dirs: list[Path]
    out: Path
    next_steps: list[str] = field(default_factory=list)
    analysis_dir: str = ""
    compare_base: str = ""


def _next_steps(kind: str, out: Path, values: dict) -> tuple[list[str], str, str]:
    run = L("1. 各ディレクトリの計算を実行します (この PC なら保存先で bash submit.sh、クラスタなら README.txt の投入の例)。",
            "1. Run the calculations (on this PC: bash submit.sh in the output directory; on a cluster: see the submission example in README.txt).")
    if kind == "compare":
        return ([run, L(f"2. 解析の「組にして比べる」で、基準のディレクトリに {out} を入れて読み込みます (compare.json を読みます)。",
                        f"2. In \"Compare a set of runs\" in the analysis, set the base directory to {out} and load it (it reads compare.json)."),
                 L(f"   コマンドなら adit-analyze {out} --compare", f"   On the command line: adit-analyze {out} --compare")], "", str(out))
    if kind == "conformers" or (kind == "neb" and _s(values, "neb_mode", "native") == "images"):
        return ([run, L(f"2. 解析でこのディレクトリ ({out}) を開くと、値ごとのエネルギーの表と図が出ます (scan.json)。",
                        f"2. Open this directory ({out}) in the analysis to get the table and plot of the energies (scan.json)."),
                 L(f"   コマンドなら adit-analyze {out} --scan", f"   On the command line: adit-analyze {out} --scan")], str(out), "")
    if kind == "neb":
        return ([run, L(f"2. 解析でこのディレクトリ ({out}) を開くと、エネルギーの曲線と障壁が出ます。",
                        f"2. Open this directory ({out}) in the analysis to get the energy curve and the barrier.")], str(out), "")
    if kind == "phonons":
        return ([run, L(f"2. python {out / 'phonon_collect.py'}   (ADIT が入った Python で。力を集めて band.yaml を書きます)",
                        f"2. python {out / 'phonon_collect.py'}   (with the Python that has ADIT installed; collects the forces and writes band.yaml)"),
                 L(f"3. そのあと解析でこのディレクトリ ({out}) を開くと、フォノン分散の図が出ます。",
                   f"3. Then open this directory ({out}) in the analysis to plot the dispersion.")], str(out), "")
    if kind == "elastic":
        return ([run, L(f"2. python {out / 'elastic_collect.py'}   (ADIT が入った Python で。応力を集めて elastic_constants.csv を書きます)",
                        f"2. python {out / 'elastic_collect.py'}   (with the Python that has ADIT installed; collects the stress and writes elastic_constants.csv)")], "", "")
    return ([run, L(f"2. 終わったら解析でこのディレクトリ ({out}) を開きます。", f"2. When it has finished, open this directory ({out}) in the analysis.")], str(out), "")


def run_batch(kind: str, spec, cfg, out_dir, values: dict, *, overwrite: bool = False) -> BatchResult:
    if kind not in BATCH_KINDS:
        raise BatchError(f"unknown batch kind: {kind!r}")
    out = Path(str(out_dir)).expanduser()
    if not str(out_dir).strip():
        raise BatchError(L(f"{lab('out')}: 指定してください。", f"{lab('out')}: choose one."))
    if kind == "compare":
        from adit.compare_sets import write_compare_set
        data, where = compare_data(values)
        dirs = write_compare_set(spec, cfg, out, data, where, overwrite=overwrite)
    elif kind == "conformers":
        from adit.conformers import DEFAULT_SEED, write_conformers
        n = _int(values, "conf_n")
        if n is None:
            raise BatchError(L(f"{lab('conf_n')}: 入れてください (既定値はありません)", f"{lab('conf_n')}: required (there is no default)"))
        rmsd = _num(values, "conf_rmsd")
        if rmsd is None:
            raise BatchError(L(f"{lab('conf_rmsd')}: 入れてください (既定値はありません)", f"{lab('conf_rmsd')}: required (there is no default)"))
        dirs = write_conformers(spec, cfg, out, n=n, rmsd=rmsd, seed=_int(values, "conf_seed", DEFAULT_SEED),
                                force_field=_s(values, "conf_ff", "MMFF94"), heavy_only=not _b(values, "conf_all"),
                                max_iters=_int(values, "conf_iters", 200), keep=_int(values, "conf_keep"),
                                smiles=_s(values, "conf_smiles") or None, overwrite=overwrite)
    elif kind == "neb":
        from adit.neb_setup import NebOptions, write_neb
        images = _int(values, "neb_images")
        if images is None:
            raise BatchError(L(f"{lab('neb_images')}: 入れてください (既定値はありません)", f"{lab('neb_images')}: required (there is no default)"))
        opts = NebOptions(images=images, mode=_s(values, "neb_mode", "native"), interpolation=_s(values, "neb_interp", "idpp"),
                          climb=_b(values, "neb_climb"), vasp_spring=_num(values, "neb_spring"), cp2k_k_spring=_num(values, "neb_kspring"),
                          qe_opt_scheme=_s(values, "neb_opt") or None)
        dirs = write_neb(spec, cfg, out, _s(values, "neb_start") or "spec", _required(values, "neb_end"), opts,
                         where=Path.cwd(), overwrite=overwrite)
    elif kind == "phonons":
        from adit.phonon_setup import parse_dim, write_phonons
        dirs = write_phonons(spec, cfg, out, parse_dim(_required(values, "ph_dim")), distance=_num(values, "ph_disp"),
                             backend=_s(values, "ph_backend", "auto"),
                             dos_mesh=parse_dim(_s(values, "ph_dos_mesh")) if _s(values, "ph_dos_mesh") else None,
                             dos_width_thz=_num(values, "ph_dos_width"), overwrite=overwrite)
    elif kind == "elastic":
        from adit.elastic_setup import parse_values, write_elastic
        dirs = write_elastic(spec, cfg, out, parse_values(_required(values, "el_strains")), components(values), overwrite=overwrite)
    else:
        from adit.ts_setup import write_sella, write_ts
        mode = _s(values, "ts_mode", "ts")
        if mode not in TS_MODES:
            raise BatchError(L(f"{lab('ts_mode')}: {mode!r} は使えません", f"{lab('ts_mode')}: unknown value {mode!r}"))
        if mode == "sella":
            dirs = write_sella(spec, cfg, out, irc=_b(values, "ts_irc"), overwrite=overwrite)
        else:
            dirs = write_ts(spec, cfg, out, mode, overwrite=overwrite)
    steps, analysis_dir, compare_base = _next_steps(kind, out, values)
    return BatchResult(kind=kind, dirs=list(dirs), out=out, next_steps=steps, analysis_dir=analysis_dir, compare_base=compare_base)


def result_message(res: BatchResult) -> str:
    names = "\n".join(f"  {d.name}" for d in res.dirs)
    head = L(f"{res.out} の中に {len(res.dirs)} 個のディレクトリを作りました。\n{names}",
             f"Created {len(res.dirs)} directories in {res.out}:\n{names}")
    return head + "\n\n" + L("次にすること", "Next steps") + "\n" + "\n".join(res.next_steps)



DOC_FIELDS: dict[str, tuple[str, str, str]] = {
    "wfc_cutoff": ("ecutwfc", "ecutwfc", "Ry"),
    "suggested_wfc_cutoff": ("ecutwfc", "ecutwfc", "Ry"),
    "sssp_cutoff_wfc": ("ecutwfc", "ecutwfc", "Ry"),
    "rho_cutoff": ("ecutrho", "ecutrho", "Ry"),
    "suggested_rho_cutoff": ("ecutrho", "ecutrho", "Ry"),
    "sssp_cutoff_rho": ("ecutrho", "ecutrho", "Ry"),
    "ENMAX": ("encut", "encut", "eV"),
    "ENMIN": ("encut", "encut", "eV"),
    "comment": ("cp2k_kind", "", ""),
    "hubbard_derivative": ("dftb_third", "", ""),
    "zeta": ("dftb_third", "", ""),
    "s6": ("d3", "d3_s6", ""),
    "s8": ("d3", "d3_s8", ""),
    "a1": ("d3", "d3_a1", ""),
    "a2": ("d3", "d3_a2", ""),
    "spin_constant": ("dftb_sk", "", ""),
}
DOC_MAX_LINES = 8


@dataclass(frozen=True)
class DocLine:
    text: str
    tip: str
    field: str = ""
    value: str = ""


def doc_lines(spec, cfg=None) -> dict[str, list[DocLine]]:
    from adit.docvalues import documented_settings, documented_values

    out: dict[str, list[DocLine]] = {}
    for v in documented_values(spec, cfg):
        target = DOC_FIELDS.get(v.quantity)
        if target is None:
            continue
        group, fieldname, unit = target
        name = Path(v.source).name
        el = f"{v.element} " if v.element else ""
        val = f"{v.value:g}" if isinstance(v.value, float) else str(v.value)
        text = L(f"{name}:{v.line} の記載: {el}{v.quantity} = {val} {v.unit}".rstrip(),
                 f"written in {name}:{v.line}: {el}{v.quantity} = {val} {v.unit}".rstrip())
        tip = L(f"{v.source} の {v.line} 行目:\n{v.text}\n\nADIT は値を選びません (この行に書かれている値を、そのまま見せています)。",
                f"line {v.line} of {v.source}:\n{v.text}\n\nADIT does not choose values; this is what the line says.")
        insertable = bool(fieldname) and isinstance(v.value, float) and (v.unit or "") == unit
        out.setdefault(group, []).append(DocLine(text=text, tip=tip, field=fieldname if insertable else "",
                                                 value=val if insertable else ""))
    for setting in documented_settings(spec):
        text = L(f"{setting.source} の記載: {setting.key} = {setting.value}",
                 f"Written in {setting.source}: {setting.key} = {setting.value}")
        tip = L(f"{setting.note}\n取得日: {setting.retrieved}\n{setting.url}\n\nADIT の推奨値ではありません。",
                f"{setting.note_en}\nRetrieved: {setting.retrieved}\n{setting.url}\n\nThis is not a recommendation by ADIT.")
        out.setdefault(setting.group, []).append(DocLine(text=text, tip=tip, field=setting.field, value=setting.value))
    return out


def doc_more(lines: list[DocLine]) -> str:
    n = len(lines) - DOC_MAX_LINES
    return L(f"ほか {n} 件", f"{n} more") if n > 0 else ""


__all__ = ["BATCH_KINDS", "BatchError", "BatchResult", "DocLine", "LABELS", "atom_numbers", "compare_data", "components",
           "doc_lines", "doc_more", "kind_note", "kind_title", "lab", "reaction_rows", "result_message", "run_batch"]
