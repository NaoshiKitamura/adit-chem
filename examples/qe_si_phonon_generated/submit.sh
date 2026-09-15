#!/bin/bash
# adit 0.0.1 が生成 (2026-09-10T09:19:02+00:00)。実行先: ローカル (プロファイル local)
# 使い方: 実行ファイルが PATH にある状態で、このディレクトリで  bash submit.sh
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1
mpirun -np 2 pw.x -in pw.in > output.log 2>&1 && mpirun -np 2 ph.x -in ph.in > ph.log 2>&1 && dynmat.x < dynmat.in > dynmat.log 2>&1
