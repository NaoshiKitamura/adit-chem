# ORCA GOAT・DOCKER ほかの機能 / GOAT, DOCKER and other entry points

ADIT は計算条件を推測せず、ジョブも投入しません。次の機能はコマンドラインから使えます。デスクトップ画面の操作欄はまだありません。ORCA の GOAT / DOCKER の条件は spec.json を画面で読み込んで保存しても保持されますが、画面上では編集できません。生成する前にプレビューで入力を確認してください。DCDFTBMD の spec.json は画面では開けないので、コマンドラインを使います。

ADIT does not guess calculation settings or submit jobs. The functions below are available from the command line; no desktop controls have been added. GOAT/DOCKER settings survive a load-and-save round trip in the desktop application but cannot be edited there. Check the generated input in the preview before writing it. DCDFTBMD spec.json files cannot be opened in the desktop application; use the command line.

## ORCA GOAT

`method.code="orca"`, `task.type="single_point"`, `method.goat=true` を `spec.json` に指定し、`adit-gen spec.json out/` で生成します。`method.method="XTB"` と `method.basis=""` は [ORCA 6.1 GOAT チュートリアル](https://www.faccts.de/docs/orca/6.1/tutorials/prop/goat.html)と同じ入力の例です。計算後は `orca.globalminimum.xyz` と `orca.finalensemble.xyz`、エネルギーと重みは `output.log` を確認してください。ORCA 本体は同梱しておらず、この環境では実走していません。

Set `method.code="orca"`, `task.type="single_point"`, and `method.goat=true` in `spec.json`, then run `adit-gen spec.json out/`. For the documented ORCA 6.1 tutorial form, set `method.method="XTB"` and `method.basis=""`. After the run, inspect `orca.globalminimum.xyz`, `orca.finalensemble.xyz`, and the energies and weights in `output.log`. ORCA is not bundled and has not been run in this development environment.

## ORCA DOCKER / Host–guest docking

ホストは `spec.json` の構造、ゲストは `method.docker_guest_file` の XYZ で指定します。`task.type="single_point"`、`method.method="XTB"`、`method.basis=""` にし、XYZ の各フレームの 2 行目に電荷と多重度を整数で書きます (例 `0 1`)。書かれていないフレームを ORCA の既定 (0, 1) として扱う場合だけ、`method.docker_assume_neutral_singlet=true` を明示します。ADIT はゲストを `guest.xyz` として写し、`%DOCKER GUEST "guest.xyz" END` を生成します。[ORCA 6.1 マニュアル](https://www.faccts.de/docs/orca/6.1/manual/contents/structurereactivity/docker.html)に従い、DOCKER は XTB/GFN-xTB/GFN-FF に限ります。結果は `orca.docker.xyz` と `output.log` を確認してください。

The host is the structure in `spec.json`; set `method.docker_guest_file` to the guest XYZ. Use `task.type="single_point"`, `method.method="XTB"`, and `method.basis=""`. The second line of each XYZ frame must contain integer charge and multiplicity, for example `0 1`. Only if you intend ORCA's default (0, 1) for frames without these values, explicitly set `method.docker_assume_neutral_singlet=true`. ADIT copies the guest as `guest.xyz` and writes `%DOCKER GUEST "guest.xyz" END`. ORCA 6.1 restricts DOCKER to XTB/GFN-xTB/GFN-FF. Inspect `orca.docker.xyz` and `output.log` after running.

## DCDFTBMD 2.0

`method.code="dcdftbmd"` に加え、`method.scc`、`method.divide_and_conquer`、構造中の各元素の `method.highest_angular_momentum` (s=1、p=2、d=3、f=4)、**順序つき**の各元素対の `method.sk_files` (`.spl`)を明示します。例：O と H なら `O-O`、`O-H`、`H-O`、`H-H` が必要です。`adit-gen spec.json out/` は `dftb.inp`、`.spl` の複製、`submit.sh` を生成します。DFTB+ の `.skf` は変換しません。対応するのは一点計算、最急降下法/FIRE の構造最適化、NVE と Berendsen NVT です。NVT の温度と時定数は共通 MD 条件から単位だけ換算します。NPT、開殻、軸固定、その他の熱浴は生成前に止めます。実行ファイルと `.spl` は利用者が入手してください。[公式 2.0 マニュアル](https://www.chem.waseda.ac.jp/dcdftbmd/document/DCDFTBMD_2.0_en.pdf)。

For `method.code="dcdftbmd"`, explicitly set `method.scc`, `method.divide_and_conquer`, `method.highest_angular_momentum` for each element (s=1, p=2, d=3, f=4), and `method.sk_files` for every **ordered** element pair. For O and H, specify `O-O`, `O-H`, `H-O`, and `H-H` `.spl` files. `adit-gen spec.json out/` creates `dftb.inp`, copies the `.spl` files, and creates `submit.sh`; it does not convert DFTB+ `.skf` files. Supported tasks are single point, SteepestDescent/FIRE optimization, NVE, and Berendsen NVT. Temperature and coupling time are converted only in units. NPT, open-shell systems, axis constraints, and other thermostats stop before generation. Obtain the executable and `.spl` files yourself. See the [official 2.0 manual](https://www.chem.waseda.ac.jp/dcdftbmd/document/DCDFTBMD_2.0_en.pdf).

## DOCK6

`adit-convert dock6 prepared/dock.in ready/` は、**利用者が完成させた** `dock.in` と、そこから参照される配位子、球、格子、既知の定義ファイルをまとめます。必要に応じて `--asset relative/path` を繰り返して追加してください。パスは `dock.in` と同じ作業ディレクトリからの相対パスにし、出力先は入力ディレクトリの外の空の場所にします。元の `dock.in` は変更せず、複製の SHA-256 と `run.sh` を書きます。受容体・配位子の準備、電荷、原子型、スコア条件を作る機能ではありません。[DOCK 6.13 マニュアル](https://dock.compbio.ucsf.edu/DOCK_6/dock6_manual.htm)の入力を完成させてから使ってください。

`adit-convert dock6 prepared/dock.in ready/` packages a **completed, user-authored** `dock.in`, its ligand, spheres, grid files, and recognized definition files. Repeat `--asset relative/path` for other dependencies. Paths must be relative to the `dock.in` working directory, and the empty output directory must be outside the input directory. The input deck is unchanged; ADIT writes SHA-256 hashes and `run.sh`. This does not prepare the receptor or ligand, assign charges or atom types, or choose scoring settings. Complete the input using the [DOCK 6.13 manual](https://dock.compbio.ucsf.edu/DOCK_6/dock6_manual.htm) first.

## Open Babel

`adit-convert openbabel source.sdf target.mol2 --input-format sdf --output-format mol2` は、PATH 上の `obabel` を明示的に使用します。入力と出力は同じファイルにできず、既存の出力は `--overwrite` を付けない限り変更しません。変換結果は一時ファイルに書いてから移動します。失敗時は以前の出力を保ち、途中ファイルの場所を表示します。結合次数・電荷・セル・座標が目的どおりか確認してください。[Open Babel の CLI 文書](https://openbabel.org/docs/Command-line_tools/babel.html)。

`adit-convert openbabel source.sdf target.mol2 --input-format sdf --output-format mol2` explicitly invokes `obabel` from PATH. Input and output cannot be the same file; an existing output is untouched unless `--overwrite` is given. ADIT stages the result before moving it into place. On failure it preserves the previous output and reports the partial file. Check bond orders, charges, cell, and coordinates for your use case. See the [Open Babel CLI documentation](https://openbabel.org/docs/Command-line_tools/babel.html).
