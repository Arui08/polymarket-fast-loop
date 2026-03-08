#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ENV_DEFAULT = Path.home() / ".config" / "x-bot" / ".env"
LOG_DIR_DEFAULT = Path.home() / ".local" / "share" / "x-bot" / "logs"
STATE_DIR_DEFAULT = Path.home() / ".local" / "share" / "x-bot"


def load_env(env_path: Path) -> dict:
    data = {}
    if not env_path.exists():
        return data
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def require_env(env: dict, keys: list[str]) -> None:
    missing = [k for k in keys if not env.get(k)]
    if missing:
        print("Missing env keys:", ", ".join(missing), file=sys.stderr)
        sys.exit(2)


def run(cmd: list[str], env: dict) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        raise SystemExit(proc.returncode)
    return proc.stdout.strip()


def ensure_xurl_auth(env: dict) -> None:
    out = run(["xurl", "auth", "status"], env)
    if "authenticated" not in out.lower() and "default" not in out.lower() and "app" not in out.lower():
        print(out)


def write_log(log_dir: Path, payload: dict) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = log_dir / f"post-{ts}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def update_last_post(state_dir: Path, text: str) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "last_post.txt").write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Minimal X auto poster via xurl")
    parser.add_argument("text", nargs="?", help="post text")
    parser.add_argument("--env-file", default=str(ENV_DEFAULT))
    parser.add_argument("--from-file", help="read post text from file")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-dir", default=str(LOG_DIR_DEFAULT))
    parser.add_argument("--state-dir", default=str(STATE_DIR_DEFAULT))
    args = parser.parse_args()

    env_path = Path(args.env_file).expanduser()
    file_env = load_env(env_path)
    merged_env = os.environ.copy()
    merged_env.update(file_env)

    require_env(file_env, ["XURL_APP_NAME"])

    if args.from_file:
        text = Path(args.from_file).expanduser().read_text(encoding="utf-8").strip()
    else:
        text = (args.text or "").strip()

    if not text:
        print("Post text is empty", file=sys.stderr)
        sys.exit(2)

    if len(text) > 280:
        print(f"Post too long: {len(text)} chars", file=sys.stderr)
        sys.exit(2)

    ensure_xurl_auth(merged_env)

    if args.dry_run:
        payload = {
            "mode": "dry-run",
            "length": len(text),
            "text": text,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        path = write_log(Path(args.log_dir).expanduser(), payload)
        print(json.dumps({"ok": True, "dry_run": True, "log": str(path)}, ensure_ascii=False))
        return

    cmd = ["xurl", "--app", file_env["XURL_APP_NAME"], "post", text]
    stdout = run(cmd, merged_env)

    try:
        resp = json.loads(stdout)
    except Exception:
        resp = {"raw": stdout}

    payload = {
        "mode": "live",
        "text": text,
        "response": resp,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    log_path = write_log(Path(args.log_dir).expanduser(), payload)
    update_last_post(Path(args.state_dir).expanduser(), text)
    print(json.dumps({"ok": True, "log": str(log_path), "response": resp}, ensure_ascii=False))


if __name__ == "__main__":
    main()
