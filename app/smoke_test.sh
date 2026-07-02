#!/bin/bash
# ローカルスモークテスト: FastAPIバックエンドを起動し主要APIを叩く
set -u
cd "$(dirname "$0")"

export DATABRICKS_HOST=https://adb-7405605463330453.13.azuredatabricks.net
export DATABRICKS_TOKEN=$(/opt/homebrew/bin/databricks auth token -p Azure-ytcy-east2 | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")
export DATABRICKS_WAREHOUSE_ID=9c8fac7a0b250221
export DASHBOARD_ID=01f175b94ff116d6b06fc944ca327432
export GENIE_SPACE_ID=01f175badff718e583cec35283ec31ee

python3 -m uvicorn main:app --port 8123 >/tmp/uvicorn_smoke.log 2>&1 &
UVPID=$!
trap "kill $UVPID 2>/dev/null" EXIT
sleep 4

fail=0
check() { # name url [curl-args...]
  local name=$1; shift
  local out
  out=$(curl -s --max-time 120 "$@")
  if [ -z "$out" ] || echo "$out" | grep -q '"detail"'; then
    echo "NG  $name: ${out:0:200}"; fail=1
  else
    echo "OK  $name: ${out:0:120}"
  fi
}

check config   localhost:8123/api/config
check products localhost:8123/api/products
check lifecycle "localhost:8123/api/lifecycle?ids=P001,P002"
check ranking  localhost:8123/api/ltv/ranking
check features localhost:8123/api/ltv/features/P001
check thread   "localhost:8123/api/thread/P001?focus=incidents"
check predict  localhost:8123/api/ltv/predict -X POST -H 'Content-Type: application/json' -d '{"product_id":"P001","adj_margin_pt":2}'
echo "--- SPA index ---"
curl -s localhost:8123/ | head -c 120; echo
exit $fail
