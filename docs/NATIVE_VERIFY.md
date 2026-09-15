# 生成入力の照合 / Generated-input verification

`adit.native_verify.verify_generated_bundle(project_dir)` は `spec.json` と実際の入力を読み、`preserved` (保持)、`mismatched` (不一致)、`unverifiable` (検証不能)を返す。`report()` は JSON 化できる。読み取り専用で、入力の修正・計算の実行はしない。

CLI では `adit-convert verify 生成ディレクトリ` を使う。対応項目の読み込みが成立し、不一致がなければ終了コードは 0。不一致・未対応入力・入力不足は 1。`--report 新しいファイル.json` を付けると詳細を保存するが、既存ファイルや生成ディレクトリ内には書かない。終了コード 0 は**検査対象に限った通過**であり、`unverifiable` が残る場合もある。結果を計算の同等性や実行可能性と解釈しないこと。

The API reads `spec.json` and the actual native inputs. Its result separates preserved, mismatched, and unverifiable fields and provides a JSON-serializable `report()`. It does not edit files or execute calculations.

Use `adit-convert verify GENERATED_DIR` from the CLI. The exit status is 0 only when supported fields could be re-imported and no mismatch was found; missing or unsupported inputs and mismatches return 1. Add `--report NEW_FILE.json` to save details outside the generated bundle without overwriting an existing file. Exit status 0 means **only that the mapped checks passed**: `unverifiable` entries may remain. It does not establish equivalence or executability.

対応範囲は [入力読み込み](NATIVE_IMPORT.md) と同じ。元入力で明示された対応項目だけを比べる。Spec の既定値が一致するだけでは「保持」としない。擬ポテンシャルの内容、力場の正しさ、実行条件、計算全体の同等性は保証しない。

The scope follows the [native importer](NATIVE_IMPORT.md). Only explicitly mapped native fields are compared. Equal inferred defaults do not count as verified preservation. Pseudopotential contents, force-field correctness, runtime configuration, and whole-calculation equivalence are not established.

VASP の原子は生成器と同じ元素ごとの順に並べて比べる。LAMMPS は元 Spec が外部 data を参照する場合、およびセル回転を伴う場合、原子座標を検証不能とする。構造の比較は Å で絶対誤差 1e-8、他の数値は相対誤差 1e-8・絶対誤差 1e-14。整数・文字列・真偽値は一致を要求する。LAMMPS の時間は読み込み時に fs へ換算済み。k 点は実際のメッシュとシフトを比較する。

複数段階の計算では、前段階入力の計算種別を Spec 全体のタスクと直接比較しない。QE の擬ポテンシャル名が生成時の設定から補われ、元 Spec に指定がない場合も、不一致ではなく検証不能とする。

VASP atoms are grouped by element exactly as in the generator. LAMMPS coordinates are unverifiable if the source Spec refers to external data or requires cell rotation. Coordinate/cell tolerance is absolute 1e-8 Å; other numeric comparisons use relative 1e-8 and absolute 1e-14. Integers, strings and booleans must match exactly. LAMMPS time is already converted to fs by the importer. K points are compared as resolved mesh and shift.

For multi-stage calculations, the task of a preparatory input is not compared directly with the overall spec task. If QE pseudopotential filenames were supplied by generation configuration rather than the source spec, they are marked unverifiable instead of mismatched.
