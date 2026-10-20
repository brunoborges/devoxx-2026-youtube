"""Build the standalone dashboard using only the Python standard library."""

import csv
from io import BytesIO, StringIO
import json
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


FIELDS = [
    "title", "url", "date_published", "views", "likes", "captured_at_utc",
    "published_at", "channel_id", "comments", "comments_status",
    "comments_captured_at_utc", "comments_source", "comments_reported_text", "comments_error",
]


def csv_cell(value):
    value = "" if value is None else str(value)
    return "'" + value if value.startswith(("=", "+", "-", "@", "\t", "\r")) else value


def workbook(data):
    rows = [FIELDS] + [[row.get(field) for field in FIELDS] for row in data]
    sheet_rows = []
    for index, row in enumerate(rows, 1):
        cells = []
        for column, value in enumerate(row):
            ref = f"{chr(65 + column)}{index}"
            if isinstance(value, int):
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                content = escape("" if value is None else str(value))
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{content}</t></is></c>')
        sheet_rows.append(f'<row r="{index}">{"".join(cells)}</row>')
    namespace = "http://schemas.openxmlformats.org"
    files = {
        "[Content_Types].xml": (
            f'<Types xmlns="{namespace}/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'
        ),
        "_rels/.rels": (
            f'<Relationships xmlns="{namespace}/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{namespace}/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        ),
        "xl/workbook.xml": (
            f'<workbook xmlns="{namespace}/spreadsheetml/2006/main" xmlns:r="{namespace}/officeDocument/2006/relationships">'
            '<sheets><sheet name="Videos" sheetId="1" r:id="rId1"/></sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            f'<Relationships xmlns="{namespace}/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{namespace}/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>'
        ),
        "xl/worksheets/sheet1.xml": (
            f'<worksheet xmlns="{namespace}/spreadsheetml/2006/main">'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" state="frozen"/></sheetView></sheetViews>'
            f'<sheetData>{"".join(sheet_rows)}</sheetData>'
            f'<autoFilter ref="A1:N{len(rows)}"/></worksheet>'
        ),
    }
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        for name, content in files.items():
            info = ZipInfo(name, date_time=(2026, 10, 20, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content.encode("utf-8"))
    return output.getvalue()


def export_data(root, data):
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(FIELDS)
    writer.writerows([csv_cell(row.get(field)) for field in FIELDS] for row in data)
    target = root / "data/devoxx-videos-since-2026-10-01"
    target.with_suffix(".csv").write_bytes(output.getvalue().encode("utf-8-sig"))
    target.with_suffix(".xlsx").write_bytes(workbook(data))


def main():
    root = Path(__file__).resolve().parent.parent
    data = json.loads((root / "data/devoxx_stats.json").read_text(encoding="utf-8"))
    template = (root / "src/devoxx-dashboard.template.html").read_text(encoding="utf-8")
    if template.count("__DATA__") != 1:
        raise ValueError("The dashboard template must contain exactly one __DATA__ placeholder")
    encoded = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    html = template.replace("__DATA__", encoded)
    (root / "index.html").write_bytes(html.encode("utf-8"))
    export_data(root, data)
    print(f"Built index.html: {len(html.encode('utf-8'))} bytes, {len(data)} videos")


if __name__ == "__main__":
    main()
