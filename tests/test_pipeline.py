import sys
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "samples"))
import make_samples  # noqa: E402

from gstinvoice import export  # noqa: E402
from gstinvoice.cli import process_file  # noqa: E402
from gstinvoice.parser import parse_invoice  # noqa: E402
from gstinvoice.validate import validate  # noqa: E402


@pytest.fixture(scope="module")
def samples(tmp_path_factory):
    d = tmp_path_factory.mktemp("samples")
    make_samples.main(str(d))
    return d


def test_intrastate_clean(samples):
    inv = process_file(samples / "invoice_intrastate_ok.pdf")
    assert inv.invoice_number == "SA/2026-27/0142"
    assert inv.invoice_date == "2026-10-14"
    assert inv.taxable_value == Decimal("50000.00")
    assert inv.cgst == inv.sgst == Decimal("4500.00")
    assert inv.total == Decimal("59000.00")
    assert export.status_of(inv) == "OK"


def test_interstate_clean(samples):
    inv = process_file(samples / "invoice_interstate_ok.pdf")
    assert inv.igst == Decimal("22500.00")
    assert inv.invoice_date == "2026-10-21"
    assert export.status_of(inv) == "OK"


def test_errors_are_flagged(samples):
    inv = process_file(samples / "invoice_with_errors.pdf")
    codes = {f["code"] for f in inv.flags}
    assert {"buyer_gstin_invalid", "total_mismatch", "igst_on_intrastate"} <= codes
    assert export.status_of(inv) == "REVIEW"


def test_missing_fields_flagged():
    inv = validate(parse_invoice("some random text with no invoice data"))
    codes = {f["code"] for f in inv.flags}
    assert {"supplier_gstin_missing", "total_missing", "invoice_number_missing"} <= codes


def test_exports(samples, tmp_path):
    invs = [process_file(p) for p in sorted(samples.glob("*.pdf"))]
    export.to_xlsx(invs, tmp_path / "o.xlsx")
    export.to_csv(invs, tmp_path / "o.csv")
    export.to_json(invs, tmp_path / "o.json")
    assert all((tmp_path / f"o.{e}").stat().st_size > 0 for e in ("xlsx", "csv", "json"))


SLICED_TEXT = """Invoice
Payment is due within 30 days from date of invoice. Late payment is subject to fees of 5% per month.
Thanks for choosing DEMO - Sliced Invoices | admin@slicedinvoices.com
Page 1/1
From:
DEMO - Sliced Invoices Order Number 12345
Suite 5A-1204
Invoice Number INV-3337
Invoice Date January 25, 2016
Due Date January 31, 2016
Total Due $93.50
To:
Test Business
Sub Total $85.00
Tax $8.50
Total $93.50"""


def test_non_gst_layout_regression():
    """Layout from a real third-party sample: month-first dates, plain 'Tax' line, 'From:' block."""
    inv = validate(parse_invoice(SLICED_TEXT))
    assert inv.supplier_name == "DEMO - Sliced Invoices"
    assert inv.invoice_date == "2016-01-25"  # not the due date
    assert inv.invoice_number == "INV-3337"
    assert (inv.taxable_value, inv.other_tax, inv.total) == (Decimal("85.00"), Decimal("8.50"), Decimal("93.50"))
    assert "total_mismatch" not in {f["code"] for f in inv.flags}
