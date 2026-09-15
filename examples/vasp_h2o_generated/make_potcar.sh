#!/bin/bash
# potcar.spec の順に $VASP_PP_PATH/potpaw_PBE/<名前>/POTCAR を連結して POTCAR を作る。adit が生成
set -e
cd "$(dirname "$0")"
: "${VASP_PP_PATH:?VASP_PP_PATH が空。POTCAR 庫の親ディレクトリを環境変数で指定してから実行する}"
: > POTCAR
: > potcar.used
for name in O H; do
  f="$VASP_PP_PATH/potpaw_PBE/$name/POTCAR"
  [ -s "$f" ] || { echo "POTCAR が無い: $f" >&2; exit 1; }
  cat "$f" >> POTCAR
  printf '%s  %s  %s\n' "$name" "$(grep -m1 TITEL "$f" | sed 's/^ *//')" "$(grep -m1 ZVAL "$f" | sed 's/^ *//')" >> potcar.used
done
echo "POTCAR を作った ($(grep -c TITEL POTCAR) 個)。内訳は potcar.used"
