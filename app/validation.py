#app/validation.py
from app.schemas import ExtractionResponse, NIDData
import re
from datetime import datetime

EXPECTED_FIELDS = [
    "name",
    "fatherName",
    "motherName",
    "dateOfBirth",
    "nidNumber",
    "address",
]

FRONT_FIELDS = {
    "name",
    "fatherName",
    "motherName",
    "dateOfBirth",
    "nidNumber",
}

BACK_FIELDS = {
    "address"
}


def _validate_nid_number(value):
    if not value:
        return None, None
    digits = re.sub(r"\D", "", value)
    if len(digits) not in (10, 13, 17):
        return None, f"nidNumber '{value}' has an unexpected length ({len(digits)} digits)."
    return digits, None

def _validate_date_of_birth(value):
    if not value:
        return None, None
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            if dt.year < 1900 or dt > datetime.now():
                return value, f"dateOfBirth '{value}' looks implausible."
            return dt.strftime("%Y-%m-%d"), None
        except ValueError:
            continue
    return value, f"dateOfBirth '{value}' could not be parsed into a standard format."


def build_extraction_response(fields: dict) -> ExtractionResponse:
    missing_fields = [f for f in EXPECTED_FIELDS if not fields.get(f)]
    warnings = [f"Could not extract '{field}'." for field in missing_fields]

    nid_value, nid_warning = _validate_nid_number(fields.get("nidNumber"))
    if nid_warning:
        warnings.append(nid_warning)
    dob_value, dob_warning = _validate_date_of_birth(fields.get("dateOfBirth"))
    if dob_warning:
        warnings.append(dob_warning)

    fields = {**fields, "nidNumber": nid_value, "dateOfBirth": dob_value}
    
    retry_side = None
    if any(f in FRONT_FIELDS for f in missing_fields):
        retry_side = "front"
    elif any(f in BACK_FIELDS for f in missing_fields):
        retry_side = "back"

    data = NIDData(
        **{
            field: fields.get(field)
            for field in EXPECTED_FIELDS
        }
    )

    return ExtractionResponse(
        success=len(missing_fields) == 0,
        data=data,
        missingFields=missing_fields,
        retryRequired=len(missing_fields) > 0,
        retrySide=retry_side,
        warnings=warnings,
        errors=[]
    )

