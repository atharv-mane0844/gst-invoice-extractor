"""Rule-based field extraction from invoice text."""
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .gstin import GSTIN_RE

AMOUNT_RE = re.compile(r"(?<![\w.])(?:₹|Rs\.?|INR)?\s*(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)(?![\w])")


@dataclass
class Invoice:
    source: str = ""
    method: str = ""
    supplier_name: str | None = None
    supplier_gstin: str | None = None
    buyer_gstin: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None  # ISO yyyy-mm-dd
    taxable_value: Decimal | None = None
    cgst: Decimal | None = None
    sgst: Decimal | None = None
    igst: Decimal | None = None
    other_tax: Decimal | None = None  # a plain 'Tax'/'VAT' line when no CGST/SGST/IGST split exists
    total: Decimal | None = None
    flags: list = field(default_factory=list)  # filled by validate.py

    @property
    def needs_review(self) -> bool:
        return any(f["severity"] in ("error", "warning") for f in self.flags)


def _to_decimal(s: str) -> Decimal | None:
    try:
        return Decimal(s.replace(",", ""))
    except InvalidOperation:
        return None


def _last_amount(line: str) -> Decimal | None:
    # Drop percentage tokens like "9%" or "@ 18 %" so rates aren't mistaken for amounts.
    cleaned = re.sub(r"\d+(?:\.\d+)?\s*%", " ", line)
    matches = AMOUNT_RE.findall(cleaned)
    return _to_decimal(matches[-1]) if matches else None


def _find_amount(lines, patterns, exclude=None):
    for pat in patterns:
        rx = re.compile(pat, re.I)
        for ln in lines:
            if rx.search(ln) and not (exclude and re.search(exclude, ln, re.I)):
                val = _last_amount(ln)
                if val is not None:
                    return val
    return None


DATE_FORMATS = ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y",
                "%d %b %Y", "%d %B %Y", "%d %b, %Y", "%d %B, %Y",
                "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y", "%Y-%m-%d")
DATE_TOKEN_RE = re.compile(
    r"\b(?:\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}\s+[A-Za-z]{3,9}\.?,?\s+\d{4}|[A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{4})\b")


def _try_date(token: str) -> str | None:
    token = token.strip().rstrip(".")
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(token, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_date(text: str) -> str | None:
    # Prefer a date sitting right after an "Invoice Date" style label; ignore due dates.
    for label in (r"invoice\s*date", r"inv\.?\s*date", r"date\s*of\s*issue", r"bill\s*date", r"\bdate\b"):
        for m in re.finditer(label + r"\s*[:\-]?\s*(.{0,30})", text, re.I):
            tok = DATE_TOKEN_RE.search(m.group(1))
            if tok and (d := _try_date(tok.group())):
                return d
    for tok in DATE_TOKEN_RE.finditer(text):
        if d := _try_date(tok.group()):
            return d
    return None


def _parse_invoice_number(text: str) -> str | None:
    m = re.search(
        r"(?:invoice|inv|bill)\s*(?:no|number|num|#)\.?\s*[:\-#]?\s*([A-Za-z0-9][A-Za-z0-9/\-_.]{1,24})",
        text, re.I)
    return m.group(1).rstrip(".") if m else None


def _assign_gstins(text: str) -> tuple[str | None, str | None]:
    found = [(m.start(), m.group()) for m in GSTIN_RE.finditer(text.upper())]
    if not found:
        return None, None
    buyer = supplier = None
    for pos, g in found:
        context = text[max(0, pos - 120):pos].lower()
        if re.search(r"bill(?:ed)?\s*to|buyer|consignee|ship\s*to|customer|recipient", context):
            buyer = buyer or g
        elif supplier is None:
            supplier = g
    if supplier is None:
        supplier = found[0][1]
    if buyer is None:
        others = [g for _, g in found if g != supplier]
        buyer = others[0] if others else None
    return supplier, buyer


SKIP_NAME_RE = re.compile(
    r"^(?:tax\s+)?invoice|^payment|^page\b|^thanks?|gstin|^date\b|^order|^due\b|^bill\s*to|^to:|^from:|^original|^duplicate",
    re.I)


def _clean_name(name):
    """Two-column layouts glue the right-hand table onto the line; cut at the first label."""
    if not name:
        return name
    return re.split(r"\s+(?:invoice|order|due|date|po|ph|tel|phone|gstin|pan)\b", name, maxsplit=1, flags=re.I)[0].strip()


def _supplier_name(lines):
    for i, ln in enumerate(lines):  # an explicit "From:" block wins
        if re.fullmatch(r"from\s*:?", ln, re.I) and i + 1 < len(lines):
            return _clean_name(lines[i + 1])
    return _clean_name(next((ln for ln in lines if re.search(r"[A-Za-z]{3}", ln) and not SKIP_NAME_RE.search(ln)), None))


def parse_invoice(text: str, source: str = "", method: str = "") -> Invoice:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    supplier, buyer = _assign_gstins(text)
    name = _supplier_name(lines)
    return Invoice(
        source=source,
        method=method,
        supplier_name=name,
        supplier_gstin=supplier,
        buyer_gstin=buyer,
        invoice_number=_parse_invoice_number(text),
        invoice_date=_parse_date(text),
        taxable_value=_find_amount(lines, [r"taxable\s*(?:value|amount)", r"sub\s*-?\s*total", r"net\s*amount"]),
        cgst=_find_amount(lines, [r"\bcgst\b"], exclude=r"total\s+(?:tax|gst)"),
        sgst=_find_amount(lines, [r"\b[su]t?gst\b"], exclude=r"total\s+(?:tax|gst)"),
        igst=_find_amount(lines, [r"\bigst\b"], exclude=r"total\s+(?:tax|gst)"),
        other_tax=_find_amount(lines, [r"^(?:tax|vat|gst)\b"], exclude=r"taxable|total\s+tax"),
        total=_find_amount(lines, [r"grand\s*total", r"total\s*(?:invoice\s*)?(?:amount|value)", r"amount\s*payable",
                                   r"invoice\s*total", r"^total\b"], exclude=r"taxable|tax\b"),
    )
