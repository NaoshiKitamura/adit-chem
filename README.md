# ADIT

**Atomistic Design and Interpretation Toolkit** — 計算化学の実行に必要なインプットファイルを、
**画面上で直感的・視覚的に作れる**デスクトップアプリです。

[![tests](https://github.com/adit-chem-project/adit-chem/actions/workflows/tests.yml/badge.svg)](https://github.com/adit-chem-project/adit-chem/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/adit-chem?color=2f7ae5)](https://pypi.org/project/adit-chem/)
[![Python](https://img.shields.io/pypi/pyversions/adit-chem)](https://pypi.org/project/adit-chem/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

![ADIT の画面](docs/images/desktop_light.png)

構造を選んだり作製したりでき、計算ソフトと計算条件を選べます。決定すると、実行に必要なファイル一式が
出力されます。シミュレーション後は、同じ画面で結果を解析でき、図や表に出力できます。

**コマンド操作は要りません。**計算化学を使いたいが、CLI やプログラムの操作には慣れていない、という人が
対象です。インプットの作成から結果の解析まで 1 つのアプリで完結するので、
複数のソフトを行き来したり、そのつど探して入れたりする必要がなくなります。

---

## インストール

**Windows** — [Releases](https://github.com/adit-chem-project/adit-chem/releases) から
`ADIT-windows-x64.zip` をダウンロードし、展開して `ADIT.exe` を起動します。
初回に SmartScreen の警告が出たら「詳細情報」→「実行」を選んでください。

**macOS (Apple Silicon)** — 同じ場所から `ADIT-arm64.zip` を落とし、初回だけ Finder で
右クリック →「開く」を選びます。Intel の Mac では、下の pip で入れてください。

**Python から入れる場合** (Linux、または自分で環境を管理したい人向け)

```bash
pip install "adit-chem[gui,smiles,analysis]" --pre
```

| コマンド | 内容 |
|---|---|
| `adit` | デスクトップアプリ |
| `adit-gen` / `adit-analyze` / `adit-report` | コマンドライン |

計算ソフト (DFTB+、VASP、Quantum ESPRESSO ほか) と、そのパラメータ (Slater-Koster、擬ポテンシャル、POTCAR) は
別途用意してください。詳しい手順は [インストール方法](docs/INSTALL.md) にあります。

## 使ってみる

1. ADIT を起動します
2. **構造** タブで、プリセットから `H2O` を選びます
3. **計算条件** タブで、計算コード (例: DFTB+) と計算の種類 (例: 構造最適化) を選びます
4. **生成** を押して、書き出し先のフォルダを指定します
5. **ワークスペース** タブのターミナルで `bash submit.sh` を実行します
   (クラスタで計算する場合は、`transfer_and_submit.sh` のコマンドを使います)
6. 計算が終わったら **解析** タブでフォルダを指定し、**解析を実行** を押します

![解析の結果](docs/images/tutorial/06_analysis_result.png)

`結合長 (最終構造): O1-H2 0.967 Å` のように出れば成功です。
画像付きの詳しい手順は [チュートリアル](docs/USAGE.md) を参照してください。

## できること

### 構造を作る

プリセット分子、SMILES、構造ファイル、バルク結晶、表面スラブ、溶液・混合物。
**Draw** では、分子を描いて SMILES にできます。
作った構造は 3D 表示で、マウスで回しながら確認できます。

### インプットファイルを書き出す

21 の計算コードに対応しています。

![対応表](docs/images/support_matrix.png)

書き出されるファイルは次のとおりです。

| ファイル | 内容 |
|---|---|
| インプットファイル | 計算コードごとの入力 (`dftb_in.hsd`、`INCAR`、`pw.in` など) |
| `submit.sh` | 計算を実行するスクリプト |
| `README.txt` | 実行方法の手引き |
| `spec.json` | 設定した条件をそのまま保存したもの。読み込めば同じ入力を作り直せます |
| `analyze.py` | 解析用のスクリプト |
| `transfer_and_submit.sh` | クラスタへ送って投入するコマンド (クラスタ向けに生成したときだけ) |

実行は、ワークスペースのターミナルで行います (`bash submit.sh`)。自動処理では `adit-gen ... --run` も使えます。

### ファイルを扱う・ターミナルを使う

**ワークスペース** タブに、ファイルのツリー・エディタ・ターミナルがあります。インプットの手直し、
ファイルの整理、`ssh` でのクラスタ接続まで、画面を切り替えずに行えます。

![ワークスペース](docs/images/tutorial/19_workspace.png)

### 結果を解析する

エネルギー・温度、RDF、MSD と拡散係数、状態密度、バンド図、振動数とスペクトル (赤外・ラマン)。
配位数、構造因子 S(q)、水素結合、Voronoi、溶媒接触表面積、自由エネルギー面など、80 以上の解析手法に対応しています。

![解析の図](docs/images/analysis_figures.png)

解析の**要約**には、値ごとに「その値を読み取ったファイル名と行番号」が付きます
(画面の解析タブと、書き出される `analysis/summary.txt` の両方)。転記した数字を後から追えます。

```
原子の電荷 (Mulliken、detailed.out:18、単位 e): O1 -0.606, H2 +0.294, H3 +0.312
```

### 図を論文やスライドへ

構造式・3D 表示・解析の図を、SVG・PNG・MOL で書き出せます。
画像をクリップボードにコピーして、例えば Word にそのまま貼ることもできます。
線の色・目盛りの向き・グリッド線・枠を指定して保存できるので、投稿先の指定にも合わせられます。

### 計算の記録を残す

**どんなときに何が出てくるか**は次のとおりです。書き出されるのは記録だけで、
記録が無い項目は「未記録」と書かれます。

| こんなとき | 使う機能 | 出てくるもの |
|---|---|---|
| 論文の「計算方法」を書く | 方法の記述 | 計算ソフトとそのバージョン、汎関数、基底関数、k 点 (Markdown) |
| 条件を変えた計算をまとめて示す | 条件の一覧 | 1 計算 1 行の表。温度を変えた 5 本なら 5 行 (CSV) |
| 結果を一覧で確かめる | 結果の一覧 | 最終エネルギー、平均温度、フレーム数、正常終了したか (CSV) |
| 計算一式を第三者へ渡す | 再現用の一式 | インプット + **計算ソフトのバージョン** + **擬ポテンシャルなどの実体** + SHA-256 (ZIP) |
| インプットを手で直したか確かめる | 入力の照合 | `spec.json` と実際のファイルの食い違い (例: ENCUT が 400 と 520 で違う) |

詳しくは [計算条件の報告](docs/REPORT.md)。

## ドキュメント

| 文書 | 内容 |
|---|---|
| [インストール方法](docs/INSTALL.md) | Windows で初めて使う手順、Linux / macOS、実行ファイルの作り方 |
| [チュートリアル](docs/USAGE.md) | 画面の操作を、手順ごとの画像で |
| [画面の説明](docs/SCREENS.md) | 欄ごとに何を決めるか |
| [設定と解析](docs/SETTINGS_AND_ANALYSIS.md) | 環境設定、コードごとの準備、解析の詳細 |
| [対応コードの範囲](docs/NEW_ENGINES.md) | 計算コードごとに、どこまで対応しているか |
| [ORCA GOAT・DOCKER ほか](docs/EXTRA_ENTRY_POINTS.md) | 配座探索、ホスト-ゲスト、DCDFTBMD、DOCK6、Open Babel |
| [実行ファイルの作り方](docs/WINDOWS_BUILD.md) | Windows の .exe (macOS は [こちら](docs/MACOS_BUILD.md)) |
| [重い解析](docs/HEAVY_ANALYSIS.md) | 大きな軌跡を計算機で処理する |
| [Python API](docs/API.md) | ライブラリとして使う |
| [開発に参加](CONTRIBUTING.md) | 動かし方と設計の方針 |

## ライセンス

[MIT](LICENSE) です。`examples/` と `tests/data/` に含まれる他プロジェクト由来のファイルは、
元のライセンスのままです ([一覧](THIRD_PARTY_NOTICES.md))。
