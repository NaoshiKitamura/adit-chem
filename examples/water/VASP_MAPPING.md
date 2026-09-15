# dftb_in.hsd と VASP 入力の対応

VASP は INCAR / POSCAR / POTCAR / KPOINTS の 4 ファイルに役割を分けますが、
DFTB+ は `dftb_in.hsd` 1 ファイルの中のブロックで同じ役割を分けます。
下の対応は「役割」の対応であり、キーワードが 1 対 1 で置き換わるわけではありません。

## ファイル・ブロック単位の対応

| VASP | DFTB+ | 補足 |
|---|---|---|
| POSCAR | `Geometry = GenFormat { <<< "geometry.gen" }` | gen 形式。1 行目「原子数 C/S/F」、2 行目 元素一覧、以下「通し番号 元素番号 x y z」(Å)。`C` はクラスタ (非周期) なので格子ベクトル行が無い。周期系は `S` にして末尾に原点 1 行 + 格子ベクトル 3 行を足す |
| POTCAR | `Hamiltonian = DFTB { SlaterKosterFiles {...} }` | 最大の違い: **元素ごとではなく元素ペアごと** (O-O, O-H, H-O, H-H)。同じセットの中でしか組み合わせられない。ファイル自体は `~/slakos/` 等に置き、入力からはパスで参照する (POTCAR を連結して置く操作に相当するものは無い) |
| POTCAR の価電子設定 (どの軌道を持つか) | `MaxAngularMomentum { O = "p"; H = "s" }` | skf ファイル形式が「どの軌道までか」を持たないため手で指定する。値はセットの文書 (skf 末尾) で決まる。GUI が自動で埋める対象 (設計書 2.5 節) |
| INCAR の手法設定 | `Hamiltonian = DFTB { Scc = Yes ... }` | 下の表を参照 |
| INCAR の構造最適化設定 (IBRION, NSW, EDIFFG, ISIF) | `Driver = GeometryOptimization {...}` | 下の表を参照 |
| KPOINTS | `Hamiltonian = DFTB { KPointsAndWeights {...} }` | 分子系 (クラスタ) では不要なので今回の入力には無い。周期系では必須 (v1 以降) |
| INCAR の出力制御 (LWAVE, LCHARG, NWRITE 等) | `Options {}` と `Analysis {}` | `Options` はファイル出力の可否 (detailed.out, results.tag, charges.bin 等)、`Analysis` は追加で計算・出力する量 (力の全成分、DOS、静電ポテンシャル等) |
| (対応なし) | `ParserOptions { ParserVersion = 12 }` | 入力の文法版を宣言する。VASP に相当物は無い。新しい DFTB+ は古い版の入力を自動変換する |

## INCAR のキーワードとの対応 (電子状態)

| INCAR | DFTB+ (`Hamiltonian = DFTB {}` 内) | 補足 |
|---|---|---|
| (SCF は常に自己無撞着) | `Scc = Yes` | DFTB では自己無撞着電荷 (SCC) を切ることもできる (`No` = 非 SCC DFTB)。通常は `Yes` |
| EDIFF (エネルギー基準) | `SccTolerance` (既定 1e-5) | 単位が違う。DFTB+ は**電荷**の差 (電子数) で判定する。エネルギー差ではない |
| NELM | `MaxSccIterations` (既定 100) | 同じ意味。超えると警告付きでそこまでの電荷でエネルギーを出して止まる |
| NELECT / 全体電荷 | `Charge` (既定 0.0) | 符号は「系の正味電荷」。VASP の NELECT (電子数) とは表現が逆 |
| ISPIN=2 / MAGMOM | `SpinPolarisation = Colinear { UnpairedElectrons = ... }` | 今回は未使用。既定はスピン分極なし |
| ISMEAR / SIGMA | `Filling = Fermi { Temperature [K] = ... }` | 既定は Fermi 分布、温度ほぼ 0 (0.1e-7 Hartree)。分子系では通常触らない |
| AMIX / BMIX / IMIX | `Mixer = Broyden { MixingParameter = 0.2 }` | 既定は Broyden 混合、混合率 0.2 |
| IVDW | `Dispersion = ...` | 今回は未使用。`DftD3`、`LennardJones` 等 |
| (対応なし。DFTB3) | `ThirdOrderFull = Yes` + `HubbardDerivs {...}` | 今回は未使用。DFTB3 は 3ob セットなど対応セットと組で使う |

## INCAR のキーワードとの対応 (構造最適化)

| INCAR | DFTB+ (`Driver = GeometryOptimization {}` 内) | 補足 |
|---|---|---|
| IBRION=1/2/3 (アルゴリズム) | `Optimizer = Rational {}` | 選択肢は Rational / LBFGS / FIRE / SteepestDescent (25.1 マニュアル 2.3.1)。`Optimiser` と `Optimizer` の両綴りが通る |
| NSW | `MaxSteps = 100` | 同じ意味。既定は 200 |
| EDIFFG (負値: 力の基準) | `Convergence { GradElem = 1E-4 }` | 力の**最大成分**が 1e-4 Hartree/Bohr (約 5.14e-3 eV/Å) 未満で収束。`GradElem [eV/AA] = 5.14e-3` と単位付きで書ける。エネルギー基準にしたいなら `Energy`、力のノルムなら `GradNorm` |
| EDIFFG (正値: エネルギー基準) | `Convergence { Energy = ... }` | 既定では無効 (inf) |
| ISIF (格子を動かすか) | `LatticeOpt = Yes/No` | 分子系では無関係。周期系で使う |
| 選択的ダイナミクス (POSCAR の T/F 列) | `MovedAtoms = 1:-1` | 動かす原子を入力側で指定する。`1:-1` は全原子。`O H` のように元素で選ぶことも可能 |
| CONTCAR | `OutputPrefix = "geom.out"` → `geom.out.gen`, `geom.out.xyz` | 最終構造の出力先。名前を自分で決める |
| ISTART / ICHARG (再開) | `charges.bin` (自動出力) + `ReadInitialCharges = Yes` | SCC の電荷が `charges.bin` に保存される (WAVECAR/CHGCAR に近い) |
| (一点計算) | `Driver {}` または `Driver` ブロック省略 | IBRION=-1, NSW=0 に相当 |

## 出力ファイルの対応

| VASP | DFTB+ | 補足 |
|---|---|---|
| OUTCAR / 標準出力 | 標準出力 (`dftb+ \| tee output`) | 各構造ステップの SCC 反復、全エネルギー、力の最大成分 |
| OSZICAR | 標準出力の `iSCC ...` 行 | SCC 反復ごとの電子エネルギーと電荷誤差 |
| OUTCAR の最終結果 | `detailed.out` | 最終ステップのエネルギー分解、Mulliken 電荷、力 (`CalculateForces`/`PrintForces` 有効時) |
| EIGENVAL | `band.out` | 固有値と占有数 |
| CONTCAR | `geom.out.gen` / `geom.out.xyz` | 上記 |
| CHGCAR (再開用途) | `charges.bin` | 電荷の再開情報 |
| (対応なし) | `dftb_pin.hsd` | 既定値をすべて展開した入力。**「自分が何を省略したか」を確かめる一番確かな方法** |
| vasprun.xml に近い | `results.tag` (`Options { WriteResultsTag = Yes }` 時) | 機械可読な結果。ASE などが読む |

## 単位について

数値の既定単位は原子単位 (エネルギー Hartree、長さ Bohr、力 Hartree/Bohr) で、
VASP の eV / Å とは異なります。gen 形式の座標だけは Å です。
角括弧で単位を付ければ換算不要で書けます (例 `GradElem [eV/AA] = 5.14e-3`)。

出典: 上記の対応は DFTB+ 25.1 マニュアル (2.2〜2.6, 2.10, 付録 D) と
公式レシピ「First calculation with DFTB+」に基づく。VASP 側のキーワードは
利用者の既知事項として記述した。
