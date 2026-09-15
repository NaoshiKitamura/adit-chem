# 計算コード間の条件監査 / Cross-code settings audit

`adit-convert calculation` は、従来の `conversion.json` に `field_audit` を追加します。
これは値の**出典と適用状況**の記録であり、異なる計算コードが同じ物理モデル・
数値解を与えるという認証ではありません。

`adit-convert calculation` adds `field_audit` to `conversion.json`. It records
the **origin and input applicability** of settings, not a certification that
different engines implement the same physical model or produce the same result.

| status | 日本語 | English |
| --- | --- | --- |
| `preserved` | 元の Spec の値を保持 | Value preserved from the source spec |
| `changed_by_request` | 明示指定で雛形の値に変更 | Changed to a target-template value at the user's request |
| `omitted_by_request` | 明示指定で除外 | Omitted at the user's request |
| `retained_in_spec_not_input` | Spec に残るが生成入力には適用されない | Retained in the spec but not applied to generated input |
| `not_used_by_task` | この計算種類では使わない | Not used by this task type |
| `from_target_template` | 変換せず雛形から取得 | Taken from the target template without translation |
| `not_translated` | コード固有の方法を対応付けない | Engine-specific method settings are not mapped |

座標・原子記号・セルなどの大きな配列の値は `field_audit` に複写しません。
正確な値は生成先の `spec.json` と構造ファイルで確認できます。
入力に書かれていない暗黙の既定値、力場と擬ポテンシャルの物理的な同等性、
熱浴アルゴリズムの同等性は、この記録では保証しません。

Large arrays such as coordinates, symbols, and cell vectors are not copied into
`field_audit`; inspect the generated `spec.json` and structure files for their
exact values. The audit does not guarantee implicit engine defaults, physical
equivalence of force fields or pseudopotentials, or equivalence of thermostat
algorithms.

## 計算結果の機械的点検

```text
adit-analyze run_lammps --audit-with run_vasp --audit-kind msd
adit-analyze run_lammps --audit-with run_vasp --audit-kind energy
```

このコマンドは点検結果を標準出力へ示すだけで、MSD やエネルギーの図は作りません。`--msd` など通常の解析オプションと同時には指定できません。解析図が必要なら各計算を別々に解析してください。

This command reports the audit on standard output only; it does not produce MSD or energy plots. It cannot be combined with ordinary analysis options such as `--msd`. Analyze each run separately when you need figures.

MSD の点検では、元素記号の列・周期境界・セル・軌跡・フレーム間隔を確認します。同じ元素どうしの原子 ID は記号だけでは区別できないため、初期座標も周期境界を考慮して照合します。異なる場合は「同じ初期構造からの比較」の点検を通しません。異なる初期構造を用いる統計比較が妥当かどうかは判定しません。
エネルギーの点検では、同じ組成・周期境界・セルで、全系の eV として読めるかを確認します。軌跡の有無やフレーム数・原子順はエネルギー用の停止条件ではありません。出力は読み取り専用で、
失敗した点検は終了状態 1 を返します。異なる計算法のエネルギーや MSD を
**科学的に直接比較してよいか**は判定しません。
異なるコードのエネルギーでは、運動・ポテンシャル・電子の寄与など、出力が含む内訳を照合していないため、直接比較の点検は通しません。

For MSD, the command checks the element-symbol sequence, periodic boundaries,
cell geometry, trajectories, and frame spacing. Symbols cannot distinguish
same-element atom identities, so initial positions are matched with periodic
boundaries accounted for. A mismatch fails the check for runs starting from the
same structure; this does not judge statistical comparisons from different
initial structures. For energy, it checks matching composition, periodic boundaries, and cells, and whether energies are available in eV for the whole simulated system; missing
trajectories, frame-count differences, and atom order do not block this mode.
It does not write files and exits with status 1 if a mechanical check fails.
It does **not** decide whether the two methods' energies or MSDs are
scientifically comparable.
Direct energy comparison across different engines fails the check because the
contributions included in their reported energies have not been matched.
