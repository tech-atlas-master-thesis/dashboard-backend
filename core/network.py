from pymongo.synchronous.database import Database

from core.values import as_oid_list, clean_str
from database.constants import (
    GRANTS_COLLECTION,
    ORGANIZATIONS_COLLECTION,
    PROGRAMMES_COLLECTION,
)

def build_network_from_projects(db: Database, projects: list[dict]):
    org_ids, grant_ids = set(), set()

    for p in projects:
        org_ids.update(as_oid_list(p.get("organisations")))
        org_ids.update(as_oid_list(p.get("projectLeader")))
        grant_ids.update(as_oid_list(p.get("grant")))

    org_by_id = {
        o["_id"]: o
        for o in db[ORGANIZATIONS_COLLECTION].find({"_id": {"$in": list(org_ids)}})
    }
    grant_by_id = {
        g["_id"]: g
        for g in db[GRANTS_COLLECTION].find({"_id": {"$in": list(grant_ids)}})
    }

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
        participant_ids = list(dict.fromkeys(
            as_oid_list(project.get("organisations"))
            + as_oid_list(project.get("projectLeader"))
        ))
        members = [org_by_id[i] for i in participant_ids if i in org_by_id]

        for o in members:
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
            "organisations": [str(o["_id"]) for o in members],
            "projectLeader": [str(o) for o in as_oid_list(project.get("projectLeader"))],
            "grant": {"_id": str(grant["_id"]), "name": grant.get("name")} if grant else None,
            "programme": {"_id": str(programme["_id"]), "name": programme.get("name")} if programme else None,
        })

    return {"nodes": list(nodes.values()), "projects": entries}
