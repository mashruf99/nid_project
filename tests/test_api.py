import io
from fastapi.testclient import TestClient
from PIL import Image
from app.main import app

client = TestClient(app)


def _fake_png_bytes(color=(255, 0, 0)):
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color=color).save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_missing_both_images():
    resp = client.post("/api/v1/extract-nid")
    body = resp.json()
    assert body["success"] is False
    assert any("Front image is missing" in e for e in body["errors"])
    assert any("Back image is missing" in e for e in body["errors"])


def test_missing_one_image():
    files = {"front_image": ("front.png", _fake_png_bytes(), "image/png")}
    resp = client.post("/api/v1/extract-nid", files=files)
    body = resp.json()
    assert body["success"] is False
    assert any("Back image is missing" in e for e in body["errors"])


def test_unsupported_file_type():
    files = {
        "front_image": ("front.bmp", _fake_png_bytes(), "image/bmp"),
        "back_image": ("back.png", _fake_png_bytes(), "image/png"),
    }
    resp = client.post("/api/v1/extract-nid", files=files)
    body = resp.json()
    assert body["success"] is False
    assert any("unsupported file type" in e for e in body["errors"])


def test_corrupt_image():
    files = {
        "front_image": ("front.png", b"not-a-real-image", "image/png"),
        "back_image": ("back.png", _fake_png_bytes(), "image/png"),
    }
    resp = client.post("/api/v1/extract-nid", files=files)
    body = resp.json()
    assert body["success"] is False
    assert any("unreadable or corrupted" in e for e in body["errors"])
