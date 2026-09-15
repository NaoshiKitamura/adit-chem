# examples/gromacs_spce —— GROMACS に同梱の SPC/E 水の箱

`examples/gromacs_spce_em_generated` (エネルギー最小化) と `examples/gromacs_spce_nvt_generated` (その続きの NVT) の入力に使ったもの。
ADIT はトポロジーを作らない (外部で作ったものを受け取る)。ここでは GROMACS に付いてくる水のファイルを使った。

| ファイル | 出典 | ライセンス |
|---|---|---|
| `conf.gro` | GROMACS 2026.3 (conda-forge `gromacs`) の `share/gromacs/top/spc216.gro` をそのまま写したもの (水 216 分子、648 原子、立方体の箱 1.86206 nm) | GROMACS と同じ LGPL-2.1 (https://www.gromacs.org/about.html) |
| `topol.top` | 2026-09-12 に手で書いた 8 行。GROMACS 同梱の `oplsaa.ff/forcefield.itp` と `oplsaa.ff/spce.itp` を `#include` し、`SOL 216` を並べるだけ | 同梱の力場を読むだけなので、力場のファイル自体はここに無い (grompp が GROMACS の置き場所から読む) |

`spce.itp` は `#ifndef FLEXIBLE` で SETTLE (剛体の水) を使う。SPC/E の文献: Berendsen, Grigera, Straatsma, J. Phys. Chem. 91, 6269 (1987)。
