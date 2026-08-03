import json
import math
from bson import ObjectId
from bson.json_util import dumps
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo.synchronous.database import Database

from database import get_db_client
from database.constants import ( TECHNOLOGIES_COLLECTION, FIELDS_COLLECTION, ORGANIZATIONS_COLLECTION,
    PROJECTS_COLLECTION, DATASETS_COLLECTION, GRANTS_COLLECTION, PROGRAMMES_COLLECTION)

load_dotenv()

BASE_URL = "/api"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def clean_str(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str):
        return value.strip() or None
    return value

def to_oid(value: str, label: str):
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Ungültige {label}: {value}")

def as_oid_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [o for v in value for o in as_oid_list(v)]
    if isinstance(value, ObjectId):
        return [value]
    try:
        return [ObjectId(value)]
    except Exception:
        return []

def build_network_from_projects(db: Database, projects: list[dict]):
    org_ids, grant_ids = set(), set()

    for p in projects:
        org_ids.update(as_oid_list(p.get("organisations")))
        org_ids.update(as_oid_list(p.get("projectLeader")))
        grant_ids.update(as_oid_list(p.get("grant")))

    org_by_id = {o["_id"]: o for o in db[ORGANIZATIONS_COLLECTION].find({"_id": {"$in": list(org_ids)}})}
    grant_by_id = {g["_id"]: g for g in db[GRANTS_COLLECTION].find({"_id": {"$in": list(grant_ids)}})}

    programme_ids = set()
    for g in grant_by_id.values():
        programme_ids.update(as_oid_list(g.get("programme")))

    programme_by_id = {
        pr["_id"]: pr
        for pr in db[PROGRAMMES_COLLECTION].find({"_id": {"$in": list(programme_ids)}})
    }

    nodes: dict = {}
    entries: list = []

    for project in projects:
        participant_ids = list(dict.fromkeys( as_oid_list(project.get("organisations")) + as_oid_list(project.get("projectLeader"))))
        participants = [org_by_id[i] for i in participant_ids if i in org_by_id]

        for o in participants:
            nodes.setdefault(str(o["_id"]), o)

        grant_oids = as_oid_list(project.get("grant"))
        grant = grant_by_id.get(grant_oids[0]) if grant_oids else None
        programme = None
        if grant:
            pr_oids = as_oid_list(grant.get("programme"))
            programme = programme_by_id.get(pr_oids[0]) if pr_oids else None

        entries.append({
            "_id": str(project["_id"]),
            "externalId": project.get("externalId"),
            "short": project.get("short"),
            "title": project.get("title"),
            "abstract": clean_str(project.get("abstract")),
            "start": project.get("start"),
            "end": project.get("end"),
            "status": project.get("status"),
            "keywords": project.get("keywords") or [],
            "organisations": [str(o["_id"]) for o in participants],
            "projectLeader": (lambda l: str(l[0]) if l else None)(as_oid_list(project.get("projectLeader"))),
            "grant": {"_id": str(grant["_id"]), "name": grant.get("name")} if grant else None,
            "programme": {"_id": str(programme["_id"]), "name": programme.get("name")} if programme else None
        })

    return {"nodes": list(nodes.values()), "projects": entries}

def get_fields_with_technologies(db: Database, dataset: str):
    return list(db[FIELDS_COLLECTION].aggregate([
        { 
            "$match": {
                "dataset": to_oid(dataset, "dataset")
            } 
        },
        { 
            "$lookup": {
            "from": TECHNOLOGIES_COLLECTION,
            "localField": "technologies",
            "foreignField": "_id",
            "as": "technologies",
        }}
    ]))

@app.get(BASE_URL + "/")
async def root():
    return {"message": "Hello World"}

@app.get(BASE_URL + "/pipelines")
async def list_pipelines():
    db = get_db_client()[DATASETS_COLLECTION]

    distinct_pipelines = db.distinct("pipelineName", {"active": True})

    return distinct_pipelines

@app.get(BASE_URL + "/datasets/{pipeline}")
async def get_datasets(pipeline: str):
    db = get_db_client()[DATASETS_COLLECTION]

    return [{**dataset, "_id": str(dataset["_id"]), "pipeline": str(dataset["pipeline"])} for dataset in db.find({"pipelineName": pipeline, "active": True}).sort({"_id": -1})]

@app.get(BASE_URL + "/data/{dataset}/key-technologies")
async def get_key_technologies(dataset: str):
    db = get_db_client()
    return json.loads(dumps(get_fields_with_technologies(db, dataset)))

@app.get(BASE_URL + "/data/{dataset}/network")
async def build_network(dataset: str):
    db = get_db_client()
    projects = list(db[PROJECTS_COLLECTION].find({"dataset": to_oid(dataset, "dataset")}))
    return json.loads(dumps(build_network_from_projects(db, projects)))

@app.get(BASE_URL + "/data/{dataset}/network/field/{field_id}")
async def build_network_by_field(dataset: str, field_id: str):
    db = get_db_client()
    dataset_oid = to_oid(dataset, "dataset")

    field = db[FIELDS_COLLECTION].find_one({"_id": to_oid(field_id, "field_id"),"dataset": dataset_oid})
    if not field:
        raise HTTPException(status_code=404, detail="Feld nicht gefunden")

    technology_ids = field.get("technologies") or []
    if not technology_ids:
        return json.loads(dumps({"nodes": [], "projects": []}))

    projects = list(db[PROJECTS_COLLECTION].find({"keyTechnologies": {"$in": technology_ids},"dataset": dataset_oid}))
    return json.loads(dumps(build_network_from_projects(db, projects)))

@app.get(BASE_URL + "/data/{dataset}/network/{technology_id}")
async def build_network_by_technology(dataset: str, technology_id: str):
    db = get_db_client()
    projects = list(db[PROJECTS_COLLECTION].find({"keyTechnologies": to_oid(technology_id, "technology_id"),"dataset": to_oid(dataset, "dataset")}))
    return json.loads(dumps(build_network_from_projects(db, projects)))