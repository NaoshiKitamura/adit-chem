#!/bin/bash
# adit 0.0.1 が生成 (2026-09-10T07:19:07+00:00)。実行先: ローカル (プロファイル local)
# 使い方: 実行ファイルが PATH にある状態で、このディレクトリで  bash submit.sh
cd "$(dirname "$0")"
export OMP_NUM_THREADS=4
dftb+ > output.log 2>&1
