#!/usr/bin/env python3
"""
Simmer FastLoop Trading Skill

Trades Polymarket BTC 5-minute fast markets using CEX price momentum.
Default signal: Binance BTCUSDT candles. Agents can customize signal source.

Usage:
 python fast_trader.py # Dry run (show opportunities, no trades)
 python fast_trader.py --live # Execute real trades
 python fast_trader.py --positions # Show current fast market positions
 python fast_trader.py --quiet # Only output on trades/errors

Requires:
 SIMMER_API_KEY environment variable (get from simmer.markets/dashboard)
"""

import os
import sys
import json
import math
import argparse
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote

# Force line-buffered stdout for non-TTY environments (cron, Docker, OpenClaw)
sys.stdout.reconfigure(line_buffering=True)

# Optional: Trade Journal integration
try:
 from tradejournal import log_trade
 JOURNAL_AVAILABLE = True
except ImportError:
 try:
 from skills.tradejournal import log_trade
 JOURNAL_AVAILABLE = True
 except ImportError:
 JOURNAL_AVAILABLE = False
 def log_trade(*args, **kwargs):
 pass

# =============================================================================
# Configuration (config.json > env vars > defaults)
# =============================================================================

CONFIG_SCHEMA = {
 "entry_threshold": {"default": 0.05, "env": "SIMMER_SPRINT_ENTRY", "type": float,
 "help": "Min price divergence from 50¢ to trigger trade"},
 "min_momentum_pct": {"default": 0.5, "env": "SIMMER_SPRINT_MOMENTUM", "type": float,
 "help": "Min BTC % move in lookback window to trigger"},
 "max_position": {"default": 5.0, "env": "SIMMER_SPRINT_MAX_POSITION", "type": float,
 "help": "Max $ per trade"},
 "signal_source": {"default": "binance", "env": "SIMMER_SPRINT_SIGNAL", "type": str,
 "help": "Price feed source (binance)"},
 "lookback_minutes": {"default": 5, "env": "SIMMER_SPRINT_LOOKBACK", "type": int,
 "help": "Minutes of price history for momentum calc"},
 "min_time_remaining": {"default": 0, "env": "SIMMER_SPRINT_MIN_TIME", "type": int,
 "help": "Skip fast_markets with less than this many seconds remaining (0 = auto: 10%% of window)"},
 "asset": {"default": "BTC", "env": "SIMMER_SPRINT_ASSET", "type": str,
 "help": "Asset to trade (BTC, ETH, SOL)"},
 "window": {"default": "5m", "env": "SIMMER_SPRINT_WINDOW", "type": str,
 "help": "Market window duration (5m or 15m)"},
 "volume_confidence": {"default": True, "env": "SIMMER_SPRINT_VOL_CONF", "type": bool,
 "help": "Weight signal by volume (higher volume = more confident)"},
 "daily_budget": {"default": 10.0, "env": "SIMMER_SPRINT_DAILY_BUDGET", "type": float,
 "help": "Max total spend per UTC day"},
}

TRADE_SOURCE = "sdk:fastloop"
SKILL_SLUG = "polymarket-fast-loop"
_automaton_reported = False
SMART_SIZING_PCT = 0.05 # 5% of balance per trade
MIN_SHARES_PER_ORDER = 5 # Polymarket minimum
MAX_SPREAD_PCT = 0.10 # Skip if CLOB bid-ask spread exceeds this

# Asset → Binance symbol mapping
ASSET_SYMBOLS = {
 "BTC": "BTCUSDT",
 "ETH": "ETHUSDT",
 "SOL": "SOLUSDT",
}

# Asset → Gamma API search patterns
ASSET_PATTERNS = {
 "BTC": ["bitcoin up or down"],
 "ETH": ["ethereum up or down"],
 "SOL": ["solana up or down"],
}


from simmer_sdk.skill import load_config, update_config, get_config_path# Load config
cfg = load_config(CONFIG_SCHEMA, file, slug="polymarket-fast-loop")
ENTRY_THRESHOLD = cfg["entry_threshold"]
MIN_MOMENTUM_PCT = cfg["min_momentum_pct"]
MAX_POSITION_USD = cfg["max_position"]
_automaton_max = os.environ.get("AUTOMATON_MAX_BET")
if _automaton_max:
 MAX_POSITION_USD = min(MAX_POSITION_USD, float(_automaton_max))
SIGNAL_SOURCE = cfg["signal_source"]
LOOKBACK_MINUTES = cfg["lookback_minutes"]
ASSET = cfg["asset"].upper()
WINDOW = cfg["window"] # "5m" or "15m"

# Dynamic min_time_remaining: 0 = auto (10% of window duration)
_window_seconds = {"5m": 300, "15m": 900, "1h": 3600}
_configured_min_time = cfg["min_time_remaining"]
if _configured_min_time > 0:
 MIN_TIME_REMAINING = _configured_min_time
else:
 MIN_TIME_REMAINING = max(30, _window_seconds.get(WINDOW, 300) // 10)
VOLUME_CONFIDENCE = cfg["volume_confidence"]
DAILY_BUDGET = cfg["daily_budget"]

# Polymarket crypto fee formula constants (from docs.polymarket.com/trading/fees)
# fee = C × p × POLY_FEE_RATE × (p × (1-p))^POLY_FEE_EXPONENT
POLY_FEE_RATE = 0.25 # Crypto markets
POLY_FEE_EXPONENT = 2 # Crypto markets


# =============================================================================
# Daily Budget Tracking
# =============================================================================

def _get_spend_path(skill_file):
 from pathlib import Path
 return Path(skill_file).parent / "daily_spend.json"


def _load_daily_spend(skill_file):
 """Load today's spend. Resets if date != today (UTC)."""
 spend_path = _get_spend_path(skill_file)
 today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
 if spend_path.exists():
 try:
 with open(spend_path) as f:
 data = json.load(f)
 if data.get("date") == today:
 return data
 except (json.JSONDecodeError, IOError):
 pass
 return {"date": today, "spent": 0.0, "trades": 0}


def _save_daily_spend(skill_file, spend_data):
 """Save daily spend to file."""
 spend_path = _get_spend_path(skill_file)
 with open(spend_path, "w") as f:
 json.dump(spend_data, f, indent=2)


# =============================================================================
# API Helpers
# =============================================================================

_client = None

def get_client(live=True):
 """Lazy-init SimmerClient singleton."""
 global _client
 if _client is None:
 try:
 from simmer_sdk import SimmerClient
 except ImportError:
 print("Error: simmer-sdk not installed. Run: pip install simmer-sdk")
 sys.exit(1)
 api_key = os.environ.get("SIMMER_API_KEY")
 if not api_key:
 print("Error: SIMMER_API_KEY environment variable not set")
 print("Get your API key from: simmer.markets/dashboard → SDK tab")
 sys.exit(1)
 venue = os.environ.get("TRADING_VENUE", "polymarket")
 _client = SimmerClient(api_key=api_key, venue=venue, live=live)
 return _client
