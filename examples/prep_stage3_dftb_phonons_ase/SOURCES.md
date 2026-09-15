# フォノン (有限変位、phonopy なし = ASE の Phonons) の実行 — DFTB+ 25.1、mio-1-1 (2026-09-12)

## 何の例か

ダイヤモンドの基本セル (C 2 原子、ASE の `bulk("C", "diamond", a=3.567)`、格子は緩和していない) から 2×2×2 の超格子 (16 原子) を作り、
ASE の Phonons と同じ変位 (参照セルの各原子を ±x ±y ±z に 0.01 Å。ASE の既定) の 12 個を、それぞれ DFTB+ の一点計算
(k 点 4×4×4、SCC) にしたもの。`adit-gen spec.json out/ --phonons 2x2x2 --phonon-backend ase --phonon-dos-mesh 10x10x10 --phonon-dos-width 0.5`
(`src/adit/phonon_setup.py`) と同じ処理を API で呼んで生成し、実行したあと `python phonon_collect.py` で集めた。

- 集めるときは ASE の Phonons (read の既定: Frederiksen、音響の和の規則) で力の定数を作り、ASE の標準の経路で振動数を出して、
  phonopy の band.yaml と同じ鍵で書く (先頭に「phonopy が書いたものではない」と注がある)
- 状態密度は q 点 10×10×10、ガウスの幅 0.5 THz (この例で選んだ値。ADIT は既定を持たない)
- 解析の役の読み取り (`src/adit/analysis/phonons.py` の analyze_phonopy) で band.yaml と total_dos.dat を読めることを確かめた

## 結果 (数値を並べるだけ。安定かどうかは判断しない)

経路 GXWKGLUWLK,UX、振動数 −4.275〜44.68 THz、負の値 (虚振動数) 24 個。
