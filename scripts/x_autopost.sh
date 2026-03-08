#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${X_BOT_ENV_FILE:-$HOME/.config/x-bot/.env}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/x_autopost.py"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 2
fi

if [[ $# -eq 0 ]]; then
  echo "Usage: $(basename "$0") \"post text\" | --from-file FILE [--dry-run]" >&2
  exit 2
fi

python3 "$PY_SCRIPT" --env-file "$ENV_FILE" "$@"
