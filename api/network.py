from fastapi import APIRouter, HTTPException

from api import BASE_URL
from api.params import to_oid
from core.lookups import fields_with_technologies
from core.network import build_network_from_projects
from core.values import serialise
from database import get_db_client
from database.constants import FIELDS_COLLECTION, PROJECTS_COLLECTION

router = APIRouter(prefix=BASE_URL, tags=["network"])

@router.get("/data/{dataset}/key-technologies")
async def get_key_technologies(dataset: str):
    db = get_db_client()
    return serialise(fields_with_technologies(db, to_oid(dataset, "dataset")))


@router.get("/data/{dataset}/network")
async def build_network(dataset: str):
    db = get_db_client()
    projects = list(db[PROJECTS_COLLECTION].find({"dataset": to_oid(dataset, "dataset")}))
    return serialise(build_network_from_projects(db, projects))

@router.get("/data/{dataset}/network/field/{field_id}")
async def build_network_by_field(dataset: str, field_id: str):
    db = get_db_client()
    dataset_oid = to_oid(dataset, "dataset")

    field = db[FIELDS_COLLECTION].find_one(
        {"_id": to_oid(field_id, "field_id"), "dataset": dataset_oid}
    )
    if not field:
        raise HTTPException(status_code=404, detail="Feld nicht gefunden")

    technology_ids = field.get("technologies") or []
    if not technology_ids:
        return serialise({"nodes": [], "projects": []})

    projects = list(db[PROJECTS_COLLECTION].find({
        "keyTechnologies": {"$in": technology_ids},
        "dataset": dataset_oid,
    }))
    return serialise(build_network_from_projects(db, projects))

@router.get("/data/{dataset}/network/{technology_id}")
async def build_network_by_technology(dataset: str, technology_id: str):
    db = get_db_client()
    projects = list(db[PROJECTS_COLLECTION].find({
        "keyTechnologies": to_oid(technology_id, "technology_id"),
        "dataset": to_oid(dataset, "dataset"),
    }))
    return serialise(build_network_from_projects(db, projects))
