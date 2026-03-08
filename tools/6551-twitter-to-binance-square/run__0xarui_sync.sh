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
POSTS_MADE=$(grep -oE 'Cycle 1 complete: [0-9]+ posts made' "$TMP_OUT" | tail -n 1 | sed -E 's/.*: ([0-9]+) posts made/\1/' || echo "0")

if [ -n "${LAST_SUCCESS:-}" ]; then
  openclaw message send \
    --channel telegram \
    --target 5411248320 \
    --message "✅ _0xarui 已同步到 Binance Square\n- Tweet ID: ${LAST_TWEET:-unknown}\n- Square: ${LAST_SUCCESS}" \
    >/dev/null 2>&1 || true
elif [ "${POSTS_MADE:-0}" = "0" ]; then
  FALLBACK_OUT=$(mktemp)
  if python3 scripts/fallback_market_post.py | tee "$FALLBACK_OUT" >> "$LOG_FILE"; then
    FALLBACK_URL=$(grep -oE 'https://www.binance.com/square/post/[0-9]+' "$FALLBACK_OUT" | tail -n 1 || true)
    openclaw message send \
      --channel telegram \
      --target 5411248320 \
      --message "🟡 20:00 无新推文，已自动补发一条晚间行情帖到 Binance Square${FALLBACK_URL:+\n- Square: $FALLBACK_URL}" \
      >/dev/null 2>&1 || true
  else
    openclaw message send \
      --channel telegram \
      --target 5411248320 \
      --message "❌ 20:00 无新推文，且自动补发行情帖失败，请检查 Binance Square 链路" \
      >/dev/null 2>&1 || true
  fi
  rm -f "$FALLBACK_OUT"
fi

rm -f "$TMP_OUT"
