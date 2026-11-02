import re

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query

from database import get_db_client
from database.constants import ORGANIZATIONS_COLLECTION, PROJECTS_COLLECTION

router = APIRouter(prefix="/api")

MIN_LENGTH = 2
MAX_HITS = 500

@router.get("/data/{dataset}/search")
async def search(dataset: str, q: str = Query(default="")):
    term = (q or "").strip()
    if len(term) < MIN_LENGTH:
        return {"organisations": [], "projects": [], "term": term}

    try:
        dataset_oid = ObjectId(dataset)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=400, detail="Ungültige Datensatz-ID")

    db = get_db_client()
    pattern = {"$regex": re.escape(term), "$options": "i"}

    organisations = list(
        db[ORGANIZATIONS_COLLECTION]
        .find(
            {"dataset": dataset_oid, "name": pattern},
            {"name": 1, "type": 1},
        )
        .limit(MAX_HITS)
    )

    projects = list(
        db[PROJECTS_COLLECTION]
        .find(
            {
                "dataset": dataset_oid,
                "$or": [{"short": pattern}, {"title": pattern}, {"externalId": pattern}],
            },
            {"short": 1, "title": 1, "externalId": 1},
        )
        .limit(MAX_HITS)
    )

    return {
        "organisations": [
            {
                "_id": str(o["_id"]),
                "name": o.get("name") or "",
                "type": o.get("type") or "",
            }
            for o in organisations
        ],
        "projects": [
            {
                "_id": str(p["_id"]),
                "short": p.get("short") or "",
                "title": p.get("title") or "",
                "externalId": p.get("externalId") or "",
            }
            for p in projects
        ],
        "term": term,
    }