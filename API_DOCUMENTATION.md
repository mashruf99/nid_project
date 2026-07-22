# API Documentation

Base URL (local development): `http://127.0.0.1:8000`

---

## Authentication

No client-facing authentication is required to call this API. The AI provider (Google
Gemini) API key is configured server-side via the `GEMINI_API_KEY` environment variable
and is never exposed to the client.

---

## Endpoints

### 1. Health Check

GET /health


Checks whether the API server is running.

**Response `200 OK`**
```json
{
  "status": "ok"
}
```

---

### 2. Extract NID Data

POST /api/v1/extract-nid


Accepts the front and back images of a Bangladesh NID card and returns extracted,
translated, and validated data as structured JSON.

#### Request

- **Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `front_image` | file (jpg / jpeg / png) | Yes | Front side of the NID card |
| `back_image` | file (jpg / jpeg / png) | Yes | Back side of the NID card |

**Constraints on each image:**
- Allowed formats: `.jpg`, `.jpeg`, `.png`
- Max file size: 10 MB
- Min resolution: 200×200 px
- Max resolution: 6000×6000 px

**Example request (`curl`)**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/extract-nid \
  -F "front_image=@front.jpg;type=image/jpeg" \
  -F "back_image=@back.jpg;type=image/jpeg"
```

---

#### Response Schema

All responses (success or failure) follow this envelope:

```json
{
  "success": true,
  "data": {
    "name": "string | null",
    "fatherName": "string | null",
    "motherName": "string | null",
    "dateOfBirth": "string | null",
    "nidNumber": "string | null",
    "address": "string | null"
  },
  "missingFields": ["string"],
  "retryRequired": false,
  "retrySide": "front | back | null",
  "warnings": ["string"],
  "errors": ["string"],
  "isValidNid": true,
  "sidesSwapped": false
}
```

| Field | Type | Description |
|---|---|---|
| `success` | boolean | `true` only if all expected fields were extracted and no errors occurred |
| `data` | object \| null | Extracted NID fields (English), or `null` if extraction did not run at all |
| `missingFields` | array of strings | Names of fields that could not be read from either image |
| `retryRequired` | boolean | `true` if the client should consider re-uploading a clearer image |
| `retrySide` | string \| null | Which side (`"front"`/`"back"`) is likely responsible for the missing data |
| `warnings` | array of strings | Non-fatal issues (e.g., a specific field couldn't be read, or sides look swapped) |
| `errors` | array of strings | Fatal issues that prevented processing (e.g., missing image, invalid file type) |
| `isValidNid` | boolean | `false` if the uploaded images don't appear to be a Bangladesh NID card at all |
| `sidesSwapped` | boolean | `true` if the front/back images appear to be swapped |

---

#### Example: Successful Extraction

**`200 OK`**
```json
{
  "success": true,
  "data": {
    "name": "Kazi Shafiul Islam",
    "fatherName": "Kazi Nazrul Islam",
    "motherName": "Selina Akter",
    "dateOfBirth": "2002-07-15",
    "nidNumber": "1515238218",
    "address": "House 37, Road 8, Mirpur-2, Block-H, Dhaka North City Corporation, Dhaka"
  },
  "missingFields": [],
  "retryRequired": false,
  "retrySide": null,
  "warnings": [],
  "errors": [],
  "isValidNid": true,
  "sidesSwapped": false
}
```

---

#### Example: Missing Images

**`200 OK`** *(request accepted, but validation failed — not an HTTP error)*
```json
{
  "success": false,
  "data": null,
  "missingFields": [],
  "retryRequired": false,
  "retrySide": null,
  "warnings": [],
  "errors": [
    "Front image is missing. Please upload both front and back images.",
    "Back image is missing. Please upload both front and back images."
  ],
  "isValidNid": true,
  "sidesSwapped": false
}
```

---

#### Example: Unsupported File Type

**`200 OK`**
```json
{
  "success": false,
  "data": null,
  "errors": [
    "Front image has an unsupported file type. Allowed: jpg, jpeg, png."
  ],
  "missingFields": [],
  "retryRequired": false,
  "retrySide": null,
  "warnings": [],
  "isValidNid": true,
  "sidesSwapped": false
}
```

---

#### Example: Corrupted / Unreadable Image

**`200 OK`**
```json
{
  "success": false,
  "data": null,
  "errors": [
    "Front image is unreadable or corrupted. Please re-upload a clear photo."
  ],
  "missingFields": [],
  "retryRequired": false,
  "retrySide": null,
  "warnings": [],
  "isValidNid": true,
  "sidesSwapped": false
}
```

---

#### Example: Uploaded Image Is Not an NID Card

**`200 OK`**
```json
{
  "success": false,
  "data": null,
  "errors": [
    "Uploaded images do not appear to be a Bangladesh NID card."
  ],
  "missingFields": [],
  "retryRequired": false,
  "retrySide": null,
  "warnings": [],
  "isValidNid": false,
  "sidesSwapped": false
}
```

---

#### Example: Partial Extraction

**`200 OK`**
```json
{
  "success": false,
  "data": {
    "name": "Kazi Shafiul Islam",
    "fatherName": "Kazi Nazrul Islam",
    "motherName": null,
    "dateOfBirth": "2002-07-15",
    "nidNumber": "1515238218",
    "address": null
  },
  "missingFields": ["motherName", "address"],
  "retryRequired": true,
  "retrySide": "back",
  "warnings": [
    "Could not extract 'motherName'.",
    "Could not extract 'address'."
  ],
  "errors": [],
  "isValidNid": true,
  "sidesSwapped": false
}
```

---

#### Example: Duplicate NID

**`200 OK`**
```json
{
  "success": false,
  "data": {
    "name": "Kazi Shafiul Islam",
    "fatherName": "Kazi Nazrul Islam",
    "motherName": "Selina Akter",
    "dateOfBirth": "2002-07-15",
    "nidNumber": "1515238218",
    "address": "House 37, Road 8, Mirpur-2, Dhaka"
  },
  "missingFields": [],
  "retryRequired": false,
  "retrySide": null,
  "warnings": [],
  "errors": ["This NID already exists."],
  "isValidNid": true,
  "sidesSwapped": false
}
```

---

#### Example: AI Service Error

**`502 Bad Gateway`**
```json
{
  "detail": "Gemini AI service error: <error details>"
}
```

**`429 Too Many Requests`**
```json
{
  "detail": "Gemini API rate limit reached. Please wait a moment."
}
```

---

#### Example: Validation Error (malformed request itself)

**`422 Unprocessable Entity`** *(FastAPI's built-in validation, e.g. wrong field name)*
```json
{
  "detail": [
    {
      "loc": ["body", "front_image"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Status Code Summary

| Code | Meaning |
|---|---|
| `200` | Request processed — check `success` field in the body for the actual outcome |
| `422` | Request itself was malformed (e.g., wrong multipart field names) |
| `429` | AI provider rate limit reached |
| `502` | AI provider returned an unexpected error, empty response, or malformed output |

**Note:** Most business-level failures (missing image, wrong file type, corrupted
image, duplicate NID, not-an-NID-card) are intentionally returned as `200 OK` with
`"success": false` and a populated `errors` array, rather than as HTTP error codes. This
lets clients always parse the same response shape and inspect `success`/`errors` instead
of branching on HTTP status for expected validation failures. Only genuine
infrastructure/provider failures (`429`, `502`) and malformed requests (`422`) use
non-200 status codes.