from bson import ObjectId
from pymongo.synchronous.database import Database

from core.values import as_oid_list, clean_str
from database.constants import (
    FIELDS_COLLECTION,
    GRANTS_COLLECTION,
    PROGRAMMES_COLLECTION,
    TECHNOLOGIES_COLLECTION,
)

def field_index(db: Database, dataset_oid: ObjectId):
    """
    Die Felder laden und dazu den umgekehrten Index Technologie → Felder.
    Eine Technologie kann in mehreren Feldern stehen, daher eine Liste.
    """
    fields = list(db[FIELDS_COLLECTION].find({"dataset": dataset_oid}))
    field_of_technology: dict = {}
    for field in fields:
        for technology in as_oid_list(field.get("technologies")):
            field_of_technology.setdefault(technology, []).append(field["_id"])
    return fields, field_of_technology

def project_fields(project: dict, field_of_technology: dict) -> set:
    found = set()
    for technology in as_oid_list(project.get("keyTechnologies")):
        found.update(field_of_technology.get(technology, []))
    return found


def fields_with_technologies(db: Database, dataset_oid: ObjectId):
    return list(db[FIELDS_COLLECTION].aggregate([
        {"$match": {"dataset": dataset_oid}},
        {"$lookup": {
            "from": TECHNOLOGIES_COLLECTION,
            "localField": "technologies",
            "foreignField": "_id",
            "as": "technologies",
        }},
    ]))


def funding_lookup(db: Database, projects: list[dict]):
    grant_ids = set()
    for project in projects:
        grant_ids.update(as_oid_list(project.get("grant")))

    grant_by_id = {
        g["_id"]: g
        for g in db[GRANTS_COLLECTION].find({"_id": {"$in": list(grant_ids)}})
    }

    programme_ids = set()
    for grant in grant_by_id.values():
        programme_ids.update(as_oid_list(grant.get("programme")))

    programme_by_id = {
        pr["_id"]: pr
        for pr in db[PROGRAMMES_COLLECTION].find({"_id": {"$in": list(programme_ids)}})
    }
    return grant_by_id, programme_by_id


def funding_line(project: dict, grant_by_id: dict, programme_by_id: dict):
    grant_oids = as_oid_list(project.get("grant"))
    grant = grant_by_id.get(grant_oids[0]) if grant_oids else None
    programme = None
    if grant:
        programme_oids = as_oid_list(grant.get("programme"))
        programme = programme_by_id.get(programme_oids[0]) if programme_oids else None
    name = clean_str((programme or grant or {}).get("name"))
    return name, grant, programme
