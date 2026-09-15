# examples/vasp_h2o の出典

VASP 公式 wiki の例「H2O」(水分子の構造緩和)を、POSCAR / INCAR / KPOINTS の 3 ファイルとして **原文のまま** 転載した。
POTCAR は含まない(ライセンス保持者以外に配布できない。docs/design_vasp_v1.md 2 節)。

| 項目 | 内容 |
|---|---|
| URL | https://www.vasp.at/wiki/index.php/H2O |
| ライセンス | GNU Free Documentation License 1.2(wiki の既定。各ページ下部に「Content is available under GNU Free Documentation License 1.2 unless otherwise noted」)。転載には出典と同ライセンスの表示が要る。この文書がそれに当たる |
| 取得日 | 2026-09-10 |
| 系 | 水分子 1 個。15 Å の立方体の箱。座標は 0.52918 倍のスケール(Bohr 単位で書いた座標を Å に直す係数) |
| 手法 | PAW-PBE(POTCAR による)、PREC = Normal、ENMAX = 400、ISMEAR = 0 / SIGMA = 0.1 |
| 構造最適化 | IBRION = 1(DIIS)、NFREE = 2、NSW = 10、EDIFFG = -0.02(全原子の力が 0.02 eV/Å 未満)。1 番目の原子(原点)は固定、残り 2 つは x, y のみ動く(Selective dynamics) |
| k 点 | Γ 点のみ(1×1×1) |

## POTCAR について(生成器が書く `potcar.spec` の参考)

この POSCAR は **元素名の行が無い旧形式** で、6 行目 `1 2` は「1 番目の種が 1 個、2 番目の種が 2 個」。
座標から 1 番目の種は原点に固定された O、2 番目の種は ±1.43 に置かれた H と読める。
したがって POTCAR は **O、H の順** に連結する。生成器は元素名の行を書く新形式(VASP 5 以降)を使う。
Materials Project の対応表(pymatgen v2023.10.11 `MPRelaxSet.yaml` の POTCAR 節、MIT)では H → `H`、O → `O`。

## 注意

- 軸固定の出典 (2026-09-12): https://vasp.at/wiki/POSCAR 。Selective dynamics の T/F は、座標を Cartesian で書いても格子ベクトル方向を表す。ADIT の Cartesian 軸固定は、許される変位が同じになる場合だけ格子方向へ変換する。セル形状を動かす ISIF (https://vasp.at/wiki/ISIF) では方向を保持できないため、部分的な Cartesian 軸固定を検査で止める。
  Axis-constraint source (2026-09-12): https://vasp.at/wiki/POSCAR . Selective dynamics T/F flags refer to lattice-vector directions even with Cartesian positions. ADIT converts Cartesian axis constraints only when the allowed displacements remain equivalent. Partial Cartesian constraints are rejected when ISIF allows the cell shape to change (https://vasp.at/wiki/ISIF), because the fixed directions cannot be retained.

- 原文は VASP 5 世代の記述(`PREC=Normal (Default for VASP.5.X)`、旧キー `ENMAX`)。6.x で通るかは人がクラスタで確かめる
- wiki の各キーワードの説明: https://www.vasp.at/wiki/index.php/ENMAX 、/PREC 、/ISMEAR 、/SIGMA 、/IBRION 、/NFREE 、/NSW 、/EDIFFG 、/POSCAR 、/KPOINTS(2026-09-10 に存在を確認)
