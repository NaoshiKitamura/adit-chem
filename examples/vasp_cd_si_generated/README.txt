ADIT 0.0.1 が生成した VASP の計算ディレクトリです (2026-09-10T07:49:48+00:00)

計算の種類: 構造最適化 / 元素: Si / 原子数: 2
計算コード: VASP
実行先: プロファイル local (この PC で直接走らせる)
  (プロファイル = ADIT の環境設定に書いた「どこで・どう走らせるか」の組。ADIT の画面の「プロファイル」で選びます)

== このディレクトリのファイル ==
  submit.sh     ジョブスクリプト (計算を走らせる手順を書いたシェルスクリプト。下の「走らせる」で使います)
  spec.json     ADIT で決めた設定一式。ADIT の「ファイル」→「計算設定 (spec.json) を開く…」で読み込むと、同じ設定を画面に戻せます
  analyze.py    解析スクリプト (下の「結果の見方」を参照)
  INCAR         VASP の入力 (計算の設定)
  POSCAR        構造 (元素ごとにまとめ直してあり、順番は potcar.spec と同じです)
  KPOINTS       k 点 (周期系で電子の状態を計算する、波数空間の点の取り方)
  potcar.spec   使う POTCAR (元素ごとの擬ポテンシャル) の一覧 (Si → Si)。POTCAR 自体は入っていません
  make_potcar.sh  上の一覧の順に POTCAR をつなげて 1 つのファイルにします (submit.sh が最初に呼びます)

== 走らせる前に用意すること ==
  POTCAR は VASP のライセンス保持者にしか配布できないため、このディレクトリには入っていません。
  計算を走らせる機械で、環境変数 VASP_PP_PATH (POTCAR ライブラリの親ディレクトリ。その下に potpaw_PBE/<名前>/POTCAR がある場所)
  を設定しておいてください。ADIT の環境設定 (cluster.toml のプロファイルの env) に書いておくと、submit.sh が設定します。
  この PC では POTCAR ライブラリを確認できなかったため、potcar.spec の TITEL / ZVAL は未確認です (実行時に make_potcar.sh が potcar.used に記録します)。

== この PC で走らせる ==
  以下はターミナル (コマンドを 1 行ずつ打ち込んで PC を操作する画面。Windows なら WSL の Ubuntu) で行います。
  1. このディレクトリへ移動します (cd = 作業する場所を変えるコマンド)
       cd /home/<user>/adit/examples/vasp_cd_si_generated
  2. vasp_std が PATH (コマンドを探す場所の一覧) にあるか確かめます
       command -v vasp_std
     場所 (例: /home/.../bin/vasp_std) が 1 行出れば準備できています。何も出なければ、計算ソフトを入れた
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
       scp -r /home/<user>/adit/examples/vasp_cd_si_generated <ユーザー名>@<クラスタのホスト名>:<クラスタでの作業ディレクトリ>/
     または
       rsync -av /home/<user>/adit/examples/vasp_cd_si_generated <ユーザー名>@<クラスタのホスト名>:<クラスタでの作業ディレクトリ>/
  2. クラスタにログインして、写したディレクトリへ移動します (ssh = 別の計算機にログインするコマンド)
       ssh <ユーザー名>@<クラスタのホスト名>
       cd <クラスタでの作業ディレクトリ>/vasp_cd_si_generated
  3. ジョブを預けます (投入)。ジョブ番号が表示されれば受け付けられています
       qsub submit.sh     (PBS のとき)   /   sbatch submit.sh   (Slurm のとき)
  4. 状態を確かめます ($USER は自分のユーザー名に置き換わります)。一覧から消えたら終わっています
       qstat -u $USER     (PBS のとき)   /   squeue -u $USER    (Slurm のとき)
  5. 終わったら結果を手元に取り戻します (手元の PC のターミナルで)
       scp -r <ユーザー名>@<クラスタのホスト名>:<クラスタでの作業ディレクトリ>/vasp_cd_si_generated <手元の置き場所>/
     または
       rsync -av <ユーザー名>@<クラスタのホスト名>:<クラスタでの作業ディレクトリ>/vasp_cd_si_generated <手元の置き場所>/

== 結果の見方 ==
  output.log    VASP が画面に出す文字を保存したもの (電子の反復 1 回ごとの行)
  OSZICAR       各ステップのエネルギーの要約
  OUTCAR        詳しい出力 (エネルギー、力、各ステップ)
  vasprun.xml   結果をプログラムで読みやすい形で書いたもの (ASE や pymatgen で読めます)
  CONTCAR       最適化後の構造 (POSCAR と同じ形式)
  analyze.py    ADIT の解析タブと同じ処理で、図と要約を analysis/ に書きます。ADIT が入った Python で走らせます
       python analyze.py

== 引用 ==
  VASP の引用要件は https://www.vasp.at/ を参照してください。POTCAR は配布物のライセンスに従います。
