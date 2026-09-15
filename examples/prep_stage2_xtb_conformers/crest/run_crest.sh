#!/bin/bash
# adit が生成。CREST (xtb によるメタダイナミクスの配座探索) を走らせる。ADIT は走らせない
cd "$(dirname "$0")"
crest struct.xyz --gfn2 --chrg 0 --uhf 0 -T 1 > crest.log 2>&1
