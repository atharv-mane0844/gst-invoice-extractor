"""Write extracted invoices to Excel, CSV or JSON."""
import csv
import json
from decimal import Decimal

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

COLUMNS = ["source", "invoice_number", "invoice_date", "supplier_name", "supplier_gstin",
           "buyer_gstin", "taxable_value", "cgst", "sgst", "igst", "other_tax", "total", "status"]
RED = PatternFill("solid", start_color="F8D7DA")
AMBER = PatternFill("solid", start_color="FFF3CD")


def _num(v):
    return float(v) if isinstance(v, Decimal) else v


def status_of(inv) -> str:
    sev = {f["severity"] for f in inv.flags}
    return "REVIEW" if "error" in sev else "CHECK" if "warning" in sev else "OK"


def _row(inv):
    d = {c: _num(getattr(inv, c, None)) for c in COLUMNS if c != "status"}
    d["status"] = status_of(inv)
    return d


def to_xlsx(invoices, path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Invoices"
    ws.append(COLUMNS)
    for c in ws[1]:
        c.font = Font(bold=True)
    for inv in invoices:
        row = _row(inv)
        ws.append([row[c] for c in COLUMNS])
        fill = {"REVIEW": RED, "CHECK": AMBER}.get(row["status"])
        if fill:
            for c in ws[ws.max_row]:
                c.fill = fill
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = min(40, max(12, max(len(str(c.value or "")) for c in col) + 2))
    fl = wb.create_sheet("Review flags")
    fl.append(["source", "invoice_number", "severity", "code", "message"])
    for c in fl[1]:
        c.font = Font(bold=True)
    for inv in invoices:
        for f in inv.flags:
            fl.append([inv.source, inv.invoice_number, f["severity"], f["code"], f["message"]])
    for letter, w in zip("ABCDE", (28, 18, 10, 26, 90)):
        fl.column_dimensions[letter].width = w
    wb.save(path)


def to_csv(invoices, path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for inv in invoices:
            w.writerow(_row(inv))


def to_json(invoices, path):
    out = [{**_row(i), "flags": i.flags} for i in invoices]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
