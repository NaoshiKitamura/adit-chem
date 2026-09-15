# ADIT

**Atomistic Design and Interpretation Toolkit** — 計算化学の入力を作り、結果を図にするデスクトップアプリです。

[![tests](https://github.com/NaoshiKitamura/adit-chem/actions/workflows/tests.yml/badge.svg)](https://github.com/NaoshiKitamura/adit-chem/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/adit-chem?color=2f7ae5)](https://pypi.org/project/adit-chem/)
[![Python](https://img.shields.io/pypi/pyversions/adit-chem)](https://pypi.org/project/adit-chem/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

![ADIT の画面](docs/images/desktop_light.png)

構造を選び、計算コードと条件を決めると、実行用の入力ファイル一式が出力されます。
計算が終わったら、同じ画面で結果の解析を行い、図と表にできます。

---

## インストール

**Windows** — [Releases](https://github.com/NaoshiKitamura/adit-chem/releases) から `ADIT-windows-x64.zip` を
ダウンロードし、展開して `ADIT.exe` をダブルクリックします。**Python の用意は要りません。**
署名を付けていないため、初回に SmartScreen の警告が出たら「詳細情報」→「実行」を選んでください。

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

1. `adit` と入力してアプリを起動します
2. **構造** タブで、プリセットから `H2O` を選びます
3. **計算条件** タブで、計算コード (例: DFTB+) と計算の種類 (例: 構造最適化) を選びます
4. **入力を生成** を押して、書き出し先のフォルダを指定します
5. 計算ソフトがこの PC に入っていれば **この PC で実行** を押します
   (クラスタで計算する場合は、書き出されたフォルダを転送して `bash submit.sh`)
6. 計算が終わったら **解析** タブでフォルダを指定し、**解析を実行** を押します

![解析の結果](docs/images/tutorial/06_analysis_result.png)

`結合長 (最終構造): O1-H2 0.967 Å` のように出れば成功です。
**画面ごとの手順は [チュートリアル](docs/USAGE.md) に、すべて画像で載せています。**

多数の計算をまとめて回すときは、同じ流れをコマンドラインでも行えます
(`adit-gen --list-samples` から始めます。[チュートリアル](docs/USAGE.md#コマンドラインから))。

## できること

### 構造を作る

プリセット分子、SMILES、構造ファイル、バルク結晶、表面スラブ、溶液・混合物。
**Draw** では、分子を描いて SMILES にできます。

作った構造は 3D で確認できます。視点は `x` `y` `z` の各軸方向と、その中間の `x+y+z` 方向から選べます。
枠の左下には、構造と一緒に回る座標軸が出ます。

### 入力を書き出す

21 の計算コードに対応しています。

![対応表](docs/images/support_matrix.png)

書き出されるファイルは次のとおりです。

| ファイル | 内容 |
|---|---|
| 入力ファイル | 計算コードごとの入力 (`dftb_in.hsd`、`INCAR`、`pw.in` など) |
| `submit.sh` | 計算を実行するスクリプト |
| `README.txt` | 実行方法の手引き (準備するもの、実行の手順、引用すべき文献) |
| `spec.json` | 設定した条件をそのまま保存したもの。読み込めば同じ入力を作り直せます |
| `analyze.py` | 解析用のスクリプト |

手元の PC で直接実行することもできます (アプリの「この PC で実行」、または `adit-gen ... --run`)。

### 結果を図にする

エネルギー・温度、RDF、MSD と拡散係数、状態密度、バンド図、振動数とスペクトル (赤外・ラマン)。
配位数、構造因子 S(q)、水素結合、Voronoi、溶媒接触表面積、自由エネルギー面など、80 以上の解析手法に対応しています。

![解析の図](docs/images/analysis_figures.png)

数値には単位と、その値を読み取った出力ファイルの名前と行番号が付きます。

```
原子の電荷 (Mulliken、detailed.out:18、単位 e): O1 -0.606, H2 +0.294, H3 +0.312
```

図は、線の色・目盛りの向き・グリッド線・枠を指定して保存することもできます。

### 論文やスライドに貼る

構造式・3D 表示・解析の図を、**SVG** (拡大しても粗くならない)、PNG、MOL で書き出せます。
画像をクリップボードにコピーして、例えば Word にそのまま貼ることもできます。

### 計算の条件と結果を書き出す

論文や報告書に転記しやすい形で、計算の記録を書き出せます。書き出されるのは記録に残っている事実だけで、
記録が無い項目は「未記録」と書かれます。

- **方法の記述** (Markdown) — 使った計算コードとその版、汎関数、基底関数、k 点などを文章にしたもの
- **条件の一覧** (CSV) — 複数の計算を 1 枚の表にまとめたもの
- **結果の一覧** (CSV) — 最終エネルギー、平均温度、フレーム数、正常終了したかどうか
- **再現用の一式** (ZIP) — 同じ計算をやり直すのに要るファイルをまとめたもの
- **入力の照合** — 生成したあとに入力ファイルが書き換わっていないかの確認

詳しくは [計算条件の報告](docs/REPORT.md) にあります。

## ドキュメント

| 文書 | 内容 |
|---|---|
| [インストール方法](docs/INSTALL.md) | Windows で初めて使う手順、Linux / macOS、実行ファイルの作り方 |
| [チュートリアル](docs/USAGE.md) | 一括生成、条件を振る、粘度、体積データ、粉末回折 |
| [画面の説明](docs/SCREENS.md) | 構造の作り方、溶媒・磁性、複数の段階に分けた計算 |
| [設定と解析](docs/SETTINGS_AND_ANALYSIS.md) | 環境設定、コードごとの準備、解析の詳細 |
| [対応コードの範囲](docs/NEW_ENGINES.md) | 計算コードごとに、どこまで対応しているか |
| [追加の入口](docs/EXTRA_ENTRY_POINTS.md) | ORCA GOAT / DOCKER、DCDFTBMD、DOCK6、Open Babel |
| [実行ファイルの作り方](docs/WINDOWS_BUILD.md) | Windows の .exe (macOS は [こちら](docs/MACOS_BUILD.md)) |
| [重い解析](docs/HEAVY_ANALYSIS.md) | 大きな軌跡を計算機で処理する |
| [Python API](docs/API.md) | ライブラリとして使う |
| [開発に参加](CONTRIBUTING.md) | 動かし方と設計の方針 |

## ライセンス

ADIT 本体のコードと文書は [MIT](LICENSE) です。

`examples/` と `tests/data/` には、他のプロジェクトから取得したファイルが含まれます
(LAMMPS、CP2K、GROMACS、Quantum ESPRESSO、VASP wiki、DFTB+ レシピ集、cclib、pymatgen)。
これらは元のライセンスのままです。一覧は [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)、
全文は [licenses/](licenses/) にあります。

VASP、Gaussian、ORCA、GAMESS、Q-Chem、GRRM などは各権利者の商標です。
