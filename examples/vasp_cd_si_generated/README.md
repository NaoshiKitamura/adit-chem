# examples/vasp_cd_si_generated —— 生成器が作った VASP の入力 (wiki の Cd Si relaxation 例に相当)

`examples/vasp_cd_si`(wiki の原文)と同じ設定を Spec に写し、adit の生成器で作ったもの。POTCAR は入っていない。
クラスタでの実走は人が行う (未実施)。

## 原文との差分と理由

| 項目 | wiki の原文 | 生成物 | 理由 |
|---|---|---|---|
| POSCAR | 元素名の行が無い旧形式、スケール 5.5 | 元素名の行あり、スケール 1 で格子ベクトルに 5.5 を掛けた値 | ASE は旧形式を読めない。数値は同じ |
| ISTART = 0, ICHARG = 2 | INCAR に明示 | extra_incar で同じ値を書く | GUI に無いキーの逃げ道として |
| ALGO / EDIFF / NELM / LREAL / ISPIN / PREC | 書かない | 明示 | Spec の値を必ず書く方針 |
| KPOINTS | Monkhorst Pack 11 11 11 | 同じ | |
| POTCAR | (前提) | 無し。potcar.spec (Si → Si) と make_potcar.sh | 配布できないため |

## クラスタでの実走 (2026-09-10、VASP 6.4.2、人が投入)

生成物をそのまま転送し、`make_potcar.sh` が POTCAR (`PAW_PBE Si 05Jan2001`) を組み立てて実行。
NSW = 10 のとおり 10 ステップで終了 (wiki の例と同じ止め方。EDIFFG = -0.0001 は 10 ステップでは満たさない)。
最終エネルギー F = -10.8244 eV。ずらした原子の z は 0.130 → 0.1275 (原文は 4.81250 Å ≈ 0.1275 に相当)。警告・エラー無し。
CPU 時間 138 秒 (32 コア、11×11×11 の k 点)。
