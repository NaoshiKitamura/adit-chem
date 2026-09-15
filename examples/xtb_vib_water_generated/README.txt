ADIT 0.0.1 が生成した xtb の計算ディレクトリです (2026-09-10T08:58:20+00:00)

計算の種類: 振動解析 / 元素: O H / 原子数: 3
計算コード: xtb
実行先: プロファイル local (この PC で直接走らせる)
  (プロファイル = ADIT の環境設定に書いた「どこで・どう走らせるか」の組。ADIT の画面の「プロファイル」で選びます)

== このディレクトリのファイル ==
  submit.sh     ジョブスクリプト (計算を走らせる手順を書いたシェルスクリプト。下の「走らせる」で使います)
  spec.json     ADIT で決めた設定一式。ADIT の「ファイル」→「計算設定 (spec.json) を開く…」で読み込むと、同じ設定を画面に戻せます
  analyze.py    解析スクリプト (下の「結果の見方」を参照)
  struct.xyz    構造 (原子の種類と座標。xyz 形式、長さの単位は Å)
  xtb.inp       xtb への追加の指示 (SCC の最大反復回数、最適化の最大サイクル数、固定原子)
                計算手法・電荷・多重度・精度・温度は submit.sh の xtb の行に引数として書いてあります

== この PC で走らせる ==
  以下はターミナル (コマンドを 1 行ずつ打ち込んで PC を操作する画面。Windows なら WSL の Ubuntu) で行います。
  1. このディレクトリへ移動します (cd = 作業する場所を変えるコマンド)
       cd /home/<user>/adit/examples/xtb_vib_water_generated
  2. xtb が PATH (コマンドを探す場所の一覧) にあるか確かめます
       command -v xtb
     場所 (例: /home/.../bin/xtb) が 1 行出れば準備できています。何も出なければ、計算ソフトを入れた
     conda 環境 (ソフトごとに分けたインストール先) を有効にしてから、もう一度確かめます。例: conda activate <環境名>
  3. 走らせます
       bash submit.sh
     画面に何も出なくても動いています。記録は output.log に書かれ、終わると次のコマンドを打てる状態に戻ります。
     途中経過は別のターミナルで  tail -f output.log  (Ctrl+C で表示だけ止まり、計算は続きます)

== 研究室のクラスタで走らせたいとき ==
  クラスタ = 研究室や計算センターが共同で使う計算機の集まり。計算はジョブスケジューラ (PBS や Slurm。計算の順番待ちを
  管理するソフト) に預けて走らせます。預けた 1 件の計算を「ジョブ」と呼びます。
  いまの submit.sh はこの PC 用です。クラスタで使うには、先に次の 2 つを行います。
  a. ADIT の環境設定 (cluster.toml) に、kind = "pbs" か "slurm" のプロファイルを足します。書き方は ADIT の README.md の付録
     「クラスタで実行する場合」にあります。キュー名や module 名 (クラスタで計算ソフトを使えるようにするための名前) は
     クラスタごとに違うので、管理者か研究室の先輩に確かめてください。
  b. ADIT でプロファイルをそれに切り替えて生成し直します。submit.sh が qsub (PBS) / sbatch (Slurm) で預ける
     ジョブスクリプトになり、この README.txt にも、そのクラスタでの投入と確認のコマンドが入ります。
  そのあとの流れは次のとおりです (<...> は自分の値に置き換えます)。
  1. このディレクトリごとクラスタへ写します (手元の PC のターミナルで。scp / rsync = ネットワーク越しにファイルを写すコマンド)
       scp -r /home/<user>/adit/examples/xtb_vib_water_generated <ユーザー名>@<クラスタのホスト名>:<クラスタでの作業ディレクトリ>/
     または
       rsync -av /home/<user>/adit/examples/xtb_vib_water_generated <ユーザー名>@<クラスタのホスト名>:<クラスタでの作業ディレクトリ>/
  2. クラスタにログインして、写したディレクトリへ移動します (ssh = 別の計算機にログインするコマンド)
       ssh <ユーザー名>@<クラスタのホスト名>
       cd <クラスタでの作業ディレクトリ>/xtb_vib_water_generated
  3. ジョブを預けます (投入)。ジョブ番号が表示されれば受け付けられています
       qsub submit.sh     (PBS のとき)   /   sbatch submit.sh   (Slurm のとき)
  4. 状態を確かめます ($USER は自分のユーザー名に置き換わります)。一覧から消えたら終わっています
       qstat -u $USER     (PBS のとき)   /   squeue -u $USER    (Slurm のとき)
  5. 終わったら結果を手元に取り戻します (手元の PC のターミナルで)
       scp -r <ユーザー名>@<クラスタのホスト名>:<クラスタでの作業ディレクトリ>/xtb_vib_water_generated <手元の置き場所>/
     または
       rsync -av <ユーザー名>@<クラスタのホスト名>:<クラスタでの作業ディレクトリ>/xtb_vib_water_generated <手元の置き場所>/

== 結果の見方 ==
  output.log    xtb が画面に出す文字を保存したもの (TOTAL ENERGY の行が全エネルギー、単位は Eh = ハートリー)
  xtbout.json   結果をプログラムで読みやすい形で書いたもの
  vibspectrum / g98.out   振動数 (cm⁻¹) と IR 強度
  analyze.py    ADIT の解析タブと同じ処理で、図と要約を analysis/ に書きます。ADIT が入った Python で走らせます
       python analyze.py

== 引用 ==
  xtb の引用要件は https://xtb-docs.readthedocs.io/ を参照してください (GFN2-xTB: J. Chem. Theory Comput. 2019, 15, 1652 など)。
