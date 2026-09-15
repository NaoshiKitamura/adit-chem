# インストール方法

ADIT を入れて、最初の計算を実行するまでの手順です。

## いちばん簡単な方法: 実行ファイルを使う (Windows / macOS)

**Python も WSL も要りません。**

1. [Releases](https://github.com/NaoshiKitamura/adit-chem/releases) を開きます
2. Windows なら `ADIT-windows-x64.zip`、macOS (Apple Silicon) なら `ADIT-arm64.zip` を
   ダウンロードします (Intel の Mac 用は配っていません。下の pip で入れてください)
3. 展開し、Windows は `ADIT.exe`、macOS は `ADIT.app` をダブルクリックします

署名を付けていないため、初回だけ警告が出ます。Windows は「詳細情報」→「実行」、
macOS は Finder で右クリック →「開く」を選んでください。

コマンドライン (`adit-gen` など) を使いたいときは、同じフォルダの `adit-cli.exe` (macOS は `adit-cli`) を呼びます。

同じ PC で計算まで実行したい場合は、次の節へ進んでください。

## 同じ PC で計算まで実行したい人へ (Windows、この順に進めてください)

Linux を使ったことがなくても、この節の手順を上から順に行えば、最初の入力ファイルを作って計算を実行するところまで進めます。
コマンドは **1 行ずつ**コピーしてターミナル (文字でコンピュータに指示を出す黒い画面) に貼り付け、Enter を押します。
`#` から行末までは説明なので、貼り付けなくてもかまいません。`<...>` は自分の値に置き換えます。

### 1. WSL (Windows の中で Linux を動かす仕組み) を入れる

1. スタートメニューで「PowerShell」を右クリックし、「管理者として実行」を選びます
2. 次の 1 行を入力して Enter を押し、終わったら PC を再起動します

   ```powershell
   wsl --install
   ```

3. 再起動後に「Ubuntu」の画面が開くので、Linux 用のユーザー名とパスワードを決めます (Windows のものとは別です。パスワードは入力しても画面に表示されません)

以後は、スタートメニューの「Ubuntu」で開く画面 (ターミナル) で作業します。

### 2. miniforge (conda) を入れる

conda は、Python や計算ソフトを「環境」という箱に分けて入れる仕組みです。miniforge はその配布版で、conda-forge (DFTB+、xtb、Quantum ESPRESSO を配布している場所) を既定で使います。

```bash
curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
bash Miniforge3-$(uname)-$(uname -m).sh      # 質問には Enter と yes で答えます
```

終わったら、ターミナルを一度閉じて開き直します。行頭に `(base)` と出ていれば入っています。

> **venv ではなく conda を勧める理由**: ADIT は Python だけで動きますが、この PC で計算を実行するには DFTB+ などの計算ソフトが要ります。
> conda ならそれらを同じ手順で入れられます。WSL の Ubuntu には最初 `python` コマンドが無く `python3` だけですが、conda の環境を有効にすると `python` が使えます。
> 計算はクラスタでしか実行せず、手元では入力の生成だけをする場合は、`python3 -m venv adit-env` と `source adit-env/bin/activate` の venv でもかまいません。

### 3. ADIT と DFTB+ を入れる環境を作る

```bash
conda create -n adit -c conda-forge "python>=3.11" dftbplus rdkit font-ttf-noto-cjk git
conda activate adit                         # 行頭が (adit) に変わります。ターミナルを開くたびに打ちます
```

`font-ttf-noto-cjk` はデスクトップ版の画面で日本語を表示するためのフォントです (WSL には最初、日本語のフォントがありません)。
xtb と Quantum ESPRESSO は、DFTB+ と同じ環境に入れると DFTB+ のバージョンが古いものに下がることがあるため、別の環境に入れます (使うものだけで十分です)。

```bash
conda create -n xtb -c conda-forge xtb
conda create -n qe -c conda-forge qe
conda activate --stack xtb                   # adit の環境を有効にしたまま、xtb も使えるようにする例
```

### 4. ADIT を入れる

ADIT の配布元の URL (git のリポジトリの場所) は、このソフトを紹介してくれた人 (配布元) に聞いてください。

```bash
pip install "adit-chem[gui] @ git+<配布元の URL>"
```

フォルダごと受け取った場合 (手元に複製した場合) は、そのフォルダに移動して `pip install ".[gui]"` を実行します。

### 5. パラメータを入手して置く

計算コードによっては、元素ごとのパラメータのファイルが要ります。ADIT には入っていないので、配布元から入手します。
Windows のブラウザでダウンロードしたファイルは、WSL の中からは `/mnt/c/Users/<Windows のユーザー名>/Downloads/` に見えます。

**DFTB+ の Slater-Koster パラメータ** (元素の組ごとの `.skf` ファイル。ライセンスは CC BY-SA 4.0 です)

入手先: https://dftb.org/parameters/download.html (水や有機分子なら mio が入り口です。mio が扱う元素は H, C, N, O, S, P)

```bash
mkdir -p ~/slakos                                                   # 置き場所を作る (~ は自分のホームフォルダ)
tar -xf /mnt/c/Users/<Windows のユーザー名>/Downloads/mio-1-1.tar.xz -C ~/slakos
ls ~/slakos/mio-1-1                                                 # H-H.skf などが並べば置けています
```

展開後は次の形になります。セットのフォルダ (`mio-1-1/`) の中に `.skf` と `LICENSE`、`README` が直接入っている形です。

```
~/slakos/
  mio-1-1/
    H-H.skf  H-O.skf  O-H.skf  O-O.skf  C-C.skf  …  LICENSE  README
```

**Quantum ESPRESSO の擬ポテンシャル (UPF ファイル)**

入手先の例: SSSP https://www.materialscloud.org/discover/sssp (ライセンスは配布元で確認してください)。
展開して、`.UPF` ファイルが直接入ったフォルダを、たとえば `~/pseudo/SSSP_efficiency/` として置きます。フォルダの名前が ADIT の「擬ポテンシャルのセット」になります。

```
~/pseudo/
  SSSP_efficiency/
    Si.pbe-n-rrkjus_psl.1.0.0.UPF  O.pbe-n-kjpaw_psl.0.1.UPF  …
```

xtb は計算手法にパラメータが入っているので不要です。VASP の POTCAR と ORCA は、下の「各計算コードで用意するもの」を見てください。

### 6. 環境設定ファイルに置き場所を書く

はじめて `adit-web` か `adit-gen` を実行すると、環境設定ファイル `~/.config/adit/cluster.toml` が作られ、その場所が表示されます。
次のコマンドで開き (nano は端末で使う簡単な文字エディタです。Ctrl+O → Enter で保存、Ctrl+X で終了)、置き場所を書きます。

```bash
echo $HOME                                   # 自分のホームフォルダ (例 /home/taro) が出ます
nano ~/.config/adit/cluster.toml
```

```toml
sk_root = "/home/<ユーザー名>/slakos"        # 5 で作った置き場所。セットのフォルダ (mio-1-1) の 1 つ上
pseudo_root = "/home/<ユーザー名>/pseudo"    # Quantum ESPRESSO を使うとき
```

パスは必ず `"..."` で囲みます。Windows の書き方 (`C:\Users\...`) はそのままでは読めません。WSL の中では `C:\Users\taro` は `/mnt/c/Users/taro` です。

### 7. 最初の入力を作って実行する

```bash
adit-web --open                             # ブラウザが開かなければ、Windows のブラウザで http://127.0.0.1:8765/ を開きます
```

ブラウザの画面で、構造「プリセット」の H2O、計算コード DFTB+、Slater-Koster パラメータ mio-1-1、プロファイル local のまま「プレビュー」→「生成」→「生成した入力をこの PC で実行」→「解析へ進む」と進みます。
ターミナルだけで行う場合は、画面で保存した計算設定 (spec.json) から次のように作れます。

```bash
adit-gen spec.json ~/adit_runs/water       # 入力ファイル一式を ~/adit_runs/water に書きます
cd ~/adit_runs/water && bash submit.sh      # 計算を実行します (記録は output.log)
python analyze.py                            # 図と要約を analysis/ に書きます
```

各ディレクトリの `README.txt` に、そのディレクトリでの手順が書かれています。

## ダブルクリックで起動する形 (.exe) を作る

配布されている実行ファイルは、この手順で作っています。自分で作り直すこともできます。

`v` で始まるタグ (例 `v0.1.0a1`) を押し上げると、GitHub Actions が Windows の `.exe` と macOS の `.app` を作り、
Releases に添付します (`.github/workflows/windows-exe.yml`、`macos-app.yml`)。手元で作る手順と確認の項目は
[Windows の実行ファイルを作る](WINDOWS_BUILD.md)。**Windows の .exe は Windows 上でしか作れません。**
出来上がりは 300〜500 MB です。

`pyinstaller packaging/adit.spec` builds a standalone bundle; see `docs/WINDOWS_BUILD.md`. A Windows `.exe`
can only be built on Windows (a manual GitHub Actions workflow is included).

## インストールと起動 (Linux / macOS / 慣れている人向け)

Python 3.11 以上が必要です。仮想環境 (conda か venv) を作り、pip でインストールします。Windows で初めての人は上の節から進めてください。
依存パッケージは ASE、pydantic、Jinja2、matplotlib、SciPy、tomli-w と、デスクトップ版には PySide6 です。SMILES と Draw (分子を描く機能) を使うには RDKit も必要です。

```bash
python3 -m venv adit-env                # conda を使うなら上の節の 3 のとおり
source adit-env/bin/activate            # Windows (PowerShell) では  adit-env\Scripts\Activate.ps1
pip install "adit-chem[gui] @ git+<配布元の URL>"   # URL は配布元に聞いてください。手元に複製したなら  pip install ".[gui]"
```

配布名は `adit-chem` です (PyPI の `adit` は別のパッケージです)。インポート名とコマンド名は `adit` です。

| 使い方 | コマンド | 備考 |
|---|---|---|
| デスクトップ版 | `adit` | PySide6 が必要です |
| ウェブ版 (ブラウザ) | `adit-web --open` | PySide6 は不要です。`http://127.0.0.1:8765/` が開きます |
| コマンドライン (生成) | `adit-gen spec.json <出力ディレクトリ>` | GUI で保存した計算設定から生成します |
| コマンドライン (変換) | `adit-convert structure ...` / `adit-convert calculation ...` | 構造形式を変換するか、共通条件を保って別の計算コードの入力を生成します |
| コマンドライン (解析) | `adit-analyze <計算結果のディレクトリ> --rdf --msd --dos` | 図と要約を `analysis/` に書きます |

### 構造形式と計算コードの変換


構造ファイルは、ASE が対応する形式の間で変換できます。入力と出力の形式は通常、ファイル名から判定されます。
デスクトップ版では「ファイル」タブの「変換」、ウェブ版では上部の「変換」から同じ機能を使えます。判定できないファイル名では、ASEの形式名を入力形式・出力形式の欄に指定できます。
どちらの画面でも、準備画面でプレビューした現在の構造をextended XYZとして保存できます。セル、周期境界、固定原子・軸固定、設定済みの初速度も保持されます。CLI で `spec.json` や生成ディレクトリから構造を変換するときも同じ情報を読みます。

Saving the current structure as extended XYZ preserves the cell, periodic boundaries, fixed atoms and axes, and any initial velocities. CLI structure conversion from `spec.json` or a generated directory reads these data as well.

```bash
adit-convert structure data.lammps POSCAR
adit-convert structure POSCAR structure.data
adit-convert structure POSCAR structure.xyz
adit-convert structure trajectory.extxyz final.cif --frame -1
adit-convert combine molecule_a.xyz molecule_b.xyz combined.xyz
adit-convert openbabel source.sdf target.mol2 --input-format sdf --output-format mol2
adit-convert dock6 prepared/dock.in ready/
```

GOAT、ORCA DOCKER、DCDFTBMD 2.0、DOCK6 の入力整理、Open Babel の変換入口は、[GOAT・DOCKER ほかの機能](EXTRA_ENTRY_POINTS.md)に日英の手順と制限を記載しています。これらの GUI/Web 欄はまだありません。

See [GOAT, DOCKER and other entry points](EXTRA_ENTRY_POINTS.md) for bilingual instructions and limitations for GOAT, ORCA DOCKER, DCDFTBMD 2.0, DOCK6 input packaging, and Open Babel conversion. GUI/Web controls have not been added.
