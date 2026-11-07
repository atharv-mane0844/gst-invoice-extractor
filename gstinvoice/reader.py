"""Turn a PDF or image into text. Text PDFs are read directly; scans fall back to OCR."""
from pathlib import Path

import pdfplumber

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def _ocr(image) -> str:
    import pytesseract
    return pytesseract.image_to_string(image, config="--psm 6")


def read_text(path: str) -> tuple[str, str]:
    """Return (text, method) where method is 'pdf-text', 'pdf-ocr' or 'image-ocr'."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".pdf":
        with pdfplumber.open(p) as pdf:
            text = "\n".join((page.extract_text() or "") for page in pdf.pages)
            if len(text.strip()) >= 30:
                return text, "pdf-text"
            pages = [_ocr(page.to_image(resolution=300).original) for page in pdf.pages]
            return "\n".join(pages), "pdf-ocr"
    if ext in IMAGE_EXTS:
        from PIL import Image
        return _ocr(Image.open(p)), "image-ocr"
    raise ValueError(f"Unsupported file type: {ext}")
