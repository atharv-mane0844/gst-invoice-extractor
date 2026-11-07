# GST Invoice Extractor

Turn Indian GST invoices (PDF or scanned image) into a clean spreadsheet, and **flag the ones that look wrong** before they reach your books.

Built for accountants and small businesses who still key invoices in by hand. The point isn't to beat general-purpose OCR; it's to know GST: GSTIN checksums, state codes, CGST/SGST vs IGST rules and standard rate slabs.

## What it extracts

Supplier name and GSTIN, buyer GSTIN, invoice number, invoice date (normalised to ISO), taxable value, CGST, SGST, IGST and grand total.

## What it checks

| Check | Why it matters |
|---|---|
| GSTIN format, state code and checksum | Catches OCR and typing errors |
| Taxable + taxes = total (₹1 rounding tolerance) | Catches arithmetic and misread digits |
| CGST equals SGST | They are always split equally |
| IGST vs CGST+SGST against supplier/buyer state | Wrong tax type means wrong input credit |
| Implied rate is a standard slab (0/3/5/12/18/28%) | Flags odd or mixed-rate invoices |

Each invoice gets a status: `OK`, `CHECK` (warnings) or `REVIEW` (errors). Excel output colours rows accordingly and adds a "Review flags" sheet.

## Quick start

```bash
sudo apt install tesseract-ocr          # only needed for scanned PDFs / images
pip install -r requirements.txt

python samples/make_samples.py          # fictional demo invoices
python -m gstinvoice.cli samples -o out.xlsx
python web/app.py                       # upload page at http://127.0.0.1:5000
pytest
```

Output format follows the extension: `.xlsx`, `.csv` or `.json`.

## Privacy

Invoices contain financial data. The web demo processes uploads in a temp folder and deletes them straight away; nothing is stored or sent anywhere. Run it on your own machine or server. Don't commit real client files (the `.gitignore` excludes `/private/`).

## Limitations (honest ones)

- Rule-based extraction works well on common layouts; unusual layouts will need review. Always check `REVIEW` rows.
- Line items and HSN codes are not extracted yet.
- OCR accuracy depends on scan quality. The checksum and arithmetic checks exist largely to catch OCR mistakes.
- Output is a generic CSV/Excel, not a verified import format for Tally or other software.
- This is a data-entry aid, not tax or legal advice.

## Roadmap

Line items and HSN, multi-rate invoices, e-invoice IRN/QR parsing, import templates for popular accounting tools, and layout learning from corrected rows.

## License

MIT
