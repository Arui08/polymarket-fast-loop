#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple memory consolidation: append key bullet lines from today's memory file into MEMORY.md."""
from __future__ import annotations
import os
from datetime import datetime, timedelta

WORKSPACE = "/root/.openclaw/workspace"
MEM_DIR = os.path.join(WORKSPACE, "memory")
MEMORY_MD = os.path.join(WORKSPACE, "MEMORY.md")


def bjt_now():
    return datetime.utcnow() + timedelta(hours=8)


def today_file():
    d = bjt_now().strftime("%Y-%m-%d")
    return os.path.join(MEM_DIR, f"{d}.md"), d


def read_text(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def extract_bullets(text: str) -> list[str]:
    lines = [l.rstrip() for l in text.splitlines()]
    bullets = []
    for l in lines:
        if l.startswith("- ") or l.startswith("• "):
            bullets.append(l)
    # de-dup
    seen = set()
    out = []
    for b in bullets:
        if b not in seen:
            out.append(b)
            seen.add(b)
    return out


def main():
    today_path, day = today_file()
    mem_text = read_text(today_path)
    if not mem_text.strip():
        print("No memory content for today.")
        return

    memory_text = read_text(MEMORY_MD)
    marker = f"## 自动整合 {day}"
    if marker in memory_text:
        print("Already consolidated today.")
        return

    bullets = extract_bullets(mem_text)
    if not bullets:
        print("No bullet items to consolidate.")
        return

    ts = bjt_now().strftime("%Y-%m-%d %H:%M")
    block = ["", f"## 自动整合 {day} {ts}（北京时间）", ""]
    block.extend(bullets)
    block.append("")

    with open(MEMORY_MD, "a", encoding="utf-8") as f:
        f.write("\n".join(block))

    print(f"Consolidated {len(bullets)} items into MEMORY.md")


if __name__ == "__main__":
    main()
