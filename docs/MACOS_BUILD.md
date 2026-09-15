# macOS の実行ファイル (.app) を作る (2026-09-14)

**開発機に Mac が無いので、この手順はまだ実機で通していません。**
作り方の設定と CI の手順だけ用意してあります。**最初に作った人が、下の「確認」を通してください。**

## 作る

GitHub の Actions から手で動かします。

1. リポジトリの **Actions** → **macos-app** → **Run workflow**
2. Apple Silicon (arm64) と Intel (x86_64) の 2 つが並行で走ります
3. 終わると成果物 (artifact) に `adit-macos-arm64` / `adit-macos-x86_64` が出ます。中身は
   - `ADIT-<arch>.zip` … 二重クリックで開く `ADIT.app` (`ditto` でまとめたもの。Finder の権限が保たれます)
   - `dist/adit/` … 画面を使わない人向けの一式 (`adit-cli` が入っています)

手元の Mac で作るなら:

```bash
python -m pip install -e ".[gui,smiles,analysis]" pyinstaller
pyinstaller packaging/adit.spec --noconfirm
open dist/ADIT.app          # 画面
./dist/adit/adit-cli gen --list-samples   # コマンド
```

## 署名と公証をしていません

Apple の開発者登録 (有料) が要るため、**署名 (codesign) も公証 (notarization) もしていません。**
そのため、受け取った人が初めて開くときは次のどちらかが要ります。

- Finder で `ADIT.app` を**右クリック → 開く** → 出てくる確認で「開く」
- または `xattr -dr com.apple.quarantine /Applications/ADIT.app`

**この手順を配布物の案内に必ず書いてください。**書かないと「壊れているから開けません」と表示され、
利用者は原因が分かりません。

署名するときは、Apple Developer Program に登録したうえで

```bash
codesign --deep --force --options runtime --sign "Developer ID Application: <名前> (<チーム ID>)" dist/ADIT.app
xcrun notarytool submit dist/ADIT-arm64.zip --apple-id <id> --team-id <team> --password <app 用パスワード> --wait
xcrun stapler staple dist/ADIT.app
```

## 確認 (実機で最初に通すこと)

Windows の手順 (`docs/WINDOWS_BUILD.md`) と同じ 7 点です。**通ったものに印を付けて、この文書を更新してください。**

1. `ADIT.app` を二重クリックして画面が出る (日本語が豆腐 □ にならない)
2. 構造を作り、入力を生成できる (`adit-cli gen --sample water_generated` → 生成 → `README.txt` がある)
3. 解析が図まで出る (`adit-cli analyze <ディレクトリ>`)
4. Draw が開き、描いた分子が SMILES になる (RDKit が同梱されているか)
5. ウェブ版が開く (`adit-cli web` → ブラウザで 127.0.0.1:8765)
6. 3D 表示が回る (画面の「構造」タブと、ウェブ版の「構造 (3D)」)
7. 別の Mac (作った機械ではない Mac) に写して、上の 1〜6 が通る

**7 が最も大事です。**作った機械では動いて、他の機械では足りないものがあって動かない、が起きます。

## Intel と Apple Silicon

CI は 2 つを別々に作ります (`macos-13` が Intel、`macos-14` が Apple Silicon)。
1 つにまとめた universal2 は、PySide6 と RDKit の配布が両対応の wheel を出していないと作れないので、**していません**。
配るときは、相手の Mac に合うほうを渡してください (Apple メニュー → この Mac について で分かります)。
