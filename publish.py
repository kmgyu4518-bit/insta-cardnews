"""Instagram carousel publisher for daily card news.

Reads cards/<DATE>/01.jpg ... NN.jpg and cards/<DATE>/caption.txt from this
public repository, then publishes them as one carousel post through the
Instagram Content Publishing API.

Rules (from the project):
- Runs only when triggered manually after approval.
- On any failure: print the reason and stop. No retries.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_VERSION = "v25.0"
GRAPH = f"https://graph.facebook.com/{API_VERSION}"
REPO_RAW = "https://raw.githubusercontent.com/kmgyu4518-bit/insta-cardnews/main"
DAILY_LIMIT_GUARD = 50  # Meta docs say 50 or 100 per 24h; use the lower one.


def fail(msg: str) -> None:
    print(f"::error::{msg}")
    sys.exit(1)


def call(method: str, path: str, params: dict) -> dict:
    params = dict(params, access_token=TOKEN)
    data = urllib.parse.urlencode(params).encode()
    url = f"{GRAPH}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        # Never print the token; the error body from Meta does not contain it.
        fail(f"{method} {path} failed ({e.code}): {body}")
    except urllib.error.URLError as e:
        fail(f"{method} {path} network error: {e.reason}")
    return {}


def wait_ready(container_id: str, label: str) -> None:
    for _ in range(30):
        status = call("GET", container_id, {"fields": "status_code,status"})
        code = status.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            fail(f"{label} container {container_id} status {code}: {status.get('status')}")
        time.sleep(5)
    fail(f"{label} container {container_id} not ready after 150s")


def main() -> None:
    date = os.environ.get("CARD_DATE", "").strip()
    if not date:
        fail("CARD_DATE is empty")

    folder = Path("cards") / date
    images = sorted(p for p in folder.glob("*.jpg"))
    caption_file = folder / "caption.txt"

    if not 2 <= len(images) <= 10:
        fail(f"{folder}: carousel needs 2-10 JPEG files, found {len(images)}")
    if not caption_file.exists():
        fail(f"{caption_file} not found")
    caption = caption_file.read_text(encoding="utf-8").strip()
    if len(caption) > 2200:
        fail(f"caption is {len(caption)} chars, limit 2200")

    # 1) Rate limit check
    usage = call("GET", f"{IG_USER_ID}/content_publishing_limit",
                 {"fields": "quota_usage,config"})
    used = (usage.get("data") or [{}])[0].get("quota_usage", 0)
    print(f"Publishing quota used in last 24h: {used}")
    if used >= DAILY_LIMIT_GUARD:
        fail(f"quota_usage {used} reached guard {DAILY_LIMIT_GUARD}")

    # 2) Item containers
    children = []
    for img in images:
        url = f"{REPO_RAW}/{img.as_posix()}"
        res = call("POST", f"{IG_USER_ID}/media",
                   {"image_url": url, "is_carousel_item": "true"})
        cid = res.get("id")
        if not cid:
            fail(f"no container id for {img.name}: {res}")
        print(f"item container {img.name}: {cid}")
        wait_ready(cid, img.name)
        children.append(cid)

    # 3) Carousel container
    carousel_params = {
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption,
    }
    if os.environ.get("AI_LABEL", "true").lower() == "true":
        carousel_params["is_ai_generated"] = "true"
    res = call("POST", f"{IG_USER_ID}/media", carousel_params)
    carousel_id = res.get("id")
    if not carousel_id:
        fail(f"no carousel container id: {res}")
    print(f"carousel container: {carousel_id}")
    wait_ready(carousel_id, "carousel")

    # 4) Publish
    res = call("POST", f"{IG_USER_ID}/media_publish", {"creation_id": carousel_id})
    media_id = res.get("id")
    if not media_id:
        fail(f"publish returned no media id: {res}")
    info = call("GET", media_id, {"fields": "permalink,timestamp"})
    print(f"Published media {media_id}")
    print(f"Permalink: {info.get('permalink')}")


if __name__ == "__main__":
    TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
    IG_USER_ID = os.environ.get("IG_USER_ID", "")
    if not TOKEN or not IG_USER_ID:
        fail("IG_ACCESS_TOKEN or IG_USER_ID secret is missing")
    main()
