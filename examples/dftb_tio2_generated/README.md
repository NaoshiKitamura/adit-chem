# examples/dftb_tio2_generated

`examples/dftb_tio2`(公式レシピ由来の手書き入力)と同じ計算を、**adit の生成器 (Spec v2、周期系対応) が作った入力**で
実行した結果。V1-2 の検証用。

- 生成の条件: `spec.json`(mio-ext、SCC、一点計算、k 点 4×4×4 シフト 0.5)
- 結果: 完走。全エネルギー -15.6210745499 Hartree。`examples/dftb_tio2/output.log` と一致
- 手書き版との差: Analysis の ProjectStates(状態密度の投影)は生成しない。Options { WriteResultsTag = Yes } と
  PrintForces を書く。ParserVersion 14。SK ファイルは skf/ に複製(リポジトリには入れない)
