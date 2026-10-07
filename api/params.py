from bson import ObjectId
from fastapi import HTTPException

def to_oid(value: str, label: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Ungültige {label}: {value}")
