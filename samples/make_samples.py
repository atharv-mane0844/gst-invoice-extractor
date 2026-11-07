"""Generate synthetic sample invoices (fictional companies) for demos and tests."""
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gstinvoice.gstin import compute_check_char  # noqa: E402


def make_gstin(state: str, pan: str, entity="1") -> str:
    base = f"{state}{pan}{entity}Z"
    return base + compute_check_char(base)


SUPPLIER_MH = make_gstin("27", "AABCS1234K")
BUYER_MH = make_gstin("27", "AAECB5678M")
BUYER_KA = make_gstin("29", "AAGCK9012P")


def draw(path, supplier, supplier_gstin, buyer, buyer_gstin, number, date, taxable, tax_lines, total):
    c = canvas.Canvas(str(path), pagesize=A4)
    y = 800
    def line(text, size=11, dy=18):
        nonlocal y
        c.setFont("Helvetica", size)
        c.drawString(50, y, text)
        y -= dy
    line(supplier, 15, 24)
    line("TAX INVOICE", 12, 22)
    line(f"GSTIN: {supplier_gstin}")
    line(f"Invoice No: {number}")
    line(f"Invoice Date: {date}", dy=26)
    line("Bill To:")
    line(buyer)
    line(f"Buyer GSTIN: {buyer_gstin}", dy=28)
    line("Description                       HSN      Qty     Amount", 10)
    line("Software consulting services      998314   1       " + f"{taxable:,.2f}", 10, 28)
    line(f"Taxable Value                                 {taxable:,.2f}")
    for label, amt in tax_lines:
        line(f"{label}                                  {amt:,.2f}")
    line(f"Grand Total                                   {total:,.2f}")
    c.save()


def main(out="samples"):
    out = Path(out)
    out.mkdir(exist_ok=True)
    draw(out / "invoice_intrastate_ok.pdf", "Sunrise Analytics Pvt Ltd", SUPPLIER_MH,
         "Bluewave Traders LLP", BUYER_MH, "SA/2026-27/0142", "14/10/2026", 50000,
         [("CGST @ 9%", 4500), ("SGST @ 9%", 4500)], 59000)
    draw(out / "invoice_interstate_ok.pdf", "Sunrise Analytics Pvt Ltd", SUPPLIER_MH,
         "Kaveri Retail Pvt Ltd", BUYER_KA, "SA/2026-27/0143", "21 Oct 2026", 125000,
         [("IGST @ 18%", 22500)], 147500)
    # Deliberately wrong: total doesn't add up, buyer GSTIN has a typo, IGST used within one state.
    bad_buyer = BUYER_MH[:-1] + ("A" if BUYER_MH[-1] != "A" else "B")
    draw(out / "invoice_with_errors.pdf", "Sunrise Analytics Pvt Ltd", SUPPLIER_MH,
         "Bluewave Traders LLP", bad_buyer, "SA/2026-27/0144", "02-11-2026", 80000,
         [("IGST @ 18%", 14400)], 96000)


if __name__ == "__main__":
    main()
