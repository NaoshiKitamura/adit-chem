# examples/vasp_cd_si の出典

VASP 公式 wiki の例「Cd Si relaxation」(ダイヤモンド構造 Si の内部座標の緩和)を、POSCAR / INCAR / KPOINTS の
3 ファイルとして **原文のまま** 転載した。POTCAR は含まない。

| 項目 | 内容 |
|---|---|
| URL | https://www.vasp.at/wiki/index.php/Cd_Si_relaxation |
| ライセンス | GNU Free Documentation License 1.2(wiki の既定)。転載には出典と同ライセンスの表示が要る。この文書がそれに当たる |
| 取得日 | 2026-09-10 |
| 系 | ダイヤモンド構造 Si、2 原子。格子定数 5.5 Å の fcc 格子(分数座標)。片方の原子の z を 0.125 → 0.130 にずらして対称性を崩してある |
| 手法 | ENCUT = 240、ISMEAR = 0 / SIGMA = 0.1、ISTART = 0 / ICHARG = 2 |
| 構造最適化 | IBRION = 2(共役勾配)、NSW = 10、ISIF = 2(内部座標のみ。格子は固定)、EDIFFG = -0.0001 |
| k 点 | 11×11×11 Monkhorst-Pack(奇数なので Γ 中心) |
| 原文が示す結果 | 10 ステップ後の力が 1e-3 eV/Å 以下、total drift 0 |

## POTCAR について

元素名の行が無い旧形式(6 行目 `2`)。Materials Project の対応表(pymatgen v2023.10.11 `MPRelaxSet.yaml`、MIT)では Si → `Si`。
PAW PBE の配布物での識別行は `PAW_PBE Si 05Jan2001`。

## 注意

- 原文は VASP 5 世代の記述。6.x で通るかは人がクラスタで確かめる
- wiki の各キーワードの説明: https://www.vasp.at/wiki/index.php/ENCUT 、/ISMEAR 、/SIGMA 、/ISTART 、/ICHARG 、/NSW 、/IBRION 、/ISIF 、/EDIFFG 、/POSCAR 、/KPOINTS 、/INCAR(2026-09-10 に存在を確認)
