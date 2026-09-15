# examples/water の出典

このディレクトリの入力は、DFTB+ 公式レシピ集の「First calculation with DFTB+」を
再現したものです。数値・キーワードはすべて公式資料から取り、記憶で補っていません。

## 参照した URL と、何を引用したか

| URL | 引用した内容 |
|---|---|
| https://dftbplus-recipes.readthedocs.io/en/latest/basics/firstcalc.html | 水分子の `dftb_in.hsd` 全文、gen 形式の説明、各ブロックの説明文、`<<<` によるファイル取り込み、実行方法 (`dftb+ \| tee output`) |
| https://dftbplus-recipes.readthedocs.io/en/latest/_downloads/5919f4094cd60c5c70c13b47928442f5/recipes.tar.bz2 | 配布アーカイブ。`recipes/basics/firstcalc/dftb_in.hsd` (Web ページと同一)、`recipes/scripts/get_slakos`、`recipes/slakos/SLAKO_DOWNLOADS`、`recipes/slakos/mio-ext/` (mio-1-1 と tiorg-0-1 へのシンボリックリンク集) |
| https://dftbplus-recipes.readthedocs.io/en/latest/introduction.html | DFTB+ の推奨インストール法 (conda-forge, `dftbplus=*=nompi_*`)、SK ファイルの入手法 (`get_slakos`) |
| https://dftbplus-recipes.readthedocs.io/en/latest/licence.html | レシピ集のライセンス (CC BY-SA 4.0) |
| https://dftb.org/parameters/download.html | パラメータセット一覧、mio の元素 (H-C-N-O-S-P)、「セット間で混在させない」注意 |
| https://dftb.org/parameters/introduction.html | SK ファイルはペア単位で存在すること、角運動量などの文書が各 skf の末尾に付くこと |
| https://github.com/dftbparams/mio (releases v1.1.0) | mio-1-1 の配布物 (`mio-1-1.tar.xz`)、`LICENSE` (CC-BY-SA 4.0)、`README` (著作権者、必須引用文献、含まれる元素) |
| https://github.com/dftbplus/dftbplus/releases/tag/25.1 | DFTB+ 25.1 のソースと `manual.pdf` |
| DFTB+ 25.1 `manual.pdf` | 2.2.2 GenFormat、2.3.1 GeometryOptimisation (Optimiser/Optimizer, MovedAtoms, MaxSteps, OutputPrefix, Convergence/GradElem 既定 1e-4 Hartree/Bohr)、2.4.11 SlaterKosterFiles (明示指定 / Prefix / Type2FileNames / 環境変数 DFTBPLUS_PARAM_DIR)、MaxAngularMomentum、2.5 Options、2.6 Analysis (PrintForces)、2.10 ParserOptions、付録 D gen 形式 |

## 原文からの変更点

1. `Geometry` を `<<< "geometry.gen"` によるファイル取り込みに変えた (同ページで紹介されている書き方)
2. SK ファイルのパスを `../../slakos/mio-ext/` から `../../slakos/mio-1-1/` に変えた
   (`mio-ext` は配布アーカイブ内のリンク集で、O/H の 4 ファイルはすべて `mio-1-1` の実体を指す)
3. 各ブロックに `#` コメントを付けた

## 実行環境 (この機械)

- DFTB+ 25.1 (conda-forge, OpenMP 版 `nompi_h0f3606b_100`)、パーサのバージョン 14
- 実行ファイル: `/home/<user>/miniforge3/envs/dftbplus/bin/dftb+`
- 付属ツール (`gen2xyz`, `xyz2gen`, `gen2cif`) も同じ環境に入っている
- 起動時のヘッダは「DFTB+ development version (commit: a23bfb2)」と表示される
  (conda パッケージの表示。`conda list` 上のバージョンは 25.1)
- Slater-Koster ファイルの置き場所 (予定): `/home/<user>/adit/slakos/mio-1-1/` (`.gitignore` 済み)

## 実行結果 (2026-09-10)

- 実行: `cd examples/water && /home/<user>/miniforge3/envs/dftbplus/bin/dftb+ | tee output.log`。終了コード 0、「Geometry converged」で完走
- 構造ステップ 10 回 (step 0〜9)、壁時計 1.35 秒 (OpenMP 8 スレッド)
- 最終全エネルギー: -4.0779379326 Hartree (-110.9663 eV)
- 最適化後の構造 (`geom.out.gen` から算出): O-H 0.9672 Å (2 本とも)、H-O-H 107.19°
  (初期構造は O-H 1.2701 Å、76.13°。チュートリアルは意図的に歪んだ初期構造から始めている)
- 力の最大成分 (`detailed.out`): 2.0e-5 Hartree/Bohr。収束基準 1e-4 を満たしている
- 警告 2 件。いずれも計算結果には影響しない
  1. `CalculateForces` が `PrintForces` に改名された旨 (パーサのバージョン 12 → 14 の自動変換)
  2. スタックサイズが 8 MB で、大きな系では `ulimit -s unlimited` を推奨する旨
- 生成したファイル: `output.log` (標準出力)、`dftb_pin.hsd` (既定値を全展開した入力)、`detailed.out`、`band.out`、
  `charges.bin`、`geom.out.gen`、`geom.out.xyz`。`output.log` と `dftb_pin.hsd`、`detailed.out`、`geom.out.*` は
  参照用にリポジトリへ入れる。`charges.bin` は `.gitignore` で除外
- skf 末尾の文書で軌道を確認: H-H.skf は `<Shells>1s </Shells>`、O-O.skf は `<Shells>2s 2p </Shells>`。
  `MaxAngularMomentum { O = "p"; H = "s" }` と一致する
