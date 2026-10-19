#!/usr/bin/env bash
# First-run (and any-run) bootstrap of the MarketMind compose stack.
#
#   1. waits until the six HTTP services answer their liveness route;
#   2. calibrates the MOS dimension weights for the current period
#      (POST /admin/mos/refresh-weights on the scoring) — fixed weights,
#      versioned by period, so running it again is harmless;
#   3. prints the scoring's GET /health, which also probes the four collectors.
#
# Reads the host ports from deploy/.env (same defaults as docker-compose.yml).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$here/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$here/.env"
  set +a
fi

host="${DEPLOY_HOST:-localhost}"
timeout="${BOOTSTRAP_TIMEOUT_SECONDS:-600}"

services=(
  "pytrends=http://$host:${PYTRENDS_PORT:-8000}/healthz"
  "oecd=http://$host:${OECD_PORT:-8001}/healthz"
  "undata=http://$host:${UNDATA_PORT:-8002}/healthz"
  "worldbank=http://$host:${WORLDBANK_PORT:-8003}/healthz"
  "scoring=http://$host:${SCORING_PORT:-8004}/healthz"
  "orchestrator=http://$host:${ORCHESTRATOR_PORT:-8081}/healthz"
)

wait_for() {
  local name="$1" url="$2" start=$SECONDS
  printf '%-14s %s ' "$name" "$url"
  until curl -fsS -o /dev/null --max-time 3 "$url"; do
    if (( SECONDS - start > timeout )); then
      echo "TIMEOUT after ${timeout}s"
      echo "Still not up. Look at: make logs" >&2
      exit 1
    fi
    printf '.'
    sleep 3
  done
  echo " ok"
}

echo "== Waiting for the services (first start runs the migrations; can take a minute)"
for entry in "${services[@]}"; do
  wait_for "${entry%%=*}" "${entry#*=}"
done

scoring="http://$host:${SCORING_PORT:-8004}"

echo
echo "== Calibrating the MOS weights for the current period"
curl -fsS -X POST "$scoring/admin/mos/refresh-weights" -H 'Content-Length: 0'
echo

echo
echo "== Scoring health (own database + the four collectors)"
health="$(curl -fsS "$scoring/health")"
if command -v python3 >/dev/null 2>&1; then
  printf '%s' "$health" | python3 -m json.tool
else
  echo "$health"
fi

echo
echo "Web:          http://$host:${WEB_PORT:-8080}"
echo "Orchestrator: http://$host:${ORCHESTRATOR_PORT:-8081}/docs"
echo "Scoring:      $scoring/docs"
