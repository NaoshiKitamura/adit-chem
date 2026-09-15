ADIT 0.0.1 が生成した Quantum ESPRESSO (pw.x) の計算ディレクトリです (2026-09-12 02:58 (JST))

計算の種類: 一点計算 / 元素: Si / 原子数: 2
計算コード: Quantum ESPRESSO (pw.x)
実行先: プロファイル local (この PC で直接走らせる)
  (プロファイル = ADIT の環境設定に書いた「どこで・どう走らせるか」の組。ADIT の画面の「プロファイル」で選びます)

== このディレクトリのファイル ==
  submit.sh     ジョブスクリプト (計算を走らせる手順を書いたシェルスクリプト。下の「走らせる」で使います)
  spec.json     ADIT で決めた設定一式。ADIT の「ファイル」→「計算設定 (spec.json) を開く…」で読み込むと、同じ設定を画面に戻せます
  analyze.py    解析スクリプト (下の「結果の見方」を参照)
  pw.in         pw.x の入力 (&CONTROL &SYSTEM などの設定と、元素・座標・k 点 = 周期系で電子の状態を計算する波数空間の点)
  pseudo/       この計算に必要な擬ポテンシャル (内殻電子の効果をまとめた、元素ごとのファイル。UPF 形式): Si.pbe-n-rrkjus_psl.1.0.0.UPF

== この PC で走らせる ==
  以下はターミナル (コマンドを 1 行ずつ打ち込んで PC を操作する画面。Windows なら WSL の Ubuntu) で行います。
  1. このディレクトリへ移動します (cd = 作業する場所を変えるコマンド)
       cd /home/<user>/adit/examples/prep_stage1_qe_dftu_si
  2. pw.x が PATH (コマンドを探す場所の一覧) にあるか確かめます
       command -v pw.x
     場所 (例: /home/.../bin/pw.x) が 1 行出れば準備できています。
     何も出なければ、計算ソフトを入れた conda 環境 (ソフトごとに分けたインストール先) を有効にしてから、
     もう一度確かめます。例: conda activate <環境名>  (入れていなければ: conda install -c conda-forge qe)
  3. 走らせます
       bash submit.sh
     画面に何も出なくても動いています。記録は output.log に書かれ、終わると次のコマンドを打てる状態に戻ります。
     途中経過は別のターミナルで  tail -f output.log  (Ctrl+C で表示だけ止まり、計算は続きます)

== 研究室のクラスタで走らせたいとき ==
  クラスタ = 研究室や計算センターが共同で使う計算機の集まり。計算はジョブスケジューラ (PBS や Slurm。計算の順番待ちを
  管理するソフト) に預けて走らせます。預けた 1 件の計算を「ジョブ」と呼びます。
  いまの submit.sh はこの PC 用です。クラスタで使うには、先に次の 2 つを行います。
  a. ADIT の環境設定ファイルに、kind = "pbs" か "slurm" のプロファイルを足します。環境設定ファイルの場所:
       /home/<user>/.config/qcgui/cluster.toml
     いちばん短い書き方は次のとおりです。ファイルの最後に書き足し、<...> を自分の値に置き換えます (# から行末までは説明で、
     消してもかまいません)。キュー名や module 名 (クラスタで計算ソフトを使えるようにするための名前) はクラスタごとに違うので、
     管理者か研究室の先輩に確かめてください。
       [profiles.remote]
       kind = "pbs"                                # Slurm のクラスタなら "slurm"
       header_extra = ["#PBS -q <キュー名>"]        # Slurm なら ["#SBATCH --partition=<パーティション名>"]
       [profiles.remote.code_modules]
       espresso = ["<module 名>"]                   # 計算ソフトを使えるようにする module の名前 (クラスタで module avail と打つと一覧が出ます)
     ほかの項目 (投入コマンド、環境変数、実行コマンドなど) は ADIT の README.md の「クラスタで実行する場合」にあります。
  b. ADIT でプロファイルをそれに切り替えて生成し直します。submit.sh が qsub (PBS) / sbatch (Slurm) で預ける
     ジョブスクリプトになり、この README.txt にも、そのクラスタでの投入と確認のコマンドが入ります。
  そのあとの流れは次のとおりです (<...> は自分の値に置き換えます)。
  1. このディレクトリごとクラスタへ写します (手元の PC のターミナルで。scp / rsync = ネットワーク越しにファイルを写すコマンド)
       scp -r /home/<user>/adit/examples/prep_stage1_qe_dftu_si <ユーザー名>@<クラスタのホスト名>:<クラスタでの作業ディレクトリ>/
     または
       rsync -av /home/<user>/adit/examples/prep_stage1_qe_dftu_si <ユーザー名>@<クラスタのホスト名>:<クラスタでの作業ディレクトリ>/
  2. クラスタにログインして、写したディレクトリへ移動します (ssh = 別の計算機にログインするコマンド)
       ssh <ユーザー名>@<クラスタのホスト名>
       cd <クラスタでの作業ディレクトリ>/prep_stage1_qe_dftu_si
  3. ジョブを預けます (投入)。ジョブ番号が表示されれば受け付けられています
       qsub submit.sh     (PBS のとき)   /   sbatch submit.sh   (Slurm のとき)
  4. 状態を確かめます ($USER は自分のユーザー名に置き換わります)。一覧から消えたら終わっています
       qstat -u $USER     (PBS のとき)   /   squeue -u $USER    (Slurm のとき)
  5. 終わったら結果を手元に取り戻します (手元の PC のターミナルで)
       scp -r <ユーザー名>@<クラスタのホスト名>:<クラスタでの作業ディレクトリ>/prep_stage1_qe_dftu_si <手元の置き場所>/
     または
       rsync -av <ユーザー名>@<クラスタのホスト名>:<クラスタでの作業ディレクトリ>/prep_stage1_qe_dftu_si <手元の置き場所>/

== 結果の見方 ==
  output.log    pw.x が画面に出す文字を保存したもの ('!    total energy' の行が全エネルギー。単位は Ry = リュードベリ)
  tmp/          波動関数と電荷密度 (続きの計算に使う途中のファイル。大きくなることがあります)
  analyze.py    ADIT の解析タブと同じ処理で、図と要約を analysis/ に書きます。ADIT が入った Python で走らせます
       python analyze.py

== 引用 ==
  擬ポテンシャルの配布物 (pslibrary) のライセンスと引用要件に従ってください (セットのディレクトリに LICENSE / README が無かったため含めていません。配布元で確認してください)。
  Quantum ESPRESSO 自体の引用は https://www.quantum-espresso.org/ を参照してください。

== 来歴 ==
  ADIT 0.0.1 / Python 3.14.7 / ASE 3.29.0 / 生成 2026-09-11T17:58:49+00:00 (UTC)
  パラメータなどのファイルの SHA-256 (中身から計算する指紋。同じ値なら同じファイル。spec.json の provenance にも同じもの):
    669fb75395a9d26973b0ea1ce8223bbcb30d3396c5d48bf5e794d1243c52375a  pseudo/Si.pbe-n-rrkjus_psl.1.0.0.UPF
  計算コードの版: 走り終えると submit.sh が出力の版の行を code_version.txt に写します
