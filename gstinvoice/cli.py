"""Command-line entry point: gstinvoice invoice1.pdf scan.jpg -o books.xlsx"""
import argparse
import sys
from pathlib import Path

from . import export
from .parser import parse_invoice
from .reader import IMAGE_EXTS, read_text
from .validate import validate

SUPPORTED = IMAGE_EXTS | {".pdf"}


def collect(paths):
    for p in map(Path, paths):
        if p.is_dir():
            yield from sorted(f for f in p.iterdir() if f.suffix.lower() in SUPPORTED)
        else:
            yield p


def process_file(path):
    text, method = read_text(str(path))
    return validate(parse_invoice(text, source=Path(path).name, method=method))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gstinvoice", description="Extract and validate GST invoices.")
    ap.add_argument("inputs", nargs="+", help="PDF/image files or folders")
    ap.add_argument("-o", "--output", default="invoices.xlsx", help="Output file (.xlsx, .csv or .json)")
    args = ap.parse_args(argv)

    invoices = []
    for f in collect(args.inputs):
        try:
            invoices.append(process_file(f))
        except Exception as e:  # keep going on a bad file
            print(f"  ! {f}: {e}", file=sys.stderr)
    if not invoices:
        print("No invoices processed.", file=sys.stderr)
        return 1

    ext = Path(args.output).suffix.lower()
    {".xlsx": export.to_xlsx, ".csv": export.to_csv, ".json": export.to_json}.get(ext, export.to_xlsx)(invoices, args.output)

    for inv in invoices:
        print(f"[{export.status_of(inv):6}] {inv.source}  #{inv.invoice_number}  total={inv.total}")
        for f in inv.flags:
            if f["severity"] != "info":
                print(f"           - {f['message']}")
    print(f"\nWrote {len(invoices)} invoice(s) to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
