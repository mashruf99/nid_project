#app/main.py
from dotenv import load_dotenv
load_dotenv()
import io
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from app.nid_extractor import extract_nid_data
from app.schemas import ExtractionResponse, NIDData
from app.storage import repository
from app.validation import build_extraction_response


ALLOWED_EXT = {"jpg", "jpeg", "png"}
MAX_SIZE = 10 * 1024 * 1024  

app = FastAPI(title="Bangladesh NID Extraction API", version="1.0.0")


def _ext(filename: str) -> str:
    return filename.lower().rsplit(".", 1)[-1] if "." in filename else ""





def vr_function(upload: UploadFile, label: str, errors: list) -> bytes:
    if upload is None:
        errors.append(f"{label} image is missing. Please upload both front and back images.")
        return b""

    if _ext(upload.filename or "") not in ALLOWED_EXT:
        errors.append(f"{label} image has an unsupported file type. Allowed: jpg, jpeg, png.")
        return b""

    raw = upload.file.read()
    if not raw:
        errors.append(f"{label} image file is empty.")
        return b""
    if len(raw) > MAX_SIZE:
        errors.append(f"{label} image exceeds 10MB limit.")
        return b""

    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()
        img2 = Image.open(io.BytesIO(raw))
        img2.load()
        if img2.format not in ("JPEG", "PNG"):
            errors.append(f"{label} image is not a valid JPG/PNG file.")
            return b""
        width, height = img2.size
        if width > 6000 or height > 6000:
            errors.append(f"{label} image resolution too large ({width}x{height}). Max 6000x6000.")
            return b""
        if width < 200 or height < 200:
            errors.append(f"{label} image resolution too small to read reliably ({width}x{height}).")
            return b""
    except (UnidentifiedImageError, OSError, SyntaxError):
        errors.append(f"{label} image is unreadable or corrupted. Please re-upload a clear photo.")
        return b""

    return raw


@app.get("/health")
def health():
    return {"status": "ok"}



@app.post("/api/v1/extract-nid", response_model=ExtractionResponse)
async def extract_nid(
    front_image: UploadFile = File(None),
    back_image: UploadFile = File(None),
):
    errors: list = []
    front_bytes = vr_function(front_image, "Front", errors)
    back_bytes = vr_function(back_image, "Back", errors)

    if errors:
        return ExtractionResponse(success=False, data=None, errors=errors)

    try:
        fields = extract_nid_data(front_bytes, front_image.filename, back_bytes, back_image.filename)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if not fields.get("isValidNid", True):
        return ExtractionResponse(success=False, data=None, errors=["Uploaded images do not appear to be a Bangladesh NID card."])

    response = build_extraction_response(fields)
    if fields.get("sidesSwapped"):
        response.warnings.append("Front and back images may be swapped. Please verify.")

    if not response.success or not response.data.nidNumber:
        return response  

    if repository.exists(response.data.nidNumber):
        return ExtractionResponse(
            success=False,
            data=response.data,
            errors=["This NID already exists."]
        )
    repository.save(response.data.model_dump())
    return response
