# チュートリアル

一度にたくさん作る、条件を振る、解析する、報告をまとめる、までの手順です。
基本の流れ (1 つ作って実行して解析する) は [README](../README.md) にあります。

## 一度にたくさん作る・条件を振る

```bash
adit-gen spec.json out/ --structures "mols/*.xyz"          # 同じ条件で構造だけ差し替えて一括生成
adit-gen spec.json out/ --scan method.ecutwfc=30,40,50     # 1 つの値を振る (収束の確認)
adit-gen spec.json out/ --scan method.ecutwfc=30,40 \
                         --scan kpoints.mesh=4x4x4,6x6x6    # 2 つ以上を同時に振る (すべての組み合わせ)
adit-gen spec.json out/ --scan "geom.dihedral(0,1,2,3)=0,30,60"   # 構造の幾何を振る (距離・角・二面角)
adit-analyze out/ --scan                                    # 値とエネルギーの表 (scan_energies.csv)
adit-report out/*/ --results-csv results.csv                # 結果を 1 枚の表に
```

`--structures` は 1 つのファイルに複数フレームがあれば、フレームごとに 1 つの計算にします。
幾何のスキャン (`geom.distance(i,j)` / `geom.angle(i,j,k)` / `geom.dihedral(i,j,k,l)`、原子の番号は 0 始まり) は
**振った幾何を固定しません**。構造を動かす計算では値が保たれないので、一点計算にするか原子を固定してください (生成時に注意が出ます)。

`--structures` generates one calculation per structure (per frame for multi-frame files) with every other setting unchanged.
Repeating `--scan` scans a grid of all combinations. Geometry scans (`geom.distance(i,j)`, `geom.angle(i,j,k)`,
`geom.dihedral(i,j,k,l)`; 0-based indices) do **not** constrain the scanned coordinate, so use a single-point task or fix
those atoms — ADIT says so when generating.

## サンプルと設定の確認

```bash
adit-gen --list-samples                        # 同梱のサンプル (examples/) の一覧
adit-gen --sample water_generated mine.json    # 1 つ写して、書き換えの出発点にする
adit-gen --check-config                        # 設定ファイル・プロファイル・知らない項目の確認
```


`--list-samples` lists the bundled `examples/` (source checkout only), `--sample` copies one `spec.json` as a starting
point, and `--check-config` prints the settings file, its profiles, and any entries ADIT does not know.

## 置換基を振る

```bash
adit-gen spec.json out/ --core "c1ccccc1[*:1]" --substituent "1=[H],C,OC,N(C)C"
```

骨格の `[*:1]` に置換基を差し込み、組み合わせごとにディレクトリを作ります (座標は RDKit の ETKDG + MMFF)。
**どの置換基を試すかは利用者が書きます** (ADIT は置換基の一覧を持ちません)。

Substituents are inserted into the `[*:1]`-style attachment points of the core, one directory per combination
(coordinates from RDKit ETKDG + MMFF). **You choose the substituents**; ADIT ships no library of groups.

## 粘度 (Green-Kubo)

```bash
adit-analyze run/ --viscosity      # 圧力テンソルの非対角成分から η = V/(k_B T)∫⟨P_ab(0)P_ab(t)⟩dt
```

LAMMPS では、生成のときに圧力テンソルを thermo に足す欄 (`thermo_pressure_tensor`) を有効にすると、
`pxy pxz pyz` を毎ステップ書きます。**積分が収束しているかは判定しません** (走る積分の図を見て判断してください)。

With LAMMPS, enable `thermo_pressure_tensor` when generating so that `pxy pxz pyz` are written every step.
`--viscosity` then evaluates the Green-Kubo integral; **convergence is not judged** — read it off the running-integral figure.

## 体積データと結晶

```bash
adit-analyze run/ --plane-average c --work-function   # LOCPOT・CHGCAR・*.cube の面平均と仕事関数
adit-convert crystal "225 Na:0,0,0 Cl:0.5,0,0 cell=5.64" nacl.cif   # 空間群から結晶を作る
```

面平均は軸に垂直な面で平均した分布を図と CSV にします。仕事関数は「面平均の最大値 (真空準位) − フェルミ準位」で、
**真空の領域が十分かどうかは判定しません** (図を見て確かめてください)。値が eV でないファイル (cube は書いたコード次第) では
仕事関数を出しません。3 次元の等値面は描かず、VMD・VESTA・OVITO に渡す形を保ちます。

`--plane-average` averages VASP `LOCPOT`/`CHGCAR` or `*.cube` data over planes normal to an axis (figure + CSV).
`--work-function` subtracts the Fermi level from the maximum of that profile; it does not judge whether the vacuum region is
adequate, and it refuses when the values are not in eV. `adit-convert crystal` builds a crystal from a space group and
fractional coordinates (the symmetry expansion is done by ASE).

## ほかの解析ツールから移ってくる人へ

MDAnalysis・MDTraj・pymatgen・VASPKIT・TRAVIS・VMD・OVITO・gmx・cpptraj との突き合わせと、

```bash
adit-analyze run/ --msd --select "element Na and z < 20"   # 原子の選び方 (MDAnalysis 風)
adit-analyze run/ --rmsd --rmsf                             # gmx rms / rmsf、cpptraj rms / atomicfluct
adit-analyze run/ --distance 1,2 --angle 2,1,3              # cpptraj distance / angle
adit-analyze run/ --vacf                                    # TRAVIS の VACF、gmx velacc
adit-analyze run/ --msd --conductivity 1                    # イオン伝導度 (Nernst-Einstein)
adit-analyze run/ --zdens --zdens-axis a                    # gmx density (軸を選べます)
```

**GROMACS の xtc・NAMD の dcd・Amber の NetCDF** は、MDAnalysis か MDTraj か chemfiles が入っていれば読みます
(`pip install MDAnalysis`)。入っていなければ「読めません」と言い、変換のしかたを出します
(黙って最終構造 1 枚で解析することはしません)。


## 重い解析は実行用のファイルにする

原子 1 個ごとの拡散係数や、変位の分布 (van Hove の自己相関) は、大きな軌跡では数十分かかります。
ADIT は**計算を投入しないのと同じ考え方で、重い解析も画面の中では回しません**。実行用のファイル一式
(`msd_worker.py` と `msd_run.sh`) を計算のディレクトリに置き、人が実行して `msd_vanhove.json` ができたら、
ADIT はそれを読んで図にします。手順と見積もりの式は [重い解析](HEAVY_ANALYSIS.md)。

```bash
adit-analyze run/ --msd --vanhove      # 見積もる。重ければ実行用のファイルを置く
bash run/msd_run.sh                     # 人が実行する (クラスタならジョブとして)
adit-analyze run/ --msd --vanhove      # できた JSON を読んで図にする
adit-analyze run/ --msd --msd-per-atom # 原子ごとの D (軽い系ならその場で)
```

`msd_worker.py` は numpy と scipy だけで動くので、ADIT が入っていないクラスタでも走ります。

Heavy analyses (per-atom diffusion, van Hove self-part) are generated as a runnable script instead of being
computed inside the GUI; see `docs/HEAVY_ANALYSIS.md`.

## 粉末 X 線回折と速度定数

```bash
adit-analyze run/ --xrd                        # 最終構造 (周期系) から粉末回折のパターン (既定 CuKa)
adit-analyze run/ --xrd --xrd-measured meas.xy # 実測 (1 列目 2θ、2 列目 強度) を重ねて描く
adit-analyze run/ --eyring 95.4                # ΔG‡ = 95.4 kJ/mol から Eyring の式で速度定数
```

回折の計算は pymatgen の `XRDCalculator` に任せ (`pip install pymatgen`)、ピークの位置・強度・面間隔・指数を
`analysis/xrd.csv` と図に出します。実測を重ねるときは**どちらも最大を 100 にそろえます**。
**一致・不一致は判定しません**し、熱振動 (デバイ・ワラー因子) と選択配向も入れていません。
速度定数は k = κ (k_B T / h) exp(−ΔG‡/RT) で、温度は `--eyring-temperature` (既定 298.15 K)、
透過係数は `--eyring-kappa` (既定 1、トンネル効果は入れない)。**どの差が ΔG‡ かは利用者が決めます。**

`--xrd` computes a powder pattern from the final periodic structure with pymatgen and can overlay a measured
pattern (both scaled to a maximum of 100); no agreement is assessed. `--eyring` turns an activation free energy
in kJ/mol into a rate constant; you decide which difference is the barrier.

## Python から部品として使う

主な関数の一覧と例外の表は `docs/API.md` にあります。解析の書き出し先は `adit-analyze -o DIR`
(Python では `AnalysisOptions(out_dir=…)`) で変えられるので、**計算のディレクトリを汚さずに**回せます。
すべての例外は `adit.errors.AditError` を継承します (`handoff.py` だけは計算機の上で単体で動かすため別)。

See `docs/API.md` for the Python entry points and the exception table.

## 計算条件の報告と再現パッケージ (`adit-report`)

生成した計算ディレクトリから、**論文や報告書の「方法」の節**、**条件の表 (CSV)**、**引用の一覧**、
**再現に要るファイル一式**を書き出せます。**書くのは記録に残っている事実だけ**で、記録が無いものは「未記録」と書きます。

```bash
adit-report run1 run2 -o methods.md --lang both   # 方法の節 (日英)・条件・解析の要約・引用・指紋
adit-report run1 run2 --csv conditions.csv        # 条件を 1 枚の表に
adit-report run1 --bundle pack.zip                # 入力一式 + manifest.json (指紋つき)
adit-report run1 --check                          # 入力が生成後に書き換えられていないか
```

生成時に入力ファイルの SHA-256 を `spec.json` に残しているので、`--check` で「この結果を出した入力は記録どおりか」を
後から確かめられます。詳しくは [報告と再現パッケージ](REPORT.md)。

From a generated directory, ADIT can write **a methods section** for a paper, **a settings table (CSV)**, **a citation
list**, and **a package with everything needed to reproduce the run**. It writes **only what is on record** and marks
anything else as not recorded. Because the SHA-256 of every input file is stored in `spec.json` at generation time,
`--check` can later confirm that the inputs still match the record. See [Reporting and reproducibility packages](REPORT.md).

OpenMM・Psi4・ABINIT・PLUMED の対応範囲と、NWChem の分子一点計算は [追加した計算コード](NEW_ENGINES.md)にあります。いずれも CLI (`adit-gen` / `adit-analyze`) からで、GUI とウェブ版に操作欄はまだありません。

| 追加した接続 | できること | 実走で確かめた例 |
|---|---|---|
| OpenMM | 利用者の GROMACS / Amber トポロジーで一点計算・最小化・MD (NVE/NVT/NPT) | `examples/openmm_spce_nvt_generated` |
| Psi4 | 分子の一点計算・構造最適化・振動解析 (手法と基底は利用者が指定) | `examples/psi4_h2o_generated` |
| ABINIT | 3 次元周期系の SCF 一点計算と構造最適化 (擬ポテンシャルは利用者のもの) | `examples/abinit_si_generated` |
| PLUMED | 利用者が書いた集合変数・バイアスを LAMMPS・GROMACS・OpenMM の MD につなぐ | `examples/plumed_lammps_cu_generated` |

どれも**力場・擬ポテンシャル・基底関数・集合変数を ADIT が作ることはありません**。

See [Additional calculation engines](NEW_ENGINES.md) for the OpenMM, Psi4, ABINIT and PLUMED scopes and for NWChem molecular single points. All of them are CLI-only (`adit-gen` / `adit-analyze`); no GUI or web controls have been added. OpenMM consumes your GROMACS or Amber topology (single point, minimization, MD); Psi4 covers molecular single points, optimizations and frequencies; ABINIT covers single-point SCF and geometry optimization for fully periodic systems; PLUMED attaches your own collective variables and bias to LAMMPS, GROMACS or OpenMM MD. **ADIT never builds force fields, pseudopotentials, basis sets or collective variables.** The verified runs are the example directories listed above.

Gaussian・US GAMESS・Q-Chem・GRRM17・OpenMX・Amber・NAMD の CLI 入力生成は [追加した計算コード](NEW_ENGINES.md) に、対応する計算種類・必要な外部ファイル・未対応の解析を日英で記載しています。Materials Studio・Schrödinger Suite・Winmostar との連携は保留です。

For the CLI input generators for Gaussian, US GAMESS, Q-Chem, GRRM17, OpenMX, Amber, and NAMD, see [Additional calculation engines](NEW_ENGINES.md) for the supported tasks, required external files, and analysis limits. Integration with Materials Studio, Schrödinger Suite, and Winmostar is deferred.

`combine` は単一フレームの通常の XYZ を 2 つ以上、指定順に連結します。拡張 XYZ のセル・制約などは保持できないため、入力にその情報があれば停止します。座標は動かさず、結合・分子間距離・周期セルを決めず、原子の重なりも検査しません。出力が既にある場合や、入力と同じファイルを出力先にした場合は停止します。画面にはまだこの操作を追加していません。

`combine` concatenates two or more single-frame plain XYZ files in the given order. It rejects extended XYZ metadata, such as a cell or constraints, because it cannot preserve them. It does not move coordinates, determine bonds, intermolecular distances, or a periodic cell, or check for overlapping atoms. It refuses an existing output or an output that is also an input. This operation is currently CLI-only.

出力名が `.data` または `.lammps` で終わる場合は、LAMMPS data 形式で書きます (`.gz` などの圧縮拡張子にも対応)。
元素ごとの質量と、入力にあれば速度を含む `atom_style atomic` 用の構造を書き出します。ASE の既定の `metal` 単位系 (長さ Å、速度 Å/ps)を使います。力場、結合トポロジー、電荷は生成しません。
形式を明示するには `--input-format lammps-data` / `--output-format lammps-data` を使います。
同じ `.data` 拡張子を使う RuNNer 形式への出力は `--output-format runnerdata` と指定してください。
入力は内容から判定できる形式を優先するため、既存の RuNNer ファイルや LAMMPS dump も読み込めます。

For output filenames ending in `.data` or `.lammps`, ADIT writes LAMMPS data for `atom_style atomic`, including elemental masses and velocities when present, using ASE's default `metal` units (Å and Å/ps).
Compressed filenames such as `.data.gz` are also supported. This exports the structure; it does not generate a force field, bond topology, or charges.
Use `--input-format lammps-data` or `--output-format lammps-data` to specify the format explicitly.
For RuNNer output, which also uses `.data`, specify `--output-format runnerdata`.
Input detection checks the file contents first, so existing RuNNer files and LAMMPS dumps remain readable.

構造形式ごとに保持できる情報は異なります。CIF と LAMMPS data への出力では固定原子・軸固定を保存できないため、入力に制約があれば CLI にその事実を表示します。CIF では初速度も保存しません。これらの保持には `.extxyz` を使ってください。通常の XYZ (`--output-format xyz`)、GEN、PDB でも制約と速度の脱落を表示します。LAMMPS data は周期境界の指定を持たないため、計算入力で別途指定が必要です。
Quantum ESPRESSO の入力は構造だけでは作れません。擬ポテンシャルと計算条件を設定した `spec.json` を `adit-gen` へ渡すか、雛形を用いて `adit-convert calculation` を使ってください。

Formats retain different data. CIF and LAMMPS data exports do not retain fixed-atom or fixed-axis constraints; the CLI reports this when constraints are present. CIF also omits initial velocities. Use `.extxyz` to preserve these data. Plain XYZ (`--output-format xyz`), GEN, and PDB exports also report omitted constraints and velocities. LAMMPS data does not encode periodic boundary settings; specify them separately in the calculation input.
Quantum ESPRESSO input needs pseudopotentials and calculation settings in addition to a structure. Use `adit-gen` with a configured `spec.json`, or `adit-convert calculation` with a target template.

XYZ のようにセルを持たない形式からPOSCARを作る場合、ADITはセルの大きさを決めません。長さをÅ単位で明示します。

```bash
adit-convert structure molecule.xyz POSCAR --cell 20          # 20 × 20 × 20 Å
adit-convert structure molecule.xyz POSCAR --cell 20,20,30    # a、b、cを別々に指定
```

既存の VASP・QE・LAMMPS・GROMACS の入力を点検するには、`adit-convert import 入力ディレクトリ 点検先` を使います。元の行番号と SHA-256、読み取れなかった条件、元の入力には無い既定値を `import_report.json` に記録します。安全に読み取れた場合だけ `draft_spec.json` を作ります。これは確認用の下書きで、元入力を完全に再現するものではありません。対応する入力形式と制限は[既存入力の読み込み](NATIVE_IMPORT.md)にあります。

To inspect existing VASP, QE, LAMMPS, or GROMACS input, run `adit-convert import INPUT_DIR REVIEW_DIR`. The `import_report.json` records source lines, SHA-256 hashes, unread settings, and spec defaults absent from the input. A `draft_spec.json` is written only when the supported subset is read without unresolved fields. It is a review draft, not a promise to reproduce the original input. See [native input import](NATIVE_IMPORT.md) for the supported subset and limits.

生成した入力と `spec.json` の対応項目は `adit-convert verify 生成ディレクトリ` で読み戻し照合できます。入力は変更しません。詳細を残す場合は `--report 新しいファイル.json` を指定してください。通過しても計算全体の同等性や実行可能性は保証しません。対応範囲は[生成入力の照合](NATIVE_VERIFY.md)を参照してください。

To re-import and check mapped settings in a generated bundle against `spec.json`, run `adit-convert verify GENERATED_DIR`. It does not modify the input. Add `--report NEW_FILE.json` to save details. Passing this limited check does not establish whole-calculation equivalence or executability; see [generated-input verification](NATIVE_VERIFY.md).

デスクトップ版では「ファイル」→「変換と点検」→「入力と結果の点検」から、既存入力の読み込み・生成入力の照合・2 計算の横断点検を行えます。ウェブ版は「変換」ページに読み込みと照合、「解析」ページに横断点検があります。どちらも CLI と同じ限定的な読み込み・点検処理を使います。既存入力の読み込みだけは、新しい点検先に報告書と、読めた場合の下書きを書きます。照合と横断点検は読み取り専用です。

In the desktop app, open File → Convert and inspect → Inspect inputs/results for native import, generated-input verification, and a two-run audit. In the web app, import and verification are on Convert; the cross-run audit is on Analysis. Both use the same limited checks as the CLI. Import writes a report and, when parsing succeeds, a draft in a new review directory. Verification and cross-run auditing are read-only.

下書きから別コードの入力を作るときは、`import_report.json` にある既定値と外部パラメータを確認してから、`adit-convert calculation 点検先/draft_spec.json 変換先の雛形 出力先 --accept-import-defaults` と明示します。LAMMPS の外部 data を使う下書きは、この指定を付けてもコード間変換できません。

To retarget a draft, review the defaults and external parameters in `import_report.json`, then explicitly use `adit-convert calculation REVIEW_DIR/draft_spec.json TARGET_TEMPLATE OUTPUT_DIR --accept-import-defaults`. This option does not bypass the cross-code safety stop for a LAMMPS draft backed by external data.

計算コードを替えるときは、変換先コードの設定を研究室の雛形として先に保存します。次の例では、ADITが生成した、外部dataファイルを使わないLAMMPSの`spec.json`から構造、固定原子、速度、計算の種類、MDのアンサンブル・温度・時間刻み・ステップ数・出力間隔を保ち、VASP固有の設定とk点は`vasp-md`の雛形から取ります。外部dataを使うLAMMPSや、外部トポロジーを使うGROMACS・Amber・NAMDからのコード間変換は、実際の原子順・電荷・結合をSpecだけで確認できないため停止します。

To switch engines, first save the target settings as a lab template. In the example below, the source is a ADIT-generated LAMMPS `spec.json` that does not use an external data file. Shared structure and MD settings stay in the spec; VASP-specific settings and k-points come from `vasp-md`. Cross-code retargeting stops for LAMMPS runs using external data and for GROMACS, Amber, or NAMD source runs using external topologies, because the spec alone cannot verify their actual atom order, charges, or bonds.

```bash
adit-gen vasp_reference.json --save-template vasp-md
adit-convert calculation lammps_run/spec.json vasp-md vasp_check/
```

力場とDFTの手法、カットオフ、擬ポテンシャルなど、コード間で同じ意味にならない設定は変換しません。生成前の機械的検査で、変換先が扱えないアンサンブルや不足している必須条件があれば停止します。何を保持し、何を変換先の雛形から取ったかは、生成先の`conversion.json`と`README.txt`に残ります。

熱浴も既定では変換元の種類を保持します。たとえば LAMMPS の `nose_hoover` を、その熱浴に対応しない QE の生成器へ渡すと停止します。
熱浴を変更する場合は、変換先の雛形に `task.md.thermostat` を明示し、`--use-target-thermostat` を付けます。
この指定は NVT/NPT の MD だけに使えます。アンサンブル、温度、時間刻み、ステップ数、出力間隔、熱浴・圧力浴の時定数、圧力は変換元の値を保持します。
初速度も既定では保持し、書き出せないコードでは停止します。初速度を引き継がないと決めた場合だけ、`--no-velocities` を付けてください。

The source thermostat and initial velocities are preserved by default. If the target generator cannot use them, generation stops.
To change the thermostat for NVT/NPT MD, explicitly set `task.md.thermostat` in the target template and pass `--use-target-thermostat`.
The source ensemble, temperature, timestep, step count, output interval, thermostat and barostat coupling times, and pressure remain unchanged.
Pass `--no-velocities` only when you intend to omit the source velocities.

QE の MD では、軌跡の出力間隔 `task.md.dump_interval` を `pw.in` の `&CONTROL` の `iprint` に書き出します。
For QE MD, `task.md.dump_interval` sets `iprint` in the `&CONTROL` namelist of `pw.in`.
See the [official QE input reference](https://www.quantum-espresso.org/Doc/INPUT_PW.html).

VASP の MD では、同じ出力間隔を `INCAR` の `NBLOCK` に書き、XDATCAR の座標出力間隔を設定します。
VASP MD writes the same interval to `NBLOCK` in `INCAR` to set the coordinate output interval in XDATCAR.
See the [VASP NBLOCK reference](https://vasp.at/wiki/NBLOCK).

VASP へ変換する場合、Nosé–Hoover の `coupling_time_fs` と NPT の `barostat_time_fs` は `spec.json` に残りますが、VASP 入力には換算しません。
Nosé–Hoover の `SMASS`、NPT の `PMASS` と `LANGEVIN_GAMMA_L` は変換先の雛形の `method.extra_incar` から取ります。
入力に適用されない項目と値は `conversion.json` の `not_applied_by_target` と生成物の README に記録します。
When converting to VASP, the Nosé–Hoover `coupling_time_fs` and NPT `barostat_time_fs` remain in `spec.json` but are not converted into VASP input parameters.
Nosé–Hoover `SMASS`, and NPT `PMASS` and `LANGEVIN_GAMMA_L`, come from `method.extra_incar` in the target template.
Unapplied settings and their values are recorded in `not_applied_by_target` in `conversion.json` and in the generated README.

```bash

# qe-md の task.md.thermostat は、利用者が選んだ QE 対応の熱浴を明示しておく

# Explicitly set a user-chosen QE-compatible thermostat in qe-md first.
adit-convert calculation lammps_run/spec.json qe-md qe_check/ --use-target-thermostat --no-velocities
```

熱浴の変更前後の値と初速度を除外した事実は、`conversion.json` と `README.txt` に残ります。
熱浴を変えたり初速度を除外したりした計算は、元の計算とまったく同じ運動方程式・初速度の比較にはなりません。
The report and README record the old and new thermostat and any omission of initial velocities.
Changing the thermostat or omitting velocities means the runs no longer use identical equations of motion or initial velocities.

初回起動時に環境設定ファイル (`~/.config/adit/cluster.toml`、Windows では `%APPDATA%\adit\cluster.toml`) の雛形が作られます。
雛形にはローカル実行用のプロファイル `local` だけが入っています。`sk_root` (Slater-Koster パラメータの置き場所) などをお使いの環境に合わせてください。
環境設定はアプリの「設定」メニューからも編集できます。

### OS ごとの違い

- **Linux / macOS**: すべての機能が使えます。「この PC で実行」は、計算コードの実行ファイルが PATH にあるときだけ押せます。
- **Windows (WSL なし)**: 構造の作成、入力ファイルの生成、解析まで使えます。計算コードを Windows で動かすことは想定していないため、「この PC で実行」は無効になります。生成したファイルは改行コード LF で書かれるので、そのまま Linux のサーバーへ転送して使えます。
- **WSL (WSLg)**: Wayland では選択肢を選んでも一覧が閉じない Qt の不具合があるため、ADIT は X11 (xcb) を既定で使います。`QT_QPA_PLATFORM` を設定している場合はそちらが優先されます。

## 図の見た目を変える

線の色、目盛りの向き、目盛り線、枠を指定できます。**数値は変わりません。**

```bash
adit-analyze run/ --plot-colors black,#d62728 --plot-ticks in --plot-grid none --plot-spines left-bottom
adit-analyze run/ --plot-line-width 1.6 --plot-font-size 9 --plot-dpi 300   # 論文に貼るとき
```

| 指定 | 選べる値 |
|---|---|
| `--plot-colors` | 色をカンマ区切りで (`black`、`#1f77b4`、`tab:red` など) |
| `--plot-ticks` | `in` (内向き) / `out` (外向き) / `inout` |
| `--plot-grid` | `both` / `x` / `y` / `none` |
| `--plot-spines` | `all` (四方) / `left-bottom` (左と下) / `none` |
| `--plot-line-width` `--plot-font-size` `--plot-dpi` | 数値 |

画面では「詳しい条件」→「図の見た目」にあります。

## 論文やスライドに貼る

Word・PowerPoint・LaTeX に貼れる形で書き出せます。**SVG は拡大しても粗くなりません**
(Word は Office 2016 以降が SVG をそのまま貼れます)。

### 解析の図

```bash
adit-analyze run/ --figure-format svg,pdf        # PNG に加えて SVG と PDF も出す
adit-analyze run/ --plot-dpi 300                 # PNG の解像度を上げる
```

画面からも保存できます。

- アプリ: 図ごとに「画像をコピー」「画像を保存…」。SVG や PDF が一緒に書かれていれば、保存のときに選べます
- ブラウザ: 図の下の「PNG で保存」「SVG で保存」「PDF で保存」

ベクタ形式を出すには、画面の「詳しい条件」→「図の追加の形式」に `svg,pdf` と入れてから解析します。

### 構造式 (Draw)

- アプリ: Draw の画面の「画像をコピー」「画像を保存…」
  (保存は SVG / PNG / **MOL** から選べます。MOL は ChemDraw などで開けます)
- ブラウザ: Draw の画面の「SVG で保存」「MOL で保存」

### 3D 表示

- アプリ: 構造のタブの「画像をコピー」「画像を保存…」
- ブラウザ: 「構造 (3D)」の「SVG で保存」

**コピー**はクリップボードに画像を入れます。Word で `Ctrl+V` するとそのまま貼れます。
