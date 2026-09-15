# examples/lammps_cu —— LAMMPS の配布物に付く Cu の EAM ポテンシャル

`examples/lammps_cu_nvt_generated` の入力に使ったもの。ADIT はポテンシャルを作らない・選ばない (利用者が用意したファイルを写すだけ)。

| ファイル | 出典 | ライセンス |
|---|---|---|
| `Cu_u3.eam` | LAMMPS の配布物の `potentials/Cu_u3.eam` (https://raw.githubusercontent.com/lammps/lammps/stable_22Jul2025_update5/potentials/Cu_u3.eam、2026-09-12 取得)。sha256 `3436c491a4c75ea8b7141adbc6ee382a118f5fdb47f609c2a660fc1eb772599f` | LAMMPS と同じ GPL-2.0 (https://docs.lammps.org/Intro_opensource.html) |

ファイルの 1 行目: `UNITS: metal`、`CITATION: Foiles et al, Phys Rev B, 33, 7983 (1986)`。使うときは Foiles らの論文を引用する。
conda-forge の `lammps` パッケージ (22 Jul 2025 update 5) には potentials/ が入っていなかったので、GitHub の同じバージョンのタグから取った。
