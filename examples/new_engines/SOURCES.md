# 追加コードの入力仕様 / Input references for additional engines

ADIT はこれらの文書の入力形式・キーワード・起動方法に合わせて、限定した計算種類だけを生成する。下の書式例は化学的な推奨条件ではない。実行可能な本体と必要なパラメータがこの開発環境に揃っていないため、7コードの実走は未確認。

ADIT follows these documents for input syntax, keywords, and launch commands within the explicitly limited task subsets. Example values are not chemical recommendations. Live runs for the seven codes have not been verified because the required executables and parameters are not all available in this development environment.

| Code | Official/vendor documentation used |
|---|---|
| Gaussian | [Gaussian 16 input overview (Japanese distributor)](https://www.conflex.co.jp/gaussian_support/input.php) — route, title, charge/multiplicity, Cartesian coordinates; [Gaussian license information](https://gaussian.com/wp-content/uploads/dl/us_com.pdf) |
| US GAMESS | [Introduction and $CONTRL/$BASIS/$DATA example](https://www.msg.chem.iastate.edu/gamess/GAMESS_Manual/intro.pdf), [input description](https://www.msg.chem.iastate.edu/GAMESS/GAMESS_Manual/input.pdf), [rungms](https://www.msg.chem.iastate.edu/gamess/GAMESS_Manual/prog.pdf), [distribution terms](https://www.msg.chem.iastate.edu/gamess/download.html) |
| Q-Chem | [Input-file overview and $molecule/$rem](https://manual.q-chem.com/6.0/Ch3.S2.SS1.html), [command-line execution](https://manual.q-chem.com/6.0/Ch3.S6.SS1.html), [license setup](https://manual.q-chem.com/6.0/Ch2.S1.SS1.html) |
| GRRM17 | [Input format](https://afir.sci.hokudai.ac.jp/manual/grrm17/grrm17_12.html), [execution and Gaussian linkage](https://afir.sci.hokudai.ac.jp/manual/grrm17/grrm17_9.html), [MIN](https://afir.sci.hokudai.ac.jp/manual/grrm17/conventional-calculations/grrm17_10.html), [FREQ](https://afir.sci.hokudai.ac.jp/manual/grrm17/conventional-calculations/grrm17_11.html) |
| OpenMX 4.0 | [Input keywords](https://openmx-square.org/openmx_man4.0/s8_2_keywords.html), [PAO/VPS and valence](https://openmx-square.org/openmx_man4.0/s13_1_valence-pseudo.html) |
| Amber | [Current reference manuals](https://ambermd.org/Manuals.php), [official sander minimization example and command](https://ambermd.org/tutorials/basic/tutorial5/index.php) |
| NAMD 3.0 | [Configuration-file format](https://www.ks.uiuc.edu/Research/namd/3.0/ug/node9.html), [configuration parameters](https://www.ks.uiuc.edu/Research/namd/3.0/ug/node12.html), [sample NVE configuration](https://www.ks.uiuc.edu/Research/namd/3.0/ug/node91.html) |
