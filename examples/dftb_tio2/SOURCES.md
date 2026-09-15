# examples/dftb_tio2 の出典 (周期系 DFTB+ の基準例)

公式レシピ集「Band structure, DOS and PDOS」の第 1 段(アナターゼ TiO2 の自己無撞着電荷を、収束した k 点で求める)を再現した。

| 項目 | 内容 |
|---|---|
| URL | https://dftbplus-recipes.readthedocs.io/en/latest/basics/bandstruct.html |
| 原本 | 配布アーカイブ recipes.tar.bz2 内 `recipes/basics/bandstruct/1_density/dftb_in.hsd`(レシピ集は CC BY-SA 4.0) |
| SK セット | mio-1-1(O-O)と tiorg-0-1(Ti-Ti, Ti-O, O-Ti)。どちらも CC BY-SA 4.0(dftbparams、2024-12-18 の配布)。tiorg は「Requires: mio」と dftb.org に明記された mio の拡張で、混在が前提 |
| 置き場所 | `slakos/mio-1-1/`、`slakos/tiorg-0-1/`、レシピ集と同じ構成のリンク集 `slakos/mio-ext/`(いずれも .gitignore) |
| 角運動量の根拠 | tiorg-0-1/Ti-Ti.skf 末尾 `<Shells>3d 4s 4p</Shells>` → Ti = "d"。mio-1-1/O-O.skf `<Shells>2s 2p</Shells>` → O = "p" |

## 原文からの変更点

1. 構造を `<<< "geometry.gen"` で取り込む(中身は原文と同一)
2. SK ファイルの Prefix を `../../slakos/mio-ext/` にした
3. `#` コメント

## 実行結果 (2026-09-10、DFTB+ 25.1、この機械)

- 終了コード 0。周期境界 Yes、k 点 32 個(4×4×4、シフト 0.5)
- SCC 反復 5 回で収束。全エネルギー -15.6210745499 Hartree(-425.0711 eV)
- 警告 3 件: パーサのバージョン 12→14 の変換、周期系での双極子は定義されない旨、スタックサイズ。いずれも結果に影響しない
- 生成したファイル: output.log、dftb_pin.hsd、detailed.out、band.out、dos_ti.{1,2,3}.out、dos_o.{1,2}.out(`charges.bin` は .gitignore)
- レシピ集は続けて `dp_dos` で状態密度を出すが、ここでは基準として SCC 計算までを置く
