"""Collect engagement for every post in data/posts.csv into data/metrics.csv.

likes and comments come from the media object (instagram_basic).
reach, saved, shares, views come from media insights, which may need the
instagram_manage_insights permission. If insights are refused, those
columns stay empty and the reason is printed; the run still succeeds.
"""

import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

GRAPH = "https://graph.facebook.com/v25.0"
INSIGHT_METRICS = ["reach", "saved", "shares", "views"]


def get(path: str, params: dict) -> tuple[dict, str]:
    params = dict(params, access_token=TOKEN)
    url = f"{GRAPH}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            return json.loads(resp.read()), ""
    except urllib.error.HTTPError as e:
        return {}, f"{e.code} {e.read().decode(errors='replace')}"
    except urllib.error.URLError as e:
        return {}, str(e.reason)


def main() -> None:
    posts = Path("data/posts.csv")
    if not posts.exists():
        print("No posts yet.")
        return
    rows = list(csv.DictReader(posts.open(encoding="utf-8")))
    now = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")

    out = []
    for r in rows:
        mid = r["media_id"].removeprefix("id_")
        base, err = get(mid, {"fields": "like_count,comments_count"})
        if err:
            print(f"::warning::{mid} basic fields failed: {err}")
        ins, ierr = get(f"{mid}/insights", {"metric": ",".join(INSIGHT_METRICS)})
        values = {}
        if ierr:
            print(f"::warning::{mid} insights unavailable: {ierr}")
        else:
            for item in ins.get("data", []):
                v = item.get("values") or [{}]
                values[item.get("name")] = v[0].get("value", "")
        out.append([
            now, r["media_id"],
            base.get("like_count", ""), base.get("comments_count", ""),
            values.get("saved", ""), values.get("shares", ""),
            values.get("reach", ""), values.get("views", ""),
        ])

    path = Path("data/metrics.csv")
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["collected_kst", "media_id", "likes", "comments", "saved", "shares", "reach", "views"])
        w.writerows(out)
    print(f"Updated {path} for {len(out)} posts")


if __name__ == "__main__":
    TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
    if not TOKEN:
        print("::error::IG_ACCESS_TOKEN secret is missing")
        sys.exit(1)
    main()
