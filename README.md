# Bangladesh NID Extraction API

An AI-powered REST API that reads both sides of a Bangladesh National ID (NID) card, extracts all key fields, translates any Bengali text into natural English, and returns clean, structured JSON. I couldn't make it dockerized due to my local machine isn't supporting WSL. I've tried thousand times to install WSL but my laptop doesn't supporting virtual machine that's why I've blindly giving the docker file without testing it on my local pc.

---

## 1. Problem Statement

Bangladesh NID cards contain critical identity information (name, parents' names, date of birth, NID number, address) printed primarily in Bengali, in a semi-structured layout that varies across old laminated cards and newer smart cards. Manually transcribing and translating this data for onboarding, KYC, or verification workflows is slow and error-prone.

This project solves that problem by accepting a photo of the **front** and **back** of an NID card and returning a single structured JSON object containing all fields already translated into English, ready to be consumed by downstream systems (databases, KYC pipelines, admin dashboards) without any manual data entry.

---

## 2. Functionality Overview

### Primary Functionality

| S.N | Feature | Description |
|---|---|---|
| 1 | Dual-image upload | Accepts front and back NID images (JPG/JPEG/PNG) via a single REST endpoint |
| 2 | AI-based OCR | Reads all visible text from both images using a multimodal (vision) AI model |
| 3 | Bengali → English translation | Translates Name, Father's Name, Mother's Name, and Address with meaning preserved (not word-for-word) |
| 4 | Structured JSON output | Returns a fixed schema: name, fatherName, motherName, dateOfBirth, nidNumber, address |
| 5 | Field-level validation | Normalizes date formats and validates NID number length before returning data |

### Secondary Functionality

| # | Feature | Description |
|---|---|---|
| 1 | Missing-image detection | Flags clearly if front and/or back image was not provided |
| 2 | File-type / corruption checks | Rejects unsupported formats, empty files, oversized files, and unreadable/corrupted images before calling the AI |
| 3 | Resolution guardrails | Rejects images that are too small (unreadable) or unreasonably large (cost/performance risk) |
| 4 | Non-NID detection | Flags when an uploaded image does not appear to be a Bangladesh NID card at all |
| 5 | Front/back swap detection | Flags when the uploaded "front" image looks like a back image (or vice versa) |
| 6 | Partial-extraction handling | Returns whatever fields could be read, with a list of missing fields and a warning, instead of failing the whole request |
| 7 | Duplicate NID detection | Prevents the same NID number from being stored twice |
| 8 | Health check | A lightweight `/health` endpoint for uptime monitoring |
| 9 | Automated tests | `pytest` test suite covering validation edge cases without requiring a live API key |

---

## 3. Codebase Structure

```text
nid_project/
├── app/
│   ├── main.py            # FastAPI app, routes, and image validation (vr_function)
│   ├── nid_extractor.py   # AI vision call: image compression, prompt, Gemini API integration
│   ├── schemas.py         # Pydantic response models (NIDData, ExtractionResponse)
│   ├── storage.py         # Lightweight JSON-file repository with file locking
│   └── validation.py      # Post-extraction validation: NID format, date normalization, missing-field logic
├── tests/
│   └── test_api.py        # Automated tests for validation/error paths
├── data/
│   └── data.json          # Local storage file (created automatically at runtime)
├── requirements.txt
├── .env.example
└── README.md
```

### What each file is responsible for

- **`app/main.py`** — Defines the FastAPI application and the `POST /api/v1/extract-nid`
  endpoint. Contains `vr_function`, which validates each uploaded file (missing file,
  wrong extension, empty file, oversized file, corrupted image, resolution limits)
  *before* any AI call is made. Also orchestrates the overall request flow: validate →
  extract → validate fields → check duplicates → store → respond.

- **`app/nid_extractor.py`** — Owns all communication with the AI provider (Google
  Gemini). Compresses/resizes images to control token cost, builds the system prompt
  that instructs the model to extract and translate fields, calls the Gemini API, and
  safely parses the JSON response (handling empty responses and malformed JSON).

- **`app/schemas.py`** — Defines the Pydantic models that describe the exact shape of
  API responses (`NIDData` for the extracted fields, `ExtractionResponse` for the full
  API response envelope, including flags like `isValidNid` and `sidesSwapped`).

- **`app/storage.py`** — A minimal file-based repository (`data/data.json`) used to
  check for and prevent duplicate NID submissions. Uses `filelock` to avoid race
  conditions when multiple requests write concurrently.

- **`app/validation.py`** — Runs *after* the AI extraction step. Normalizes the date of
  birth into `YYYY-MM-DD`, validates the NID number's digit length, and determines which
  fields (if any) are missing — building the final `ExtractionResponse`.

- **`tests/test_api.py`** — Automated tests using FastAPI's `TestClient`. These only
  exercise the validation logic in `main.py` (missing images, wrong file type, corrupted
  image), so they run without needing a real `GEMINI_API_KEY`.

---

## 4. Edge Cases Handled

| Category | Edge Case | Where Handled |
|---|---|---|
| Upload | Missing front and/or back image | `main.py` |
| Upload | Unsupported file type (not jpg/jpeg/png) | `main.py` |
| Upload | Empty (0-byte) file | `main.py` |
| Upload | File exceeds size limit (10MB) | `main.py` |
| Upload | Corrupted / unreadable image | `main.py` (PIL `verify()` + `load()`) |
| Upload | File extension doesn't match actual image format | `main.py` |
| Upload | Resolution too large (performance/cost risk) | `main.py` |
| Upload | Resolution too small (unreliable OCR) | `main.py` |
| AI Response | Empty response from the model | `nid_extractor.py` |
| AI Response | Malformed / non-JSON output | `nid_extractor.py` |
| AI Response | Markdown-fenced JSON | `nid_extractor.py` |
| AI Response | Rate limit / quota errors | `nid_extractor.py` |
| Content | Uploaded image is not actually a Bangladesh NID card | `nid_extractor.py` + `main.py` (`isValidNid`) |
| Content | Front and back images appear swapped | `nid_extractor.py` + `main.py` (`sidesSwapped`) |
| Data Quality | NID number has an implausible digit count | `validation.py` |
| Data Quality | Date of birth in an unexpected format or an implausible date | `validation.py` |
| Data Quality | Partial extraction (some fields unreadable) | `validation.py` (returns `missingFields`, `warnings`, `retryRequired`) |
| Data Integrity | Duplicate NID number submitted twice | `storage.py` + `main.py` |
| Data Integrity | Concurrent writes to local storage | `storage.py` (file locking) |

### Known limitations (documented intentionally, not hidden)
- Present Address and Permanent Address are not distingushed in Bangladesh National ID card that's why currently returned as a single combined
  `address` field rather than two separate fields.
- Extracted data is stored in a local unencrypted JSON file — suitable for a
  demo/prototype, not for production-grade PII storage.
- No automatic server-side retry loop exists yet; `retryRequired`/`retrySide` are
  returned as signals for the client to act on.

---

## 5. Why Not a Traditional OCR Library (e.g., Tesseract, Baidu OCR, Google Cloud Vision)?

Traditional OCR engines were seriously considered and deliberately not used, for the
following reasons:

1. **Bengali script accuracy varies widely across OCR engines.** Several OCR
   services are trained and tuned primarily on Latin-script or Chinese-script data
   (e.g., Baidu OCR), and do not reliably handle Bengali conjuncts (যুক্তাক্ষর) or
   NID-specific print layouts.

2. **Traditional OCR only extracts raw text — it does not understand structure.**
   A generic OCR engine returns a flat block of text; it cannot on its own determine
   which line is the "Father's Name" versus "Address" versus a disclaimer sentence.
   That would require building and maintaining a separate, brittle layout-parsing
   pipeline — especially difficult given that Bangladesh has multiple NID card
   layouts in circulation (old laminated cards vs. newer smart cards).

3. **Translation would require a second, separate step.** OCR only reads text; it
   doesn't translate it. Using a traditional OCR + a separate translation API (e.g.,
   Google Translate) typically produces literal, word-for-word translations rather
   than natural, meaning-preserving translations — which the project specifically
   requires for fields like Address.

4. **A single multimodal AI model handles all three steps at once.** By using a
   vision-capable large language model (Gemini), the same API call performs OCR,
   field-level structuring, and context-aware translation together — reducing
   pipeline complexity, the number of failure points, and the amount of custom
   parsing logic needed.

The trade-off: this approach depends on a third-party AI provider's availability and
rate limits (a real issue encountered during development — see `AI_USAGE.md` for
details), whereas a self-hosted OCR engine would not have that dependency. For the
scope and reliability needs of this project, the accuracy and simplicity gains of a
single multimodal call outweighed that trade-off.

---

## Technology Stack

- **Backend Framework:** FastAPI (Python)
- **AI/Vision Model:** Google Gemini (`gemini-3.5-flash`), accessed via `google-genai`
- **Image Processing:** Pillow (validation, compression, resizing)
- **Data Validation:** Pydantic
- **Local Storage:** JSON file with `filelock` for concurrency safety
- **Testing:** Pytest + FastAPI `TestClient`

## Build & Run Instructions

\`\`\`bash
# 1. Clone the repository
git clone <repo-url>
cd nid_project

# 2. Create and activate a virtual environment
python -m venv venv
venv\\Scripts\\activate      # Windows
source venv/bin/activate    # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# then edit .env and add your GEMINI_API_KEY

# 5. Run the server
uvicorn app.main:app --reload
\`\`\`

The API will be available at `http://127.0.0.1:8000`, with interactive Swagger docs at
`http://127.0.0.1:8000/docs`.

## Running Tests

\`\`\`bash
pip install pytest httpx
pytest tests/test_api.py -v
\`\`\`

## API Endpoint

- `POST /api/v1/extract-nid` — accepts `front_image` and `back_image` as multipart form
  fields, returns structured JSON. See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
  for full request/response details.
- `GET /health` — basic health check.

## Additional Documentation

- [AI Usage & Prompting Documentation](./AI_USAGE.md)
- [API Documentation](./API_DOCUMENTATION.md)
