#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace/tools/6551-twitter-to-binance-square
set -a
source /root/.openclaw/workspace/config/6551.env
source /root/.openclaw/workspace/config/binance-square.env
set +a
python3 scripts/auto_mirror.py --config /root/.openclaw/workspace/tools/6551-twitter-to-binance-square/_0xarui_config.json --once
