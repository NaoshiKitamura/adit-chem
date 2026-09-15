
from __future__ import annotations

from adit.errors import AditValueError
import csv
import json
from pathlib import Path

import numpy as np

from adit import batch
from adit.lang import L
from adit.spec import AtomsData, CalculationSpec

CODES = ("dftbplus", "vasp", "espresso")
ELASTIC_FILE = "elastic.json"
COLLECT_SCRIPT = "elastic_collect.py"
VOIGT = {1: (0, 0), 2: (1, 1), 3: (2, 2), 4: (1, 2), 5: (0, 2), 6: (0, 1)}
MAX_RUNS = 200


class ElasticError(AditValueError):
    pass


def parse_values(text: str, what: str = "strains") -> list[float]:
    try:
        return [float(x) for x in str(text).split(",") if x.strip()]
    except ValueError as ex:
        raise ElasticError(L(f"数をカンマで区切って書いてください: {text!r}", f"write numbers separated by commas: {text!r}")) from ex


def strain_matrix(j: int, delta: float) -> np.ndarray:
    e = np.zeros((3, 3))
    a, b = VOIGT[j]
    if a == b:
        e[a, a] = delta
    else:
        e[a, b] = e[b, a] = delta / 2.0
    return e


def dir_name(j: int, delta: float) -> str:
    return f"e{j}_{delta:+.5f}".rstrip("0").rstrip(".")


def plan(spec: CalculationSpec, strains: list[float], components: list[int]) -> list[tuple[str, int, float, object]]:
    if spec.method.code not in CODES:
        raise ElasticError(L(f"弾性定数の一括生成は {' / '.join(CODES)} だけです (応力を出力から読めるコード)", f"elastic constants support {' / '.join(CODES)} only (codes whose stress can be read)"))
    if not all(spec.structure.atoms.pbc):
        raise ElasticError(L("弾性定数は 3 方向とも周期の構造で作ります", "elastic constants need a structure periodic in all three directions"))
    t = spec.task
    if t.type not in ("single_point", "geometry_optimization"):
        raise ElasticError(L("計算の種類は一点計算 (原子を動かさない) か構造最適化 (原子の緩和あり) にしてください", "the task must be a single point (clamped ions) or a geometry optimization (relaxed ions)"))
    if t.type == "geometry_optimization" and t.relax_cell != "no":
        raise ElasticError(L("歪みを与えたセルを保つので、格子を動かす指定 (task.relax_cell) は no にしてください", "the strained cell must be kept, so task.relax_cell must be no"))
    if not strains:
        raise ElasticError(L("歪みの大きさを 1 つ以上書いてください (例 -0.01,0.01)", "give at least one strain (e.g. -0.01,0.01)"))
    if any(not np.isfinite(s) for s in strains):
        raise ElasticError(L(f"歪みの大きさに数でない値 (nan) や無限大があります: {strains}", f"the strains contain a non-finite value (nan or infinity): {strains}"))
    if any(s == 0 for s in strains) or len(set(strains)) != len(strains):
        raise ElasticError(L("歪みの大きさは 0 以外で、同じ値を 2 回書かないでください (歪みなしは e0 として自動で作ります)", "strains must be non-zero and distinct (the unstrained run e0 is made automatically)"))
    if any(abs(s) >= 1 for s in strains):
        raise ElasticError(L("歪みの大きさは -1 と 1 のあいだにしてください (セルが裏返ります)", "strains must be between -1 and 1 (the cell would invert)"))
    bad = [c for c in components if c not in VOIGT]
    if bad or not components or len(set(components)) != len(components):
        raise ElasticError(L("成分は 1〜6 (Voigt の番号) を重ねずに書いてください", "components must be distinct Voigt indices 1..6"))
    if len(components) * len(strains) + 1 > MAX_RUNS:
        raise ElasticError(L(f"計算の数が {len(components) * len(strains) + 1} になり、上限 {MAX_RUNS} を超えます", f"{len(components) * len(strains) + 1} runs exceed the limit {MAX_RUNS}"))
    names = {dir_name(j, d) for j in components for d in strains}
    if len(names) != len(components) * len(strains):
        raise ElasticError(L(f"歪みの大きさの差が小さすぎて、ディレクトリの名前 (小数点以下 5 桁) を分けられません: {strains}",
                             f"the strains are too close to give different directory names (five decimals): {strains}"))
    a0 = spec.atoms
    out = [("e0", 0, 0.0, a0)]
    for j in components:
        for d in strains:
            a = a0.copy()
            a.set_cell(np.asarray(a0.cell) @ (np.eye(3) + strain_matrix(j, d)), scale_atoms=True)
            out.append((dir_name(j, d), j, d, a))
    return out


def write_elastic(spec: CalculationSpec, cfg, out_dir: Path | str, strains: list[float], components: list[int] | None = None,
                  *, overwrite: bool = False) -> list[Path]:
    from adit import __version__

    out = Path(out_dir).expanduser()
    components = components or [1, 2, 3, 4, 5, 6]
    runs = plan(spec, strains, components)
    base = spec.model_dump(mode="json")
    base["handoff"] = None
    items, meshes = [], {}
    for name, j, d, a in runs:
        data = dict(base, structure=dict(base["structure"], atoms=AtomsData.from_ase(a).model_dump(mode="json"), velocities=None))
        data["meta"] = dict(base["meta"], comment=(base["meta"].get("comment", "") + f" elastic strain {j}:{d:+g}").strip())
        s = CalculationSpec.model_validate(data)
        if s.kpoints is not None:
            meshes[name] = "x".join(map(str, s.kpoints.resolved_mesh(s.structure.atoms.cell)))
        items.append(batch.Item(name, s, [L("== 弾性定数の歪み ==", "== Strain for elastic constants =="),
                                          L(f"  Voigt の成分 {j} に歪み {d:+g} (0 は歪みなし)。応力だけを使います。全体は ../README.txt" if j else "  歪みなしの計算 (直線の当てはめの δ = 0 の点)。全体は ../README.txt",
                                            f"  strain {d:+g} on Voigt component {j}; only the stress is used. See ../README.txt" if j else "  unstrained run (the δ = 0 point of the fits). See ../README.txt")]))
    dirs = batch.write_items(items, cfg, out, overwrite=overwrite)
    batch.write_json(out / ELASTIC_FILE, {"generated_by": f"adit {__version__}", "code": spec.method.code, "task": spec.task.type,
                                          "components": components, "strains": strains,
                                          "runs": [{"dir": n, "component": j, "strain": d} for n, j, d, _ in runs], "kpoints_mesh": meshes,
                                          "convention": "Voigt 1=xx 2=yy 3=zz 4=yz 5=xz 6=xy; engineering shear strain; stress in GPa, ASE sign (compression negative)"})
    (out / COLLECT_SCRIPT).write_text(
        "#!/usr/bin/env python3\n" + L("# ADIT が生成。各歪みの応力を集めて、弾性定数の表 (elastic_constants.csv) を書く。ADIT が入った Python で実行する\n",
                                        "# generated by ADIT. Collects the stress of each strain and writes elastic_constants.csv; run with the Python that has ADIT installed\n")
        + "from pathlib import Path\nfrom adit.elastic_setup import collect\n\nprint(collect(Path(__file__).resolve().parent)['summary'])\n", encoding="utf-8", newline="\n")
    lines = [L(f"ADIT {__version__} が生成した、弾性定数のための歪みの計算です ({spec.method.code}、{'原子の緩和あり' if spec.task.type == 'geometry_optimization' else '原子を動かさない'})",
               f"Strain runs for elastic constants, generated by ADIT {__version__} ({spec.method.code}, {'relaxed ions' if spec.task.type == 'geometry_optimization' else 'clamped ions'})"), "",
             L(f"  成分 (Voigt の番号 1=xx 2=yy 3=zz 4=yz 5=xz 6=xy): {components}、歪みの大きさ: {strains} (4〜6 は工学歪み)、計算の数 {len(runs)} (歪みなしの e0 を含む)",
               f"  components (Voigt 1=xx 2=yy 3=zz 4=yz 5=xz 6=xy): {components}, strains: {strains} (4-6 engineering), {len(runs)} runs (with the unstrained e0)")]
    if len(set(meshes.values())) > 1:
        lines.append(L(f"  k 点の分割数が歪みで変わっています ({sorted(set(meshes.values()))}。密度の指定のため)。一覧は elastic.json の kpoints_mesh",
                       f"  the k-point mesh changes with strain ({sorted(set(meshes.values()))}; density setting); see kpoints_mesh in elastic.json"))
    lines += ["", L("== 実行したあと ==", "== After running =="),
              L(f"  python {COLLECT_SCRIPT}   (応力を集め、成分ごとに δ = 0 を含む点で直線を当てた傾き C_ij [GPa] を elastic_constants.csv に書きます)",
                f"  python {COLLECT_SCRIPT}   (collects the stress and writes the slopes C_ij [GPa] of straight-line fits including δ = 0 to elastic_constants.csv)"),
              L("  値の良し悪し (歪みの大きさが線形の範囲か) は ADIT は判断しません。当てはめの残差は elastic.json に書きます。", "  ADIT does not judge the values (whether the strains are in the linear range); fit residuals go to elastic.json.")]
    batch.write_top(out, cfg, spec, dirs, lines, "歪みの計算", "strain runs")
    return dirs


def collect(out_dir: Path | str) -> dict:
    from adit.outputs import OutputError, read_stress

    out = Path(out_dir).expanduser()
    rec = json.loads((out / ELASTIC_FILE).read_text(encoding="utf-8"))
    stress, bad = {}, []
    for r in rec["runs"]:
        try:
            s = read_stress(out / r["dir"])
            stress[r["dir"]] = [float(s[VOIGT[i]]) for i in range(1, 7)]
        except (OutputError, Exception) as ex:
            bad.append(f"{r['dir']}: {ex}")
    if bad:
        raise ElasticError(L(f"応力を読めない計算が {len(bad)} 個あります (全部が走り終わってから集めます):\n  ", f"{len(bad)} runs have no readable stress (collect after all have finished):\n  ") + "\n  ".join(bad[:10]))
    c = [[None] * 6 for _ in range(6)]
    fits = []
    for j in rec["components"]:
        pts = [(r["strain"], stress[r["dir"]]) for r in rec["runs"] if r["component"] in (0, j)]
        x = np.array([p[0] for p in pts])
        for i in range(1, 7):
            y = np.array([p[1][i - 1] for p in pts])
            slope, icpt = np.polyfit(x, y, 1)
            resid = y - (slope * x + icpt)
            c[i - 1][j - 1] = float(slope)
            fits.append({"i": i, "j": j, "c_gpa": float(slope), "intercept_gpa": float(icpt), "n_points": len(pts), "max_abs_residual_gpa": float(np.abs(resid).max())})
    rec.update(stress_voigt_gpa=stress, c_gpa=c, fits=fits)
    batch.write_json(out / ELASTIC_FILE, rec)
    with open(out / "elastic_constants.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["i\\j", *range(1, 7)])
        for i in range(6):
            w.writerow([i + 1, *["" if v is None else f"{v:.4f}" for v in c[i]]])
    with open(out / "elastic_stress.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["dir", "component", "strain", "s_xx_gpa", "s_yy_gpa", "s_zz_gpa", "s_yz_gpa", "s_xz_gpa", "s_xy_gpa"])
        for r in rec["runs"]:
            w.writerow([r["dir"], r["component"], r["strain"], *[f"{v:.6f}" for v in stress[r["dir"]]]])
    rows = ["  " + " ".join(f"{('-' if v is None else f'{v:9.2f}'):>9}" for v in c[i]) for i in range(6)]
    summary = "\n".join([L("弾性定数 C_ij [GPa] (行 i = 応力の成分、列 j = 歪みの成分。Voigt 1=xx 2=yy 3=zz 4=yz 5=xz 6=xy。対称化していません):",
                           "elastic constants C_ij [GPa] (row i = stress component, column j = strain component; Voigt 1=xx ... 6=xy; not symmetrized):"),
                         *rows, L(f"書いたもの: {out / 'elastic_constants.csv'}、{out / 'elastic_stress.csv'}、{out / ELASTIC_FILE}",
                                  f"wrote: {out / 'elastic_constants.csv'}, {out / 'elastic_stress.csv'}, {out / ELASTIC_FILE}")])
    return {"c_gpa": c, "fits": fits, "summary": summary}


if __name__ == "__main__":
    import sys
    print(collect(sys.argv[1])["summary"])


__all__ = ["ElasticError", "parse_values", "strain_matrix", "plan", "write_elastic", "collect", "VOIGT"]
