# 試験に使う実物のファイルの出典

すべて、書式を**実物で**確かめるために置いてあります。

| ファイル | 出典 | ライセンス | いつ・何を確かめたか |
|---|---|---|---|
| `si.proj.projwfc_up` | 手元で Quantum ESPRESSO 7.x の projwfc.x を Si 2 原子で実行 | — (自分で作った) | 2026-09-13。filproj の並び |
| `epsr_si.dat` / `epsi_si.dat` / `eels_si.dat` | 手元で QE の epsilon.x を Si (ノルム保存の擬ポテンシャル) で実行 | — (自分で作った) | 2026-09-13。列の並びと、-Im(1/eps) が QE 自身の値と一致すること |
| `bader_ACF.dat` | 手元で bader 1.0.5 を、電子数 6 と 2 のガウス関数を置いた cube で実行 | — (自分で作った) | 2026-09-13。ACF.dat の列と、分けられた電子数 (5.9999 / 1.9987) |
| `PROCAR.simple` / `PROCAR.new_format_5.4.4.gz` | [pymatgen](https://github.com/materialsproject/pymatgen) の `test-files/io/vasp/outputs/` | MIT | 2026-09-13。素の形式と lm 分解 + 位相 (VASP 5.4.4)。読んだ値は pymatgen の `Procar` と一致 |
| `WAVEDER.gz` | [pymatgen](https://github.com/materialsproject/pymatgen) の `test-files/io/vasp/outputs/WAVEDER` を gzip したもの | MIT | 2026-09-13。Fortran の書式なしレコードの並び。読んだ配列は pymatgen の `Waveder` と完全一致 |
| `gaussian_dvb_raman.out.gz` / `gamess_dvb_ir.out.gz` / `qchem_dvb_raman.out.gz` / `orca_dvb_raman.out.gz` | [cclib](https://github.com/cclib/cclib) の `data/` (Gaussian 16、GAMESS-US 2018、Q-Chem 5.4、ORCA 6.0 の実際の出力) | BSD-3 | 2026-09-13。エネルギー・構造・振動数・赤外の強度・**ラマン活性**・Mulliken 電荷。読んだ値は cclib 自身の読み取りと一致 (GAMESS の赤外だけ単位の換算が要る) |
| `water_hessian.out` | DFTB+ の実行 (2026-09-10) | — (自分で作った) | hessian.out の並び |

**開発機に VASP は無いので、VASP の出力は公開されている本物のファイルで確かめています。**

## リポジトリに置いていないが、実物で確かめたもの

ライセンスが ADIT (MIT) と合わないので**置いていません**。書式は 2026-09-13 に実物で確かめました。

| 何 | 出典 | ライセンス | 試験の実行方法 |
|---|---|---|---|
| OpenMX の `.out` | OpenMX 付属の `work/input_example/Methane.out`・`H2O.out` ([FermiQ/openmx-square](https://github.com/FermiQ/openmx-square) で公開) | GPL-3 | `ADIT_OPENMX_OUT=<file> pytest tests/test_readers_openmx.py` |
| VASP の `vasprun.xml` + `WAVEDER` (誘電関数の突き合わせ) | pymatgen の `fixtures/reproduce_eps` | MIT だが 2.7 MB と大きい | 手元でだけ実施 (結果は `analysis/waveder.py` の説明に記録) |
