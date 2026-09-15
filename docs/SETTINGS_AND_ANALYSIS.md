# 設定と解析

環境設定ファイル (`cluster.toml`)、計算コードごとに用意するもの、解析の詳細です。

## 環境設定 (cluster.toml)

```toml
sk_root = "/home/<ユーザー名>/slakos"   # Slater-Koster パラメータの置き場所 (直下に mio-1-1/ など)
pseudo_root = "/home/<ユーザー名>/pseudo" # Quantum ESPRESSO の擬ポテンシャル (直下に <セット名>/*.UPF)
cp2k_data = ""                       # CP2K の data ディレクトリ (BASIS_MOLOPT など)。空なら CP2K_DATA_DIR、cp2k の隣の share/cp2k/data の順に探します
default_profile = "local"
enable_run = true                    # false にすると「この PC で実行」を表示しません
language = "ja"                      # "ja" または "en" (環境変数 ADIT_LANG が優先)
theme = "auto"                       # "auto" / "light" / "dark" (環境変数 ADIT_THEME が優先)

[profiles.local]
kind = "direct"
description = "この PC で bash submit.sh を実行"
```

### クラスタで実行する場合

環境設定ファイルに `kind = "pbs"` または `kind = "slurm"` のプロファイルを追加すると、`submit.sh` にそのスケジューラのヘッダが付きます。
テンプレートが書くのは汎用の項目 (ジョブ名、ノード数、コア数、MPI プロセス数、OpenMP スレッド数、制限時間) だけで、
サイト固有の値はすべて環境設定から埋めます (既定は空)。
下の例の `<...>` はそのままでは動かないので、クラスタの管理者か研究室の先輩に確かめて置き換えてください。置き換え忘れがあると、生成の前の検証で「仮の値のままです」と表示されます。
使わない行は、行頭に `#` を付けて無効にしたままにします。

```toml
[profiles.remote]
kind = "pbs"                        # または "slurm"
description = "所属のクラスタ"
select_extra = ""                   # PBS の select 行の末尾に付ける文字列 (サイトが要求する場合。例 ":jobtype=core")
header_extra = ["#PBS -q <キュー名>"]  # ヘッダに追加する行 (queue / partition / account など。Slurm なら "#SBATCH --partition=<パーティション名>")
submit_command = "qsub"             # 投入コマンド名 (README.txt に書くだけで、ADIT は実行しません)
status_command = "qstat -u $USER"   # 状態確認のコマンド (同上)

[profiles.remote.code_modules]   # 計算コードごとに module load するもの (クラスタで module avail と打つと一覧が出ます)
dftbplus = ["<DFTB+ の module 名>"]

# vasp = ["<MPI の module 名>", "<数値計算ライブラリの module 名>"]

# [profiles.remote.env]          # submit.sh の先頭で export する環境変数 (VASP を使うときだけ。# を外して使います)

# VASP_PP_PATH = "<POTCAR ライブラリの親ディレクトリ>"

[profiles.remote.commands]       # 計算コードごとの実行コマンド。{mpiprocs} {omp_threads} {binary} が埋められます
dftbplus = "dftb+"

# vasp = "mpirun -np {mpiprocs} <VASP の bin>/vasp_{binary}"

# orca = "<ORCA を展開したディレクトリ>/orca"   # ORCA は絶対パスで呼び、mpirun は付けません
```

生成したあとの手順は次の 3 つです。

```bash
scp -r <生成したディレクトリ> <クラスタ>:<作業ディレクトリ>/        # 1. 転送
ssh <クラスタ> 'cd <作業ディレクトリ>/<名前> && qsub submit.sh'     # 2. 投入 (Slurm なら sbatch)
ssh <クラスタ> 'qstat -u $USER'                                      # 3. 状態確認 (Slurm なら squeue)
```

`#!/bin/sh` で `module` コマンドが定義されていない環境があるため、`submit.sh` は `module` を使う前に `/etc/profile` を読み、それでも見つからなければ理由を表示して止まります。

## 各計算コードで用意するもの

| 計算コード | 本体 | パラメータ |
|---|---|---|
| DFTB+ | conda-forge の `dftbplus` など。`dftb+` を PATH に | Slater-Koster パラメータを https://dftb.org/parameters/download.html から取得し、`sk_root` の下に置きます (CC BY-SA 4.0、論文で引用が必要)。必要な元素ペアの skf ファイルと LICENSE / README が出力ディレクトリの `skf/` にコピーされます |
| VASP | ライセンスを持つ利用者が用意します。実行パスを `commands.vasp` に | POTCAR ライブラリを `potpaw_PBE/<名前>/POTCAR` の階層で置き、親ディレクトリを `env.VASP_PP_PATH` に。**POTCAR 自体は出力に含めません** (`potcar.spec` と `make_potcar.sh` を書き、実行時に連結します) |
| xtb | conda-forge の `xtb` を PATH に (LGPL-3.0) | 不要 (計算手法に内蔵) |
| Quantum ESPRESSO | conda-forge の `qe` などで `pw.x` を PATH に | UPF ファイルを `pseudo_root/<セット名>/` に置きます (pslibrary、SSSP https://www.materialscloud.org/discover/sssp など。ライセンスは配布元で確認してください)。必要な元素の UPF と付属文書が `pseudo/` にコピーされます |
| ORCA | 登録して入手し、実行パスを `commands.orca` に (再配布不可) | 不要 |
| CP2K | conda-forge の `cp2k` などで `cp2k.psmp` を PATH に (GPL-2.0-or-later) | CP2K に付いている data ディレクトリ (BASIS_MOLOPT、GTH_POTENTIALS など)。場所は環境設定の `cp2k_data` に書きます (空なら環境変数 `CP2K_DATA_DIR`、PATH にある cp2k の隣の `share/cp2k/data` の順に探します)。使う項目だけが `BASIS_adit` / `POTENTIAL_adit` に写されます |
| LAMMPS | conda-forge の `lammps` などで `lmp` を PATH に (GPL-2.0) | 力場のファイル (EAM、ReaxFF の ffield、機械学習ポテンシャルのモデル) か、外部で作った data ファイル。ADIT は力場の係数を決めません |
| GROMACS | conda-forge の `gromacs` などで `gmx` を PATH に (LGPL-2.1) | 外部で作ったトポロジー (.top / .itp) と構造 (.gro / .pdb)。CHARMM-GUI、acpype、pdb2gmx などで作ります |
| 機械学習ポテンシャル (MACE・CHGNet) | 生成物の `run_mlip.py` を実行する環境に `pip install ase mace-torch` (または `chgnet`)。PyTorch が入るので数 GB になります。**ADIT 自身は使いません** | 学習済みモデル。空欄ならパッケージの既定のモデル (初回に自動でダウンロードされます)。モデルのファイルを指定すると出力ディレクトリに写します。ライセンスはモデルごとに違うので配布元で確認してください |

### CP2K・LAMMPS・GROMACS の画面

計算コードのプルダウンで選ぶと、そのコードの欄が出ます。青字は必須の欄です (ラベルにカーソルを合わせると説明が出ます)。

- **CP2K**: 汎関数、カットオフと相対カットオフ [Ry] は既定を持たないので、自分で決めます (CP2K のマニュアルの「CUTOFF と REL_CUTOFF の収束」の手順)。元素ごとの基底と擬ポテンシャルは、data ディレクトリのファイルから読んだ候補がプルダウンに並びます。候補が 1 つだけの元素は空欄のままでそれを使います。分子や表面のように周期でない方向があるときは「ポアソン方程式の解き方」を選び、箱の無い分子なら「分子の箱の一辺」を入れます。画面に無い設定は「追加の行 (節ごと)」に `[FORCE_EVAL/DFT/SCF]` のような見出しを書き、その下に行を書きます。
- **LAMMPS**: 単位系 (metal / real) と pair_style、pair_coeff を書き、力場のファイルを「写すファイル」に入れます (入力の中ではファイル名だけで書きます)。data ファイルを空にすると構造から `data.lammps` を書きます (atomic か charge 形式)。外部の data ファイルを使うときは、型番号の元素を順に入れ、構造の群にも同じ系を読み込みます。k 点の群は出ません。
- **GROMACS**: トポロジー (.top) と構造のファイル (.gro / .pdb) を指定します。**構造の正本は構造のファイルです。**「構造の群にも読み込む」を押すと、構造の群の作り方が「ファイル」になって同じファイルを読み込みます (原子数の確認と 3D 表示に使います。ウェブ版では「構造の欄にもこのファイルを使う」に印を付けます)。NPT では圧浴と等温圧縮率が必須です (GROMACS のマニュアルの水の例は 4.5e-5 /bar)。NVT → NPT → 本計算のように段階を重ねるときは、前の段階の `adit.cpt` を「前の段階の .cpt」に指定します。k 点の群は出ません。

計算の種類のうち、そのコードの生成器に無いもの (LAMMPS と GROMACS の振動解析とバンド計算、CP2K のバンド計算) は、選ぶと「生成できません」の欄に理由が出ます。ほかのコードと同じ扱いです。

ORCA は開発環境に量子化学計算用の本体がないため、入力ファイルの内容だけをテストしています。VASP はクラスタで、DFTB+、xtb、pw.x、CP2K、LAMMPS、GROMACS、OpenMM、Psi4、ABINIT、PLUMED はローカルで実行して確認しています。

## 出力ディレクトリ

```
<出力ディレクトリ>/
  submit.sh      実行スクリプト (ローカル: bash submit.sh / クラスタ: qsub または sbatch submit.sh)
  spec.json      計算設定一式。ADIT で開くと復元できます
  README.txt     実行手順と出力ファイルの見方
  analyze.py     解析スクリプト (analysis/ に図と要約を書きます)
  dftb_in.hsd, geometry.gen, skf/       DFTB+ の場合
  INCAR, POSCAR, KPOINTS, potcar.spec, make_potcar.sh   VASP の場合
  struct.xyz, xtb.inp                   xtb の場合
  pw.in, pseudo/                        Quantum ESPRESSO の場合
  orca.inp                              ORCA の場合
```

## 解析

各出力ディレクトリの `analyze.py` を計算後に実行すると (`python analyze.py --rdf --msd --dos`)、`analysis/` に図 (PNG) と要約 (summary.txt / summary.json) が書かれます。
GUI の「解析」タブ、ウェブ版の「解析」ページ、`adit-analyze` も同じ処理です。数値の良し悪しの判断はしません。

| 解析 | 読むファイル | 出力 |
|---|---|---|
| エネルギー・温度の推移 | DFTB+ md.out / output.log、xtb output.log と xtb.trj、VASP vasprun.xml と OSZICAR、pw.x output.log、ORCA output.log | 折れ線グラフ |
| 動径分布関数 (RDF) | 軌跡 (geo_end.xyz、xtb.trj、vasprun.xml / XDATCAR、pw.x output.log、ORCA trajectory.xyz) | 元素の組ごとの g(r) |
| 平均二乗変位 (MSD) と拡散係数 | 同上 (周期系は境界をまたぐ移動を補正) | MSD の図と、既定では最大ずれ時間の 10〜50 % を直線フィットして求めた D [cm²/s] |
| 状態密度 (DOS) | DFTB+ band.out と detailed.out のフェルミ準位、VASP DOSCAR | ガウス関数で広げた DOS |
| 振動数とスペクトル | DFTB+ hessian.out (質量重み付きヘシアンの対角化)、xtb vibspectrum、VASP OUTCAR、ORCA output.log | 振動数の一覧とスペクトル (IR 強度があれば重み付き) |
| 結合長 | 最終構造 | 共有結合半径の和の 1.2 倍以内にある原子対 |
| バンド図 | `bands/kpath.json` と DFTB+ band.out、pw.x output.log、VASP EIGENVAL | 高対称点のラベル付きバンド図と、フェルミ準位をまたぐ最小の間隔 |
| 原子の電荷 | DFTB+ detailed.out、xtb xtbout.json、CP2K output.log (Mulliken・Hirshfeld) | 原子ごとの表。電荷の定義と出典 (ファイル:行) を添える |
| 熱化学 (コードの値) | xtb・ORCA の output.log | ZPE・H・G などをそのまま (行番号つき) |
| 熱化学 (ASE で計算) | 振動数と最終構造 | 理想気体・調和・準調和・準 RRHO。温度などは利用者が入れる (既定値は無く、足りなければ計算しない理由を出す)。thermo.csv |
| HOMO-LUMO ギャップ・双極子 | xtb xtbout.json など | 値と出典 |
| 時系列の統計 | MD の温度・エネルギー・密度・圧力 | ブロック平均による平均値の誤差 (blocking.png)、積分自己相関時間 |
| 配位数 n(r) | RDF と同じ軌跡 | coordination.png、rdf.json の n と n_reverse |
| z 方向の密度分布 | 周期系の軌跡 | 元素ごとの数密度と質量密度 (zdensity.png / zdensity.json) |
| 圧力 | LAMMPS log.lammps、GROMACS のエネルギーの表 | pressure.png |
| 元素ごとの拡散係数 | MSD と同じ軌跡 | 元素ごとの D [cm²/s] (当てはめ範囲は指定できる) |
| NEB | VASP の像のディレクトリ (00, 01, …)、QE neb.x の .dat / .int、CP2K BAND の output.log | エネルギーの曲線 (neb.png) と障壁。CP2K は像の値のみ |
| PDOS | VASP DOSCAR、QE projwfc.x の *.pdos_atm#… | pdos.png / pdos.csv |
| UV-Vis | ORCA の TD-DFT の吸収の表 | 遷移の表 (uvvis_transitions.csv) と、広げたスペクトル (uvvis.png) |
| 空間群 | 最終構造 (spglib が入っているとき) | 許容誤差ごとの空間群 |
| フォノン分散・DOS | phonopy の band.yaml、total_dos.dat | phonon_bands.png、phonon_dos.png |
| 組にして比べる表 | 複数の計算のディレクトリ | ΣνE、組成の釣り合い、条件が違う項目 (compare_*.csv、compare_energy.png) |

`adit-analyze` の主なオプション (`adit-analyze --help` に全部):

| オプション | 意味 |
|---|---|
| `--stride N` | 軌跡を N フレームおきに使う (大きな軌跡の間引き。RDF・MSD・z 密度・書き出しに効く) |
| `--msd-fit T0 T1` | 拡散係数を当てはめる時間の範囲 [fs] (既定は最大の遅れ時間の 10〜50 %) |
| `--zdens [Å]` | z 方向の密度分布 (数を続けると区間の幅。既定 0.2 Å。周期系だけ) |
| `--export` | 軌跡を `analysis/export/` に書き出す (extxyz・xyz・pdb、VMD の view.vmd、OVITO の ovito_pipeline.py、export_README.txt) |
| `--unwrap-molecules` | 書き出す前に分子を周期境界でつなぎ直す (`--export` を含む) |
| `--memory-mb MB` | MSD で座標を持つメモリの上限 (既定 1024)。超える軌跡は読まずに止まり、間引きの間隔を示す |
| `--compare [組]` | 組にして比べる表。`"ads=1:slab_mol,-1:slab,-1:mol"` (係数:ディレクトリ。反応は `;` で区切る)。省くと compare.json を読む |
| `--thermo MODEL` ほか | 熱化学 (ASE)。`--temperature` `--pressure` `--symmetry-number` `--geometry` `--spin` `--imaginary` `--exclude-lowest` `--qh-cutoff` `--msrrho-tau` をモデルに合わせて入れる |
| `--uvvis SHAPE:FWHM` | ORCA の UV-Vis を広げる形と半値全幅 [eV] (例 `gauss:0.3`) |
| `--pdos` | PDOS のファイルが無いときも理由を書く (あれば指定しなくても描く) |
| `--symprec Å[,Å…]` | 空間群の許容誤差 (既定は 1e-5、1e-3、1e-1 を並べる) |

```bash
adit-analyze out/md --msd --stride 10 --msd-fit 1000 5000 --zdens 0.5
adit-analyze out/md --export --unwrap-molecules
adit-analyze out/vib --thermo ideal_gas --temperature 298.15 --pressure 100000 --symmetry-number 2 --geometry nonlinear --spin 0
adit-analyze runs/ --compare "ads=1:slab_mol,-1:slab,-1:mol"
```

画面では、解析タブ (ウェブ版は解析のページ) の「詳しい条件」を開くと、上のオプションと同じ欄があります (間引き、MSD の当てはめ範囲、
z 方向の密度分布、時系列の統計、熱化学の各欄、UV-Vis の広げ方、空間群の許容誤差)。熱化学の欄には既定値を入れていません。
結果は要約の下に表 (原子の電荷、熱化学、電子状態、時系列の統計、軌跡、拡散係数、空間群、UV-Vis の遷移) と図で出ます。表は見出しを押すと畳めます。
長い表は先頭 20 行だけを出し、全体のファイルの場所を添えます。

- 軌跡が大きすぎて止まったときは、理由の文と「間引きを N にする」ボタンが出ます。押すと間引きの欄に N が入るので、もう一度「解析を実行」を押します
- MSD では周期境界を越えた移動を最小像から復元します。間引き後の隣接フレーム間で移動が最短セル幅の40 %以上になった場合は、移動方向を一意に復元できなくなる半セル幅へ近いため、要約と`summary.json`に注意を残します。
- MSD の D は指定した時間範囲の直線フィットから求めます。ブロックごとの D を使う参考誤差は、すべてのブロックで同じ時間範囲を使える場合だけ表示します。短い軌跡では D が出てもブロック誤差は出ないことがあります。参考誤差はブロック D の平均の標準誤差であり、全軌跡から求めた D の厳密な誤差ではありません。

The MSD-derived D comes from a linear fit over the stated time range. A reference block-based error is shown only when every block can use that same range. A short trajectory may yield D without a block error. This error is the standard error of the mean block D, not a rigorous error on D fitted from the full trajectory.
- 「TRAVIS・VMD・OVITO 用に書き出す」で `analysis/export/` に書き出し、export_README.txt の中身を表示します。
  デスクトップ版は「書き出したフォルダを開く」でファイルマネージャを開きます (ウェブ版は場所を表示するだけ)
- 「組にして比べる…」で、比べる計算のディレクトリと係数を行で入れます (名前が空の行は上の行と同じ反応)。
  デスクトップ版は小さな画面、ウェブ版は別のページ (`/compare`)。基準のディレクトリに compare.json があれば読み込めます

## 収束の確認と格子定数 (1 つの条件を変えて一括生成)

平面波 DFT (VASP、Quantum ESPRESSO) の結果は、化学的な条件とは別に、数値計算の細かさの設定で変わります。
代表は **カットオフエネルギー** (電子の波をどこまで細かく表すか。QE の `ecutwfc`、VASP の `ENCUT`) と **k 点** (結晶の中の電子の状態を何点で代表させるか) です。
小さすぎると答えがずれ、大きすぎると計算時間が膨らむので、値を上げていき、エネルギーがほとんど変わらなくなる所を探します。これが収束の確認です。
格子の大きさを少しずつ変えてエネルギーを並べると、平衡の格子定数と体積弾性率 (どれだけ潰れにくいか) も求まります。

ADIT は、1 つの条件だけを変えた入力を値ごとのディレクトリにまとめて作り、実行したあとの結果を表と図にします。

**画面から**

1. いつもどおり構造と計算の条件を決めます。
2. 「実行」メニューの「1 つの条件を変えて一括生成…」を開き、変える項目 (カットオフ / k 点の分割数 / k 点の密度 / 格子の大きさ / その他) と値 (カンマ区切り) を入れて「生成」を押します。
3. できたディレクトリをそれぞれ実行します (この PC なら各ディレクトリで `bash submit.sh`、クラスタならジョブとして。大きな系はクラスタで)。
4. すべて終わったら、解析タブで「解析を実行」を押します (ディレクトリの欄には保存先が入っています)。

**コマンド行から**

```bash
adit-gen spec.json out/ --scan method.ecutwfc=30,40,50,60     # QE のカットオフ [Ry]
adit-gen spec.json out/ --scan kpoints.mesh=4x4x4,6x6x6,8x8x8  # k 点の分割数
adit-gen spec.json out/ --scan scale=0.97,0.98,0.99,1.00,1.01,1.02,1.03   # 格子の大きさ (周期系)

# それぞれを実行したあと
adit-analyze out/ --scan
```

**表と図の読み方** (`out/scan_energies.csv`、`out/scan_energy.png`、格子の大きさなら `out/eos.png` と `out/eos.json`)

| 列 | 意味 |
|---|---|
| 最後の値との差 [meV/原子] | いちばん最後に書いた値 (ふつう最も細かい条件) のエネルギーとの差を、原子の数で割ったもの。格子の大きさを変えたときだけは「最小値との差」で、エネルギーがいちばん低い倍率を 0 にします |
| 力の最大値 [eV/Å]、圧力 [GPa] | 最終構造の値 (DFTB+、QE、VASP の出力から読めるときだけ) |
| 状態方程式の当てはめ | 格子の大きさを 5 点以上変えたときだけ。Birch–Murnaghan の式で、平衡の体積・体積弾性率・エネルギーが最小になる倍率とそのときの格子の長さを出します |

どの値で十分とみなすかは、計算の目的によって違うので、ADIT は判断しません。
よく使われる目安は 1 原子あたり 1 meV 程度ですが、反応エネルギーのように差を見る計算ではもっと緩くてよいことが多く、力や応力 (格子定数、振動) を使う計算ではもっと厳しくする必要があります。

**注意すること**

- ふつうはカットオフを先に決め、次に k 点を決めます。
- QE の `ecutrho` (電荷密度のカットオフ) を 0 (指定しない) にすると、pw.x は `ecutwfc` の 4 倍を使います。ウルトラソフトや PAW の擬ポテンシャルでは、もっと大きな値を求められることがあります。
- VASP で体積を変える計算 (格子の大きさの一括生成や格子の緩和) では、カットオフが低いと見かけの応力 (Pulay 応力) が出て、格子定数が小さめに出ます。POTCAR の既定より 3 割ほど高い `ENCUT` がよく勧められます。
- 金属は k 点の収束が遅いので、占有の広げ方 (smearing) とその幅も合わせて決めます。
- 値の数だけ計算が増えます。

## ウェブ版

```bash
adit-web --open        # http://127.0.0.1:8765/
```

デスクトップ版と同じ生成と解析を、ブラウザのフォームから行います。「プレビュー」で生成ファイルの内容を確認し、「入力を生成」でサーバー (adit-web を動かしている PC) 上の出力ディレクトリに書き出します。
「この PC で実行」の条件はデスクトップ版と同じです。「解析」ページでは計算結果のディレクトリを解析し、図と要約をそのページに表示します。spec.json の読み込みとダウンロードもできます。

依存は Python の標準ライブラリと Jinja2 だけです。**認証はありません。**既定では 127.0.0.1 でのみ待ち受けます。`--host 0.0.0.0` にすると、そのアドレスに届く人は誰でも生成と実行ができるため、信頼できるネットワークの中だけで使ってください。

## 開発

```bash
pip install ".[dev]"
pytest -q            # dftb+ / xtb / pw.x が PATH にあれば、実際に実行するテストも走ります
```


新しい計算コードを追加するには、`codes/<name>.py` に `InputGenerator` を実装して `register()` し、`spec.py` に Method を追加し、GUI にパネルを追加します。
