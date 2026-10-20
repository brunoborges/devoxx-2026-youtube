"""Build the standalone dashboard using only the Python standard library."""

import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    data = json.loads((root / "data/devoxx_stats.json").read_text(encoding="utf-8"))
    template = (root / "src/devoxx-dashboard.template.html").read_text(encoding="utf-8")
    if template.count("__DATA__") != 1:
        raise ValueError("The dashboard template must contain exactly one __DATA__ placeholder")
    encoded = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    html = template.replace("__DATA__", encoded)
    (root / "index.html").write_bytes(html.encode("utf-8"))
    print(f"Built index.html: {len(html.encode('utf-8'))} bytes, {len(data)} videos")


if __name__ == "__main__":
    main()
