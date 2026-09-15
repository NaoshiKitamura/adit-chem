# Windows の実行ファイル (.exe) を作る (2026-09-13)

「ダブルクリックで起動する ADIT」を作るための手順。**Windows の .exe は Windows 上でしか作れません**
(PyInstaller は他の OS 向けに作り分けられない)。作る場所は次のどちらかです。

1. **Windows の PC で作る** —— 手元に Windows があるならこれが一番早い
2. **GitHub Actions の windows-latest で作る** —— `.github/workflows/windows-exe.yml` を動かすと、
   出来上がった一式が成果物 (artifact) として downloads に出る。リポジトリを GitHub へ push してある場合だけ

作りかたの設定は `packaging/adit.spec`、実行ファイルの入口は `packaging/launch.py` です。

## 1 Windows の PC で作る

PowerShell で、リポジトリを置いた場所に移動してから:

```powershell
py -3.12 -m venv build-env
build-env\Scripts\activate
pip install -e ".[gui,smiles,analysis]" pyinstaller
pyinstaller packaging\adit.spec --noconfirm
```

`dist\adit\` に**実行ファイルが 2 つ**出来ます。フォルダごと配ってください (中のファイルが要ります)。

| ファイル | 使いみち |
|---|---|
| `ADIT.exe` | 画面 (デスクトップ版)。黒い画面が出ない代わりに、**標準出力を持たないので CLI には使えません** |
| `adit-cli.exe` | CLI。`adit-cli.exe gen ...` / `analyze` / `report` / `convert` / `web` |

2 つに分けるのは Windows の決まりのためです。画面用の実行ファイル (GUI サブシステム) には標準出力が無く、
**1 つにすると CLI の表示が何も出ません** (2026-09-13 に実際に作って確かめました)。
1 つの .exe にまとめたいときは `packaging/adit.spec` の `ONEFILE = False` を `True` に変えます
(起動のたびに一時フォルダへ展開するので、開くまで数秒かかります)。

## 2 出来た実行ファイルの確認 (作った人が必ず通す)

```powershell
dist\adit\ADIT.exe                             # 画面が開く。日本語が □ になっていないか
dist\adit\adit-cli.exe gen --list-samples      # サンプルの一覧が出るか (同梱の examples を読めているか)
dist\adit\adit-cli.exe gen --sample water_generated mine.json
dist\adit\adit-cli.exe gen mine.json out\run1  # 入力・submit.sh・README.txt が書けるか
dist\adit\adit-cli.exe analyze out\run1        # 実行していないディレクトリでは理由を言って止まるか (終了コード 2)
dist\adit\adit-cli.exe web                     # ブラウザで http://127.0.0.1:8765 が開くか
```

**画面の日本語が □ (豆腐) になるとき**は、フォントが同梱されていません。conda の環境で
`conda install -c conda-forge font-ttf-noto-cjk` を入れてから作り直すか、`ADIT_FONT_DIR` に
`NotoSansCJKjp-VF.ttf` のあるフォルダを指定して作り直します。

## 3 同梱するもの・しないもの

| 同梱する | 理由 |
|---|---|
| `adit/scripts/templates/*.j2`、`adit/web/templates/*.html` | submit.sh と画面の雛形 |
| `examples/*/spec.json` | `gen --list-samples` / `--sample` が読む |
| `fonts/NotoSansCJKjp-VF.ttf` (あれば) | 画面と図の日本語 |

| 同梱しない | 理由 |
|---|---|
| DFTB+・xtb・Quantum ESPRESSO などの計算ソフト | 配布条件が別。**Windows では実行ボタンが無効**なので、そもそも要らない |
| Slater-Koster セット、擬ポテンシャル、POTCAR | ライセンス上、ADIT が配ってはいけない |

## 4 分かっている制限

- **Windows では計算を実行できません。**実行ボタンは押せず、「生成した入力を Linux のサーバーに転送して使います」
  と出ます (`gui/main_window.py`)。exe で出来るのは入力の生成と、手元にある出力の解析です
- **大きさは 300〜500 MB** (PySide6 と matplotlib と SciPy を同梱するため)。`ONEFILE = True` でも縮みません
- **署名していません。**SmartScreen が「発行元不明」と警告します。配るなら署名するか、受け取る人に
  「詳細情報 → 実行」を案内してください
- **RDKit を入れた環境で作ると SMILES から構造を作れます**。入れずに作ると、その欄だけが使えません
- この設定は **Linux で実際に作って、CLI が動くところまで確かめました** (2026-09-13)。
  確かめたのは `gen --list-samples` / `--sample` / 入力の生成 / `analyze` (未実行のディレクトリで終了コード 2) /
  `report` / `convert verify` の 6 つと、**画面が起動して窓を作るところまで** (`QT_QPA_PLATFORM=offscreen`)。
  **Windows での生成したファイルは未確認**です (Windows の実行ファイルは Windows 上でしか作れないため)。
  上の「2 出来た実行ファイルの確認」を必ず通してください
- 作ってみて分かったこと 2 つ (どちらも spec に入れてあります):
  1. **ASE は形式ごとのモジュールを名前で動的に読み込む**ので、`hiddenimports` に `ase.io` を入れないと
     `.gen` の書き出しが `UnknownFileTypeError` で落ちる
  2. Linux では **conda の `libOpenGL.so.0` を同梱しないと画面が起動しない** (Windows の PySide6 は
     OpenGL の DLL を自分で持っているので、この処理は Linux でだけ働く)
  3. **画面用の実行ファイルは標準出力を持たない**ので、CLI 用に console 版 (`adit-cli.exe`) を別に作る
  4. 窓の大きさの既定 (1800x1000) が **1536x864 の画面からはみ出した**ので、画面の 95 % に収めるようにした
     (`gui/main_window.py`)
