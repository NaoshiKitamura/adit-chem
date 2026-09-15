# examples/water_generated

`examples/water`(公式チュートリアル由来の手書き入力)と同じ計算を、
**adit の生成器 (`codes/dftbplus.py`) が作った入力**で実行した結果。フェーズ 3 の検証用。

- 生成の条件: `spec.json`(mio-1-1、SCC、Rational 最適化、MaxSteps 100、GradElem 1e-4)
- 生成したファイル: `dftb_in.hsd`, `geometry.gen`(`skf/` は CC BY-SA 4.0 のデータなのでリポジトリには入れない)
- 実行結果: `output.log`, `dftb_pin.hsd`, `detailed.out`, `geom.out.gen`, `results.tag`
- 結果: 完走(Geometry converged、10 ステップ)。全エネルギー -4.0779379326 Hartree。
  最終座標は `examples/water/geom.out.gen` と同一


## 2026-09-10 (Spec v2) の更新

力の収束基準の単位を eV/Å に統一したので、`Convergence { GradElem [eV/AA] = 0.00514221 }` と単位付きで書くようになった
(1e-4 Hartree/Bohr を換算した値。DFTB+ は単位修飾子を受け付けるので換算は DFTB+ 側で行われる)。
結果 (全エネルギー -4.0779379326 Hartree、最終座標) は変わらない。`spec.json` は version 2。
