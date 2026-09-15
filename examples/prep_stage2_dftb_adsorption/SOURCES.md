# 比べる計算の組 (吸着) の実行 — DFTB+ 25.1、mio-1-1 (2026-09-12)

## 何の例か

グラフェン 2×2 (C 8 原子、真空 15 Å の箱、周期) の上 3 Å に水 1 分子を置いた吸着の組。
`adit-gen spec.json out/ --compare-set set.json` (`src/adit/compare_sets.py`) で生成し、各ディレクトリで DFTB+ を実行し、
`adit-analyze out/ --compare` (`src/adit/analysis/compare.py`) で集計したもの。

- 条件 (3 つとも同じ): DFTB+ 25.1、SK セット mio-1-1、SCC、一点計算、k 点 4×4×1 (周期のあるもの)
- 分子 (molecule) は `molecule_box` を既定の `as_is` のままにしたので非周期 (k 点なし)。この違いは止めずに `compare.json` の
  `differences` (structure.periodic) と `partial` (k 点の項目) に書かれる。これを確かめるための例
- 入力の構造は ASE の `graphene(size=(2, 2, 1), vacuum=7.5)` と `molecule("H2O")` (ASE 3.29.0) から作った

## ファイル

| ファイル | 中身 |
|---|---|
| `inputs/` | 生成に使った spec.json、set.json、構造 (slab.extxyz, h2o.xyz, adsorbed.extxyz) |
| `compare.json` | 組の定義 (reactions)、計算ごとの条件、条件の違い、組成の釣り合い |
| `slab/ molecule/ adsorbed/` | 各計算 (入力と DFTB+ の出力。skf は mio-1-1 から写したもの、CC BY-SA 4.0) |
| `compare_*.csv`、`compare_summary.json`、`compare_energy.png` | 解析 (adit-analyze --compare) の結果 |

## 結果 (数値を並べるだけ。比べてよいかは判断しない)

| 計算 | 原子数 | 全エネルギー [eV] |
|---|---|---|
| adsorbed | 11 | -488.6238 |
| slab | 8 | -377.7017 |
| molecule | 3 | -110.9604 |

ΔE = E(adsorbed) − E(slab) − E(molecule) = +0.0383 eV (+3.695 kJ/mol)。条件が違う項目 1 個 (structure.periodic)、
一部の計算にだけある項目 6 個 (k 点の項目など)。
