ADIT 0.0.1 が生成した DFTB+ の計算ディレクトリです (2026-09-10T08:59:01+00:00)

計算の種類: 分子動力学 (MD) / 元素: O H / 原子数: 3
計算コード: DFTB+
実行先: プロファイル local (この PC で直接走らせる)
  (プロファイル = ADIT の環境設定に書いた「どこで・どう走らせるか」の組。ADIT の画面の「プロファイル」で選びます)

== このディレクトリのファイル ==
  submit.sh     ジョブスクリプト (計算を走らせる手順を書いたシェルスクリプト。下の「走らせる」で使います)
  spec.json     ADIT で決めた設定一式。ADIT の「ファイル」→「計算設定 (spec.json) を開く…」で読み込むと、同じ設定を画面に戻せます
  analyze.py    解析スクリプト (下の「結果の見方」を参照)
  dftb_in.hsd   DFTB+ の入力 (計算の設定。DFTB+ はこのディレクトリで起動すると自動でこれを読みます)
  geometry.gen  構造 (原子の種類と座標。gen 形式、長さの単位は Å)
  skf/          Slater-Koster ファイル (DFTB+ が使う、元素の組ごとのパラメータ) と LICENSE、README: H-H.skf, H-O.skf, LICENSE, O-H.skf, O-O.skf, README

== この PC で走らせる ==
  以下はターミナル (コマンドを 1 行ずつ打ち込んで PC を操作する画面。Windows なら WSL の Ubuntu) で行います。
  1. このディレクトリへ移動します (cd = 作業する場所を変えるコマンド)
       cd /home/<user>/adit/examples/dftb_md_water_generated
  2. dftb+ が PATH (コマンドを探す場所の一覧) にあるか確かめます
       command -v dftb+
     場所 (例: /home/.../bin/dftb+) が 1 行出れば準備できています。何も出なければ、計算ソフトを入れた
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
       scp -r /home/<user>/adit/examples/dftb_md_water_generated <ユーザー名>@<クラスタのホスト名>:<クラスタでの作業ディレクトリ>/
     または
       rsync -av /home/<user>/adit/examples/dftb_md_water_generated <ユーザー名>@<クラスタのホスト名>:<クラスタでの作業ディレクトリ>/
  2. クラスタにログインして、写したディレクトリへ移動します (ssh = 別の計算機にログインするコマンド)
       ssh <ユーザー名>@<クラスタのホスト名>
       cd <クラスタでの作業ディレクトリ>/dftb_md_water_generated
  3. ジョブを預けます (投入)。ジョブ番号が表示されれば受け付けられています
       qsub submit.sh     (PBS のとき)   /   sbatch submit.sh   (Slurm のとき)
  4. 状態を確かめます ($USER は自分のユーザー名に置き換わります)。一覧から消えたら終わっています
       qstat -u $USER     (PBS のとき)   /   squeue -u $USER    (Slurm のとき)
  5. 終わったら結果を手元に取り戻します (手元の PC のターミナルで)
       scp -r <ユーザー名>@<クラスタのホスト名>:<クラスタでの作業ディレクトリ>/dftb_md_water_generated <手元の置き場所>/
     または
       rsync -av <ユーザー名>@<クラスタのホスト名>:<クラスタでの作業ディレクトリ>/dftb_md_water_generated <手元の置き場所>/

== 結果の見方 ==
  output.log    実行ログ (SCC = 電荷を自己無撞着に決める反復 の様子と、各ステップのエネルギー)
  detailed.out  最後のステップのエネルギーの内訳、Mulliken 電荷 (原子ごとの電荷の目安)、原子にかかる力
  results.tag   全エネルギーなどを、プログラムで読みやすい形で書いたもの
  geo_end.xyz   MD の軌跡 (MDRestartFrequency ステップごとの構造と速度)
  md.out        各ステップのエネルギーと温度
  dftb_pin.hsd  省略した設定を既定値で埋めた入力。実際に使われた設定を確かめられます
  analyze.py    ADIT の解析タブと同じ処理で、図と要約を analysis/ に書きます。ADIT が入った Python で走らせます
       python analyze.py --rdf --msd   (動径分布関数と拡散係数も求めます)

== 引用 ==
  Slater-Koster セット mio-1-1 は CC BY-SA 4.0 で配布されています。論文などでは、セットの README
  (skf/README) に書かれた文献の引用が求められます。DFTB+ 自体の引用先は output.log の先頭に表示されます。
