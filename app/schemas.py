#app/schemas.py 
from typing import Optional
from pydantic import BaseModel

class NIDData(BaseModel):
    name: Optional[str] = None
    fatherName: Optional[str] = None
    motherName: Optional[str] = None
    dateOfBirth: Optional[str] = None
    nidNumber: Optional[str] = None
    address: Optional[str] = None

class ExtractionResponse(BaseModel):
    success: bool
    data: Optional[NIDData] = None
    missingFields: list[str] = []
    retryRequired: bool = False
    retrySide: Optional[str] = None
    warnings: list[str] = []
    errors: list[str] = []
    isValidNid: bool = True
    sidesSwapped: bool = False
