import json
from itertools import combinations

from bson import ObjectId
from bson.json_util import dumps
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import get_db_client
from database.constants import TECHNOLOGIES_COLLECTION, FIELDS_COLLECTION, ORGANIZATIONS_COLLECTION, \
    PROJECTS_COLLECTION, DATASETS_COLLECTION

load_dotenv()



BASE_URL = "/api"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get(BASE_URL + "/")
async def root():
    return {"message": "Hello World"}

@app.get(BASE_URL + "/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

def get_projects(db):
    projects_collection = db[PROJECTS_COLLECTION]
    projects = list(projects_collection.find())
    return projects

def create_organisation_map(organisation_map, organisations_collection, organisation_ids):
    for organisation in organisations_collection.find({"_id": {"$in": organisation_ids}}):
        organisation_map.append(organisation)

def buildNodes(organisation_map, nodes):
    for organisation in organisation_map:
        organisation_id_string = str(organisation["_id"])
        if organisation_id_string not in nodes:
            nodes[organisation_id_string] = organisation;

def buildLinks(organisation_map, links, project):
    for org_a, org_b in combinations(organisation_map, 2):
        source_id = str(org_a["_id"])
        target_id = str(org_b["_id"])

        key = (min(source_id, target_id), max(source_id, target_id))
        if key not in links:
            links[key] = {
                "source": source_id,
                "target": target_id,
                "projects": []
            }
        links[key]["projects"].append(project.get("title"))

def get_fields_with_technologies(db):
    fields_collection = db[FIELDS_COLLECTION]

    return list(fields_collection.aggregate([
        {
            "$lookup": {
                "from": TECHNOLOGIES_COLLECTION,
                "localField": "technologies",
                "foreignField": "_id",
                "as": "technologies"
            }
        }
    ]))

    fields = list(fields_collection.find())
    key_technologies = list(key_technologies_collection.find())

    fields_map = {}
    for field in fields:
        field_id_str = str(field["_id"])
        field["technologies"] = []
        fields_map[field_id_str] = field
    
    for technology in key_technologies:
        field_id_str = technology.get("field")
        if field_id_str in fields_map:
            fields_map[field_id_str]["technologies"].append(technology)

    return list(fields_map.values())


@app.get(BASE_URL + "/key-technologies")
async def get_key_technologies():
    db = get_db_client()
    fields_with_technologies = get_fields_with_technologies(db)
    return json.loads(dumps(fields_with_technologies))

@app.get(BASE_URL + "/network")
async def build_network():
    db = get_db_client()
    organisations_collection = db[ORGANIZATIONS_COLLECTION]
    projects = get_projects(db)
    nodes = {}
    links = {}

    for project in projects:
        organisation_ids = project.get("organisations", [])
        project_leader_id = project.get("project_leader")
        if project_leader_id and project_leader_id not in organisation_ids:
            organisation_ids.append(project_leader_id)
                         
        organisation_map = []
        create_organisation_map(organisation_map, organisations_collection, organisation_ids)
        buildNodes(organisation_map, nodes)
        buildLinks(organisation_map, links, project)

    return json.loads(dumps({
        "nodes": list(nodes.values()),
        "links": list(links.values())
    }))



