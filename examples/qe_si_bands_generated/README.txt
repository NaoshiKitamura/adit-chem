adit 0.0.1 が生成した Quantum ESPRESSO (pw.x) の計算ディレクトリ (2026-09-10T09:23:22+00:00)

計算: 一点計算  / 元素: Si / 原子数: 2
コード: Quantum ESPRESSO (pw.x)
実行先: プロファイル local (direct)

ファイル:
  submit.sh     実行スクリプト
  spec.json     設定一式。adit で開けば設定を復元できる
  analyze.py    解析スクリプト (python analyze.py --rdf --msd --dos。図と要約を analysis/ に書く。GUI の解析タブと同じ)
  pw.in         pw.x の入力 (名前空間 &CONTROL &SYSTEM &ELECTRONS &IONS &CELL と、種・座標・k 点のカード)
  ph.in / dynmat.in   振動解析のとき。submit.sh が pw.x → ph.x → dynmat.x の順に走らせ、振動数は dynmat.out
  pseudo/       この計算に要る擬ポテンシャル (UPF): Si.pbe-n-rrkjus_psl.1.0.0.UPF

実行 (ローカル)。実行ファイルが PATH にあること (例: conda activate dftbplus):
  bash submit.sh
  標準出力は output.log に入る


出力の見方:
  output.log    pw.x の標準出力 ('!    total energy' の行が各 SCC の全エネルギー。単位 Ry)
  tmp/          波動関数と電荷密度 (outdir)

引用: 擬ポテンシャルの配布物 (pslibrary) のライセンスと引用要件に従う (セットのディレクトリに LICENSE / README が無かったので同梱していない。配布元で確かめること)。
  Quantum ESPRESSO 自体の引用は https://www.quantum-espresso.org/ を参照。
