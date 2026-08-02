#!/usr/bin/env python3
"""Refresh the 'Latest Releases' section of README.md from the GitHub Releases API.

Reads GITHUB_TOKEN from the environment when available (set automatically by
GitHub Actions) and falls back to unauthenticated requests for public repos.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

REPOS = [
    ("LevelGate", "Codex00911/LevelGate"),
    ("Graphify-Pro", "Codex00911/Graphify-Pro"),
    ("telegram-secretary-bot", "Codex00911/telegram-secretary-bot"),
]

TOKEN = os.environ.get("GITHUB_TOKEN", "")


def fetch(url):
    for attempt in range(3):
        req = urllib.request.Request(url)
        if TOKEN:
            req.add_header("Authorization", "token " + TOKEN)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "codex-readme-updater")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as err:
            if err.code == 404:
                return None
            if attempt < 2:
                time.sleep(2)
                continue
            raise
        except (urllib.error.URLError, OSError):
            if attempt < 2:
                time.sleep(2)
                continue
            raise
    return None


def main():
    rows = []
    for name, repo in REPOS:
        rel = fetch("https://api.github.com/repos/%s/releases/latest" % repo)
        if not rel:
            continue
        tag = rel.get("tag_name") or "?"
        title = rel.get("name") or ""
        body = rel.get("body") or ""
        # Pick the first meaningful description line: skip markdown headings and
        # lines that merely repeat the release title/tag
        desc = ""
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cleaned = re.sub(r"^[#>\*\-]+\s*", "", line)
            if cleaned and cleaned != title and cleaned != tag:
                desc = cleaned
                break
        notes = desc[:120].replace("|", "\\|")
        if not notes:
            notes = "\u2014"
        url = rel.get("html_url") or ("https://github.com/" + repo)
        rows.append((name, tag, notes, url))

    lines = ["<!-- RELEASES:START -->", ""]
    if rows:
        lines.append("| Project | Version | Notes |")
        lines.append("| :--- | :--- | :--- |")
        for name, tag, notes, url in rows:
            lines.append("| [%s](%s) | `%s` | %s |" % (name, url, tag, notes))
    else:
        lines.append("_No releases yet \u2014 the first one is on its way \U0001F680_")
    lines += ["", "<!-- RELEASES:END -->"]
    block = "\n".join(lines)

    with open("README.md", encoding="utf-8") as handle:
        content = handle.read()

    marker = re.compile(r"<!-- RELEASES:START -->.*?<!-- RELEASES:END -->", re.S)
    if not marker.search(content):
        print("ERROR: RELEASES markers not found in README.md", file=sys.stderr)
        return 1

    updated = marker.sub(block, content)
    if updated == content:
        print("No changes needed.")
        return 0

    with open("README.md", "w", encoding="utf-8") as handle:
        handle.write(updated)

    print("Updated releases section with %d release(s)." % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
