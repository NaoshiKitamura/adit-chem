# examples/vasp_h2o_generated —— 生成器が作った VASP の入力 (wiki の H2O 例に相当)

`examples/vasp_h2o`(wiki の原文)と同じ設定を Spec に写し、adit の生成器 (`codes/vasp.py`) で作ったもの。
**POTCAR は入っていない。**`potcar.spec` と `make_potcar.sh` が代わりに入る。
この機械には POTCAR 庫が無いので、TITEL / ZVAL は「未確認」。クラスタでの実走は人が行う (未実施)。

## 原文との差分と理由

| 項目 | wiki の原文 | 生成物 | 理由 |
|---|---|---|---|
| POSCAR の形式 | 元素名の行が無い旧形式、座標にスケール 0.52918 | 元素名の行あり (VASP 5 形式)、スケール 1 でセルと座標に 0.52918 を掛けた値 | ASE は旧形式を読めない。数値は同じ |
| 座標の書き方 | cart (直交) | Direct (分数) | ASE の書き出しの既定。等価 |
| Selective dynamics | O は F F F、H は T T F (z を止める) | O は F F F、H は T T T | v1 の固定は原子単位 (fixed_atoms)。軸ごとの固定は未対応 |
| ENMAX = 400 | 旧キー | ENCUT = 400 | 現在のキー (wiki の ENCUT ページ)。値は同じ |
| IBRION = 1, NFREE = 2 | DIIS | IBRION = 2 (共役勾配) | 生成器の既定。IBRION は extra_incar で上書きできる |
| ALGO / EDIFF / NELM / LREAL / ISPIN | 書かない (VASP の既定) | 明示 (Normal / 1e-4 / 60 / Auto / 1) | Spec の値を必ず書く方針 |
| ISIF | 書かない (既定 2) | ISIF = 2 | 同上 |
| KPOINTS | Monkhorst Pack 1 1 1 | Gamma 1 1 1 | Γ 点のみは Gamma 指定 (同じ点) |
| POTCAR | (wiki は前提として持っている) | 無し。potcar.spec (O → O、H → H) と make_potcar.sh | 配布できないため |

## クラスタでの実走 (2026-09-10、VASP 6.4.2、人が投入)

生成物をそのまま転送し、`make_potcar.sh` が POTCAR (`PAW_PBE O 08Apr2002`、`PAW_PBE H 15Jun2001`) を組み立てて実行。
5 ステップで「reached required accuracy」(収束)。最終エネルギー F = -14.2226 eV。警告・エラー無し。
wiki の VASP 5 世代の書き方 (ENMAX) を ENCUT に直したものが 6.4.2 で通った。CPU 時間 5.4 秒 (32 コア)。
