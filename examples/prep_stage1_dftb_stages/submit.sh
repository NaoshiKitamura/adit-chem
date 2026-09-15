#!/bin/bash
# adit 0.0.1 が生成。段を順に走らせる (前の段が失敗したらそこで止まる)
cd "$(dirname "$0")"
set -e
for d in stage_01_min stage_02_nvt stage_03_nve; do
  echo "== $d"
  bash "$d/submit.sh"
done
