# フォノン (有限変位、phonopy 4.5.0) の実行 — DFTB+ 25.1、mio-1-1 (2026-09-12)

## 何の例か

`prep_stage3_dftb_phonons_ase` と同じダイヤモンドの基本セル (C 2 原子、a = 3.567 Å、格子は緩和していない)、同じ 2×2×2 の超格子と
DFTB+ の条件で、変位を phonopy で作ったもの。phonopy は対称性で変位を減らすので、計算は 1 個 (disp-001) になった。
`adit-gen spec.json out/ --phonons 2x2x2 --phonon-backend phonopy --phonon-dos-mesh 10x10x10` (`src/adit/phonon_setup.py`) と同じ処理を
API で呼んで生成し、実行したあと `python phonon_collect.py` で集めた。

- phonopy は ADIT の依存ではない。この実行では phonopy 4.5.0 (PyPI、BSD-3-Clause) を開発機の一時的な場所に入れて使った
  (依存として phonors・symfc・PyYAML・h5py・spglib などを宣言している。`pip install phonopy` ならまとめて入る)
- 基本セルの選び方と変位の大きさは phonopy の既定。状態密度は q 点 10×10×10 (この例で選んだ値) で、phonopy の既定のテトラヘドロン法。
  phonopy は「偶数のメッシュの半分ずらしが基本セルの点群を保たないので、対称性の削減を切った」と警告した
- phonopy の既定のメッシュ (この格子で 49×49×49) の状態密度は、同じ日に 1.5 GB のメモリの上限を超えて止められた。ADIT は既定の
  メッシュで状態密度を作らない (メッシュを与えたときだけ)
- 解析の役の読み取り (`src/adit/analysis/phonons.py`) で band.yaml と total_dos.dat を読めることを確かめた

## 結果 (数値を並べるだけ。安定かどうかは判断しない)

経路 GXWKGLUWLK,UX、振動数 0.0003847〜41.74 THz、負の値 0 個。
同じ DFTB+ の条件で ASE の Phonons (phonopy なし) の経路で集めた結果 (−4.275〜44.68 THz、負の値 24 個) とは一致しない。
違いの原因は確かめていない (ASE の Phonons は対称性を使わず、小さな超格子の端の像の扱いが phonopy と違う、と推測)。
