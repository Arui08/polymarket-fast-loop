#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace/tools/6551-twitter-to-binance-square
set -a
source /root/.openclaw/workspace/config/6551.env
source /root/.openclaw/workspace/config/binance-square.env
set +a

LOG_FILE="/root/.openclaw/workspace/tools/6551-twitter-to-binance-square/_0xarui_sync.log"
TMP_OUT=$(mktemp)
python3 scripts/auto_mirror.py --config /root/.openclaw/workspace/tools/6551-twitter-to-binance-square/_0xarui_config.json --once | tee "$TMP_OUT"
cat "$TMP_OUT" >> "$LOG_FILE"

LAST_SUCCESS=$(grep 'SUCCESS — Square post:' "$TMP_OUT" | tail -n 1 | sed 's/.*SUCCESS — Square post: //')
LAST_TWEET=$(grep 'Posting tweet ' "$TMP_OUT" | tail -n 1 | sed -E 's/.*Posting tweet ([0-9]+).*/\1/')

if [ -n "${LAST_SUCCESS:-}" ]; then
  openclaw message send \
    --channel telegram \
    --target 5411248320 \
    --message "✅ _0xarui 已同步到 Binance Square\n- Tweet ID: ${LAST_TWEET:-unknown}\n- Square: ${LAST_SUCCESS}" \
    >/dev/null 2>&1 || true
fi

rm -f "$TMP_OUT"
