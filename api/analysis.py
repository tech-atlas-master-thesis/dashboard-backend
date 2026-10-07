from fastapi import APIRouter

from api import BASE_URL
from api.params import to_oid
from core.analysis import field_analysis
from core.values import serialise
from database import get_db_client

router = APIRouter(prefix=BASE_URL, tags=["analysis"])

@router.get("/data/{dataset}/analysis/fields")
async def analysis_fields(dataset: str):
    db = get_db_client()
    return serialise(field_analysis(db, to_oid(dataset, "dataset")))
