from dotenv import load_dotenv
from fastapi import FastAPI
from bson.json_util import dumps
from database import get_db_client
from bson import ObjectId
import json
from itertools import combinations
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()



BASE_URL = "/api"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
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
    projects_collection = db["projects"]
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

@app.get(BASE_URL + "/network")
async def build_network():
    db = get_db_client()
    organisations_collection = db["organisations"]
    projects = get_projects(db)
    nodes = {}
    links = {}

    for project in projects:
        organisations_from_project = project.get("organisations", [])
        organisation_ids = []
        for entry in organisations_from_project:
            if "orgID" in entry:
                id = ObjectId(entry["orgID"]["$oid"])
                organisation_ids.append(id)
                         
        organisation_map = []
        create_organisation_map(organisation_map, organisations_collection, organisation_ids)
        buildNodes(organisation_map, nodes)
        buildLinks(organisation_map, links, project)

    return json.loads(dumps({
        "nodes": list(nodes.values()),
        "links": list(links.values())
    }))



