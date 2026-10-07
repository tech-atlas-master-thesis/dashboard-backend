from bson import ObjectId
from pymongo.synchronous.database import Database

from core.graph import metrics
from core.lookups import field_index, project_fields
from core.values import as_oid_list, clean_str
from database.constants import ORGANIZATIONS_COLLECTION, PROJECTS_COLLECTION

def field_analysis(db: Database, dataset_oid: ObjectId) -> dict:
    fields, field_of_technology = field_index(db, dataset_oid)
    projects = list(db[PROJECTS_COLLECTION].find({"dataset": dataset_oid}))

    org_ids = set()
    for project in projects:
        org_ids.update(as_oid_list(project.get("organisations")))
        org_ids.update(as_oid_list(project.get("projectLeader")))

    org_types = {
        str(o["_id"]): clean_str(o.get("type"))
        for o in db[ORGANIZATIONS_COLLECTION].find(
            {"_id": {"$in": list(org_ids)}}, {"type": 1}
        )
    }

    by_field = {f["_id"]: [] for f in fields}
    without_field = 0
    for project in projects:
        found = project_fields(project, field_of_technology)
        if not found:
            without_field += 1
        for field_id in found:
            by_field[field_id].append(project)

    rows = []
    for field in fields:
        rows.append({
            "_id": str(field["_id"]),
            "label": clean_str(field.get("label")),
            "short": clean_str(field.get("short")),
            "style": field.get("style"),
            **metrics(by_field[field["_id"]], org_types),
        })

    rows.sort(key=lambda r: r["projects"], reverse=True)

    return {
        "fields": rows,
        "total": metrics(projects, org_types),
        "projectsWithoutField": without_field,
    }
