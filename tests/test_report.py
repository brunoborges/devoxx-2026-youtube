import csv
from io import BytesIO, StringIO
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build
import collect_comments as collector


def header(label):
    return {"commentsHeaderRenderer": {"countText": {"runs": [{"text": label}]}}}


class CommentTests(unittest.TestCase):
    def test_exact_counts(self):
        for label, expected in [("0 Comments", 0), ("1 Comment", 1), ("1,234 Comments", 1234)]:
            self.assertEqual(collector.parse_count(header(label)), (expected, label))
        for label in ("1.2K Comments", "Comments", "1,23 Comments", "-1 Comments", ""):
            self.assertIsNone(collector.parse_count(header(label)))
        self.assertIsNone(collector.parse_count({"commentRenderer": {"text": "10 Comments"}}))

    def test_continuation(self):
        initial = {"itemSectionRenderer": {
            "sectionIdentifier": "comment-item-section",
            "contents": [{"continuationCommand": {"token": "test-token"}}],
        }}
        page = 'var ytInitialData = ' + json.dumps(initial) + ';"INNERTUBE_CONTEXT":{}'
        with patch.object(collector, "request", side_effect=[page, json.dumps(header("0 Comments"))]):
            result = collector.collect({"url": "https://www.youtube.com/watch?v=test"})
        self.assertEqual(result["comments"], 0)
        self.assertEqual(result["comments_status"], "available")
        self.assertIsNotNone(result["comments_captured_at_utc"])

    def test_missing_disabled_and_failure_are_not_zero(self):
        disabled = {"itemSectionRenderer": {
            "sectionIdentifier": "comment-item-section",
            "contents": [{"messageRenderer": {"text": {"simpleText": "Comments are turned off."}}}],
        }}
        for initial, expected in [({}, "unavailable"), (disabled, "disabled")]:
            with patch.object(collector, "request", return_value="var ytInitialData = " + json.dumps(initial)):
                result = collector.collect({"url": "https://www.youtube.com/watch?v=test"})
            self.assertIsNone(result["comments"])
            self.assertEqual(result["comments_status"], expected)
        with patch.object(collector, "request", side_effect=TimeoutError("request timed out")):
            result = collector.collect({"url": "https://www.youtube.com/watch?v=test"})
        self.assertIsNone(result["comments"])
        self.assertEqual(result["comments_status"], "failed")
        self.assertIn("timed out", result["comments_error"])


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.rows = json.loads((ROOT / "data/devoxx_stats.json").read_text(encoding="utf-8"))

    def test_canonical_snapshot(self):
        self.assertEqual(len(self.rows), 192)
        self.assertEqual(len({r["url"] for r in self.rows}), 192)
        self.assertEqual(sum(r["views"] for r in self.rows), 291615)
        self.assertEqual(sum(r["likes"] for r in self.rows), 2352)
        for row in self.rows:
            self.assertTrue(row["captured_at_utc"].startswith("2026-10-20"))
            self.assertTrue(row["comments_captured_at_utc"])
            self.assertIn(row["comments_status"], ("available", "disabled", "unavailable", "failed"))
            if row["comments_status"] == "available":
                self.assertIsInstance(row["comments"], int)
                self.assertGreaterEqual(row["comments"], 0)
                self.assertEqual(collector.exact_count(row["comments_reported_text"]), row["comments"])
            else:
                self.assertIsNone(row["comments"])

    def test_exports_match_canonical_data(self):
        base = ROOT / "data/devoxx-videos-since-2026-10-01"
        csv_rows = list(csv.DictReader(StringIO(base.with_suffix(".csv").read_text(encoding="utf-8-sig"))))
        self.assertEqual(len(csv_rows), len(self.rows))
        for source, exported in zip(self.rows, csv_rows):
            self.assertEqual(exported, {field: build.csv_cell(source.get(field)) for field in build.FIELDS})
        with ZipFile(base.with_suffix(".xlsx")) as archive:
            self.assertIsNone(archive.testzip())
            root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
            ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            rows = root.findall("s:sheetData/s:row", ns)
            self.assertEqual(len(rows), 193)
            for source, row in zip(self.rows, rows[1:]):
                values = [cell.findtext("s:v", namespaces=ns) if cell.get("t") != "inlineStr"
                          else cell.findtext("s:is/s:t", default="", namespaces=ns) for cell in row]
                self.assertEqual(values, ["" if source.get(f) is None else str(source[f]) for f in build.FIELDS])
            self.assertFalse(root.findall(".//s:f", ns), "Untrusted titles must never become formulas")
        self.assertEqual(base.with_suffix(".xlsx").read_bytes(), build.workbook(self.rows))

    def test_formula_safety_and_nulls(self):
        self.assertEqual(build.csv_cell(None), "")
        self.assertEqual(build.csv_cell(0), "0")
        for value in ("=1+1", "+formula", "-formula", "@formula", "\tformula", "\rformula"):
            self.assertTrue(build.csv_cell(value).startswith("'"))
        with ZipFile(BytesIO(build.workbook([{"title": "=1+1", "comments": 0}]))) as archive:
            sheet = archive.read("xl/worksheets/sheet1.xml").decode()
            self.assertIn('<t xml:space="preserve">=1+1</t>', sheet)
            self.assertNotIn("<f>", sheet)


if __name__ == "__main__":
    unittest.main()
