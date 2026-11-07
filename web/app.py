"""Minimal upload page for demos: drop invoices in, get a review table and an Excel file out.

Run:  python web/app.py   then open http://127.0.0.1:5000
Files are processed in a temp folder and deleted immediately; nothing is stored.
"""
import base64
import io
import sys
import tempfile
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, request  # noqa: E402

from gstinvoice import export  # noqa: E402
from gstinvoice.cli import SUPPORTED, process_file  # noqa: E402

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>GST Invoice Extractor</title>
<style>body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem}
table{border-collapse:collapse;width:100%%;font-size:14px}td,th{border:1px solid #ddd;padding:6px 8px;text-align:left}
.OK{background:#e6f4ea}.CHECK{background:#fff3cd}.REVIEW{background:#f8d7da}small{color:#555}</style>
<h1>GST Invoice Extractor</h1>
<p>Upload PDF or image invoices. Fields with problems are flagged for human review.</p>
<form method=post enctype=multipart/form-data>
<input type=file name=files multiple accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff" required>
<button>Extract</button><br><small>Files are processed in memory/temp and not stored.</small></form>
%s"""


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return PAGE % ""
    invoices = []
    with tempfile.TemporaryDirectory() as tmp:
        for f in request.files.getlist("files"):
            name = Path(f.filename or "upload").name
            if Path(name).suffix.lower() not in SUPPORTED:
                continue
            dest = Path(tmp) / name
            f.save(dest)
            try:
                invoices.append(process_file(dest))
            except Exception as e:
                return PAGE % f"<p>Could not read {escape(name)}: {escape(str(e))}</p>"
    if not invoices:
        return PAGE % "<p>No supported files uploaded.</p>"
    buf = io.BytesIO()
    export.to_xlsx(invoices, buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    rows = ""
    for inv in invoices:
        st = export.status_of(inv)
        flags = "<br>".join(escape(x["message"]) for x in inv.flags if x["severity"] != "info")
        rows += (f"<tr class={st}><td>{escape(inv.source)}</td><td>{escape(str(inv.invoice_number))}</td>"
                 f"<td>{escape(str(inv.invoice_date))}</td><td>{escape(str(inv.supplier_gstin))}</td>"
                 f"<td>{inv.taxable_value}</td><td>{inv.total}</td><td><b>{st}</b><br>{flags}</td></tr>")
    table = ("<table><tr><th>File</th><th>Invoice #</th><th>Date</th><th>Supplier GSTIN</th>"
             f"<th>Taxable</th><th>Total</th><th>Status</th></tr>{rows}</table>"
             f'<p><a download=invoices.xlsx href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}">Download Excel</a></p>')
    return PAGE % table


if __name__ == "__main__":
    app.run(debug=False)
