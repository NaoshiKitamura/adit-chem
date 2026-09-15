# 配座の候補の実行 — RDKit 2026.03 (ETKDG + MMFF94) → xtb 6.7.1 GFN2 の最適化 (2026-09-12)

## 何の例か

エタノール (SMILES `CCO`) の配座を RDKit の ETKDG で 10 個作り、MMFF94 で最適化し、エネルギーの低い順に全原子の RMSD 0.3 Å 以下を
重複として外した 3 個を、それぞれ xtb (GFN2-xTB) の構造最適化にしたもの。
`adit-gen spec.json out/ --conformers 10 --rmsd 0.3 --conf-all-atoms` (`src/adit/conformers.py`) と同じ処理を API で呼んで生成し、
各ディレクトリで xtb を実行し、`adit-analyze out/ --scan` で表にした。

- 乱数の種は既定の 12345。種 0 では RDKit 2026.03 が 10 個すべて同じ座標を返した (同じ日に確かめた。ADIT は今は止める)
- 閾値 0.3 Å はこの例のために選んだ値 (ADIT は既定を持たない)。anti と gauche の全原子の RMSD は 0.41〜0.43 Å だったので、
  0.5 Å では 1 個にまとまった。水素を除いた RMSD (既定) では、OH の向きだけが違う配座は 0.01 Å 未満になり、重複になる
- CREST の入力 (crest/) は、計算コードが xtb の GFN2 なので書かれている (ADIT は実行しない)

## 結果 (数値を並べるだけ)

| 配座 | MMFF94 の順位 | xtb 最適化後の全エネルギー [eV] |
|---|---|---|
| conf_001 | 1 (MMFF で最も低い) | -309.98849844 |
| conf_002 | 2 | -310.05575138 |
| conf_003 | 3 | -310.05575138 |

MMFF94 と GFN2-xTB でエネルギーの順が逆になっている (conf_001 は MMFF で最も低く、xtb の最適化後は他の 2 つより 67 meV 高い)。
conf_002 と conf_003 の xtb のエネルギーは 8 桁まで同じ (鏡像の関係と推測。確かめていない)。

## ファイル

| ファイル | 中身 |
|---|---|
| `conformers.json` | 10 個すべての MMFF のエネルギー、残したか、重複の相手と RMSD |
| `conformers.sdf` | 残した 3 個 |
| `conf_001/ … conf_003/` | 各配座の xtb の入力と出力 |
| `crest/` | CREST の入力 (struct.xyz、run_crest.sh) |
| `scan.json`、`scan_energies.csv`、`scan_energy.png` | 解析 (adit-analyze --scan) の結果 |
