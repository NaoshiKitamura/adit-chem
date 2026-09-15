#!/bin/bash
# adit 0.0.1 が生成 (2026-09-10T09:23:22+00:00)。実行先: ローカル (プロファイル local)
# 使い方: 実行ファイルが PATH にある状態で、このディレクトリで  bash submit.sh
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1
mpirun -np 2 pw.x -in pw.in > output.log 2>&1 && cd bands && mpirun -np 2 pw.x -in pw.in > output.log 2>&1
