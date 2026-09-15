#!/bin/sh
#PBS -N si
#PBS -l select=1:ncpus=8:mpiprocs=8:ompthreads=1:jobtype=core
#PBS -l walltime=01:00:00
#PBS -j oe
#PBS -q normal
# adit 0.0.1 が生成 (2026-09-10T07:49:48+00:00)。実行先: PBS (プロファイル cluster)
# 使い方: このディレクトリを転送し、その中で  qsub submit.sh

if [ ! -z "${PBS_O_WORKDIR}" ]; then
   cd ${PBS_O_WORKDIR}
fi

# #!/bin/sh では module が未定義なことがある。/etc/profile を読んでから確かめる (無ければ理由を出して止まる)

export OMP_NUM_THREADS=1
ulimit -s unlimited
bash make_potcar.sh && mpirun -np 8 vasp_std > output.log 2>&1
