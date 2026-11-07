"""Sanity checks that flag fields a human should look at before posting to books."""
from decimal import Decimal

from .gstin import is_valid_gstin, state_of
from .parser import Invoice

STANDARD_RATES = {Decimal(x) for x in ("0", "0.25", "3", "5", "12", "18", "28")}
TOLERANCE = Decimal("1.00")  # invoices round to the nearest rupee


def _flag(inv: Invoice, severity: str, code: str, msg: str):
    inv.flags.append({"severity": severity, "code": code, "message": msg})


def validate(inv: Invoice) -> Invoice:
    inv.flags = []
    for label, g in (("Supplier", inv.supplier_gstin), ("Buyer", inv.buyer_gstin)):
        if g is None:
            sev = "error" if label == "Supplier" else "info"
            _flag(inv, sev, f"{label.lower()}_gstin_missing", f"{label} GSTIN not found.")
        elif not is_valid_gstin(g):
            _flag(inv, "error", f"{label.lower()}_gstin_invalid",
                  f"{label} GSTIN {g} fails format/checksum validation (possible OCR or typing error).")

    for fld, label in (("invoice_number", "Invoice number"), ("invoice_date", "Invoice date"),
                       ("taxable_value", "Taxable value"), ("total", "Total")):
        if getattr(inv, fld) is None:
            _flag(inv, "error", f"{fld}_missing", f"{label} not found.")

    cg, sg, ig = (inv.cgst or Decimal(0)), (inv.sgst or Decimal(0)), (inv.igst or Decimal(0))
    tax = cg + sg + ig
    if not tax and inv.other_tax:  # plain 'Tax' line, no GST split available
        tax = inv.other_tax

    if inv.cgst is not None and inv.sgst is not None and abs(inv.cgst - inv.sgst) > Decimal("0.02"):
        _flag(inv, "error", "cgst_sgst_mismatch", f"CGST ({inv.cgst}) and SGST ({inv.sgst}) should be equal.")
    if (cg or sg) and ig:
        _flag(inv, "error", "mixed_tax_types", "Invoice shows both CGST/SGST and IGST.")

    if inv.taxable_value is not None and inv.total is not None:
        expected = inv.taxable_value + tax
        if abs(expected - inv.total) > TOLERANCE:
            _flag(inv, "error", "total_mismatch",
                  f"Taxable {inv.taxable_value} + tax {tax} = {expected}, but invoice total is {inv.total}.")

    if inv.taxable_value and tax:
        rate = (tax / inv.taxable_value * 100).quantize(Decimal("0.1"))
        if not any(abs(rate - r) <= Decimal("0.6") for r in STANDARD_RATES):
            _flag(inv, "warning", "unusual_rate",
                  f"Implied GST rate is {rate}%, which is not a standard slab (0/3/5/12/18/28). "
                  "May be a mixed-rate invoice.")

    s_state, b_state = state_of(inv.supplier_gstin), state_of(inv.buyer_gstin)
    if s_state and b_state:
        if s_state == b_state and ig:
            _flag(inv, "warning", "igst_on_intrastate",
                  f"Both parties are in {s_state}, so CGST+SGST is expected, but IGST was charged.")
        if s_state != b_state and (cg or sg):
            _flag(inv, "warning", "gst_on_interstate",
                  f"Supplier ({s_state}) and buyer ({b_state}) differ, so IGST is expected, but CGST/SGST was charged.")
    return inv
