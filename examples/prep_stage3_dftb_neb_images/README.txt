ADIT 0.0.1 が生成した、補間した反応経路の像ごとの一点計算です (dftbplus)

== 反応経路 (NEB) ==
  始状態・終状態を含めて 7 個の像 (中間 5 個)。全像は images.extxyz、条件は neb.json
  - 補間: ASE の NEB.interpolate (method = idpp、mic = False)
  これは NEB の最適化ではありません (像を補間した位置のまま、エネルギーだけを計算します)。
  経路に沿った長さ [Å] は neb.json の path_length_ang。

== 走らせたあと ==
  adit-analyze <このディレクトリ> --scan   (像ごとのエネルギーの表)

== この PC で走らせる ==
  bash submit.sh   (像の計算を順に走らせます。1 つずつ走らせるなら、各ディレクトリで bash submit.sh)

== クラスタで走らせる (ADIT は投入しません) ==
  各ディレクトリの submit.sh をクラスタのプロファイルで生成したうえで、このディレクトリで次のように投入します (互いに独立)。
  PBS:   for d in image_00 image_01 image_02 image_03 image_04 image_05 image_06; do (cd $d && qsub submit.sh); done
  Slurm: for d in image_00 image_01 image_02 image_03 image_04 image_05 image_06; do (cd $d && sbatch submit.sh); done
