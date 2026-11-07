import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "samples"))
sys.path.insert(0, str(ROOT / "web"))
import make_samples  # noqa: E402
from app import app  # noqa: E402


def test_upload_flow(tmp_path):
    make_samples.main(str(tmp_path))
    client = app.test_client()
    assert client.get("/").status_code == 200
    data = {"files": [(io.BytesIO((tmp_path / "invoice_with_errors.pdf").read_bytes()), "bad.pdf")]}
    r = client.post("/", data=data, content_type="multipart/form-data")
    body = r.get_data(as_text=True)
    assert "REVIEW" in body and "Download Excel" in body
