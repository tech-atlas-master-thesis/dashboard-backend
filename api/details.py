from fastapi import APIRouter, HTTPException

from api import BASE_URL
from api.params import to_oid
from core.details import organisation_detail, project_detail
from core.values import serialise
from database import get_db_client

router = APIRouter(prefix=BASE_URL, tags=["details"])

@router.get("/data/{dataset}/organisation/{organisation_id}")
async def get_organisation(dataset: str, organisation_id: str):
    data = organisation_detail(
        get_db_client(),
        to_oid(dataset, "dataset"),
        to_oid(organisation_id, "organisation_id"),
    )
    if data is None:
        raise HTTPException(status_code=404, detail="Organisation nicht gefunden")
    return serialise(data)

@router.get("/data/{dataset}/project/{project_id}")
async def get_project(dataset: str, project_id: str):
    data = project_detail(
        get_db_client(),
        to_oid(dataset, "dataset"),
        to_oid(project_id, "project_id"),
    )
    if data is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return serialise(data)
