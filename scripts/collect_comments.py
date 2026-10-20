"""Collect aggregate public comment counts without retaining comment content."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "data/devoxx_stats.json"


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def text(value):
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""
    return value.get("simpleText", "") or "".join(
        run.get("text", "") for run in value.get("runs", [])
    )


def exact_count(label):
    match = re.fullmatch(r"\s*([\d,]+)\s*(?:Comments?)?\s*", label, re.I)
    if not match or not re.fullmatch(r"\d+|\d{1,3}(?:,\d{3})+", match[1]):
        return None
    return int(match[1].replace(",", ""))


def parse_count(value):
    for node in walk(value):
        for key in ("commentsHeaderRenderer", "commentsEntryPointHeaderRenderer"):
            if key not in node:
                continue
            header = node[key]
            for field in ("countText", "commentCount"):
                label = text(header.get(field))
                count = exact_count(label)
                if count is not None:
                    return count, label
    return None


def is_disabled(value):
    return any(
        "comments are turned off" in text(node.get("text")).lower()
        or "comments are disabled" in text(node.get("text")).lower()
        for node in walk(value)
    )


def embedded(page, marker):
    return json.JSONDecoder().raw_decode(page.split(marker, 1)[1].lstrip())[0]


def request(url, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Origin": "https://www.youtube.com",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))
        except (TimeoutError, urllib.error.URLError):
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))


def collect(video):
    result = {
        "comments": None,
        "comments_status": "unavailable",
        "comments_source": "YouTube public comments header",
        "comments_reported_text": None,
        "comments_error": None,
    }
    try:
        page = request(video["url"] + "&hl=en")
        initial = embedded(page, "var ytInitialData = ")
        found = parse_count(initial)
        sections = [
            node["itemSectionRenderer"]
            for node in walk(initial)
            if node.get("itemSectionRenderer", {}).get("sectionIdentifier")
            == "comment-item-section"
        ]
        if not found and any(is_disabled(section) for section in sections):
            result["comments_status"] = "disabled"
        elif not found:
            token = next(
                (
                    node["continuationCommand"]["token"]
                    for section in sections
                    for node in walk(section)
                    if "continuationCommand" in node
                ),
                None,
            )
            if token:
                context = embedded(page, '"INNERTUBE_CONTEXT":')
                response = json.loads(
                    request(
                        "https://www.youtube.com/youtubei/v1/next?prettyPrint=false",
                        {"context": context, "continuation": token},
                    )
                )
                if "error" in response:
                    raise ValueError("YouTube continuation returned an API error")
                found = parse_count(response)
                if not found and is_disabled(response):
                    result["comments_status"] = "disabled"
        if found:
            result["comments"], result["comments_reported_text"] = found
            result["comments_status"] = "available"
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError) as exc:
        result["comments_status"] = "failed"
        result["comments_error"] = f"{type(exc).__name__}: {exc}"
    result["comments_captured_at_utc"] = datetime.now(timezone.utc).isoformat()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", action="store_true", help="Skip available/disabled records")
    args = parser.parse_args()
    rows = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    pending = [
        row for row in rows
        if not args.resume or row.get("comments_status") not in ("available", "disabled")
    ]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(collect, row): row for row in pending}
        for future in as_completed(futures):
            row = futures[future]
            row.update(future.result())
            temporary = SNAPSHOT.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            temporary.replace(SNAPSHOT)
            print(
                f"{row['url']}: {row['comments_status']} "
                f"{row['comments'] if row['comments'] is not None else '—'}"
                + (f" ({row['comments_error']})" if row["comments_error"] else ""),
                flush=True,
            )
    statuses = {status: sum(row.get("comments_status") == status for row in rows)
                for status in ("available", "disabled", "unavailable", "failed")}
    print(json.dumps(statuses), flush=True)
    if statuses["failed"]:
        raise SystemExit("Some requests failed; see comments_error in the snapshot and retry with --resume.")


if __name__ == "__main__":
    main()
