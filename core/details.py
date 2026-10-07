from bson import ObjectId
from pymongo.synchronous.database import Database

from core.graph import participants
from core.lookups import field_index, funding_line, funding_lookup, project_fields
from core.values import as_oid_list, clean_str, share
from database.constants import (
    ORGANIZATIONS_COLLECTION,
    PROJECTS_COLLECTION,
    TECHNOLOGIES_COLLECTION,
)


TOP_PARTNERS = 10

def organisation_detail(db: Database, dataset_oid: ObjectId, org_oid: ObjectId):
    organisation = db[ORGANIZATIONS_COLLECTION].find_one({"_id": org_oid})
    if not organisation:
        return None

    projects = list(db[PROJECTS_COLLECTION].find({
        "dataset": dataset_oid,
        "$or": [{"organisations": org_oid}, {"projectLeader": org_oid}],
    }))

    fields, field_of_technology = field_index(db, dataset_oid)
    grant_by_id, programme_by_id = funding_lookup(db, projects)

    self_id = str(org_oid)

    by_field = {f["_id"]: 0 for f in fields}
    partner_counts: dict = {}
    line_counts: dict = {}
    status_counts: dict = {}
    leading = 0
    partners_per_project = []
    rows = []

    for project in projects:
        members = participants(project)
        others = members - {self_id}
        partners_per_project.append(len(others))
        for other in others:
            partner_counts[other] = partner_counts.get(other, 0) + 1

        # Mehrere Leitungen je Projekt sind möglich.
        leaders = {str(o) for o in as_oid_list(project.get("projectLeader"))}
        is_leader = self_id in leaders
        if is_leader:
            leading += 1

        found = project_fields(project, field_of_technology)
        for field_id in found:
            by_field[field_id] += 1

        line, _, _ = funding_line(project, grant_by_id, programme_by_id)
        if line:
            line_counts[line] = line_counts.get(line, 0) + 1

        status = clean_str(project.get("status"))
        if status:
            status_counts[status] = status_counts.get(status, 0) + 1

        rows.append({
            "_id": str(project["_id"]),
            "short": clean_str(project.get("short")),
            "title": clean_str(project.get("title")),
            "status": status,
            "start": project.get("start"),
            "end": project.get("end"),
            "fundingLine": line,
            "partners": len(others),
            "leading": is_leader,
            "fields": [str(field_id) for field_id in found],
        })

    rows.sort(key=lambda r: (r["start"] is None, r["start"]), reverse=True)
    assignments = sum(by_field[f["_id"]] for f in fields)

    profile = [
        {
            "_id": str(f["_id"]),
            "label": clean_str(f.get("label")),
            "short": clean_str(f.get("short")),
            "style": f.get("style"),
            "projects": by_field[f["_id"]],
            "share": share(by_field[f["_id"]], assignments),
        }
        for f in fields if by_field[f["_id"]] > 0
    ]
    profile.sort(key=lambda r: r["projects"], reverse=True)

    top_ids = sorted(partner_counts, key=partner_counts.get, reverse=True)[:TOP_PARTNERS]
    partner_docs = {
        str(o["_id"]): o
        for o in db[ORGANIZATIONS_COLLECTION].find(
            {"_id": {"$in": [ObjectId(i) for i in top_ids]}}
        )
    }
    top_partners = [
        {**partner_docs[i], "sharedProjects": partner_counts[i]}
        for i in top_ids if i in partner_docs
    ]

    programmes = sorted(
        ({"name": name, "projects": count} for name, count in line_counts.items()),
        key=lambda r: r["projects"], reverse=True,
    )

    return {
        "organisation": organisation,
        "metrics": {
            "projects": len(projects),
            "leadingProjects": leading,
            "partnersTotal": len(partner_counts),
            "partnersMean": round(sum(partners_per_project) / len(projects), 2) if projects else 0.0,
            "fields": len(profile),
            "fieldsTotal": len(fields),
            "fieldAssignments": assignments,
            "status": status_counts,
        },
        "fields": profile,
        "partners": top_partners,
        "fundingLines": programmes,
        "projects": rows,
    }

def project_detail(db: Database, dataset_oid: ObjectId, project_oid: ObjectId):
    project = db[PROJECTS_COLLECTION].find_one({"_id": project_oid, "dataset": dataset_oid})
    if not project:
        return None

    fields, field_of_technology = field_index(db, dataset_oid)
    grant_by_id, programme_by_id = funding_lookup(db, [project])
    line, grant, programme = funding_line(project, grant_by_id, programme_by_id)

    leader_oids = as_oid_list(project.get("projectLeader"))
    leaders = {str(o) for o in leader_oids}

    member_ids = list(dict.fromkeys(
        as_oid_list(project.get("organisations")) + leader_oids
    ))
    org_by_id = {
        str(o["_id"]): o
        for o in db[ORGANIZATIONS_COLLECTION].find({"_id": {"$in": member_ids}})
    }

    members = []
    type_counts: dict = {}
    for member_id in member_ids:
        organisation = org_by_id.get(str(member_id))
        if not organisation:
            continue
        org_type = clean_str(organisation.get("type")) or "Unbekannt"
        type_counts[org_type] = type_counts.get(org_type, 0) + 1
        members.append({**organisation, "leading": str(member_id) in leaders})
    
    members.sort(key=lambda o: not o["leading"])

    technology_fields = _technologies_by_field(db, project, fields, field_of_technology)
    recurring = _recurring_consortia(
        db, dataset_oid, project_oid, project, member_ids
    )

    n = len(participants(project))

    return {
        "project": {
            "_id": str(project["_id"]),
            "externalId": project.get("externalId"),
            "short": clean_str(project.get("short")),
            "title": clean_str(project.get("title")),
            "abstract": clean_str(project.get("abstract")),
            "keywords": project.get("keywords") or [],
            "start": project.get("start"),
            "end": project.get("end"),
            "status": clean_str(project.get("status")),
            "fundingLine": line,
            "grant": {"_id": str(grant["_id"]), "name": clean_str(grant.get("name"))} if grant else None,
            "programme": {"_id": str(programme["_id"]), "name": clean_str(programme.get("name"))} if programme else None,
        },
        "metrics": {
            "participants": n,
            "cooperations": n * (n - 1) // 2,
            "types": type_counts,
            "withoutLeader": not leaders,
            "leaders": len(leaders),
        },
        "participants": members,
        "technologyFields": technology_fields,
        "recurring": recurring,
    }


def _technologies_by_field(db: Database, project: dict, fields: list, field_of_technology: dict):
    technology_oids = as_oid_list(project.get("keyTechnologies"))
    technology_by_id = {
        t["_id"]: t
        for t in db[TECHNOLOGIES_COLLECTION].find({"_id": {"$in": technology_oids}})
    }
    field_by_id = {f["_id"]: f for f in fields}

    groups: dict = {}
    for technology_oid in technology_oids:
        technology = technology_by_id.get(technology_oid)
        if not technology:
            continue
        # Der Vorgabewert [None] sammelt Technologien ohne Feld in einer
        # eigenen Gruppe, die im Frontend als "Ohne Feld" erscheint.
        for field_id in field_of_technology.get(technology_oid, [None]):
            groups.setdefault(field_id, []).append(technology)

    result = []
    for field_id, technologies in groups.items():
        field = field_by_id.get(field_id)
        result.append({
            "_id": str(field_id) if field_id else None,
            "label": clean_str(field.get("label")) if field else None,
            "short": clean_str(field.get("short")) if field else None,
            "style": field.get("style") if field else None,
            "technologies": technologies,
        })
    return result

def _recurring_consortia(db: Database, dataset_oid: ObjectId, project_oid: ObjectId, project: dict, member_ids: list):
    own = participants(project)
    candidates = list(db[PROJECTS_COLLECTION].find({
        "dataset": dataset_oid,
        "_id": {"$ne": project_oid},
        "$or": [
            {"organisations": {"$in": member_ids}},
            {"projectLeader": {"$in": member_ids}},
        ],
    }))

    candidate_grants, candidate_programmes = funding_lookup(db, candidates)

    recurring = []
    for candidate in candidates:
        shared = own & participants(candidate)
        if len(shared) < 2:
            continue
        candidate_line, _, _ = funding_line(candidate, candidate_grants, candidate_programmes)
        recurring.append({
            "_id": str(candidate["_id"]),
            "short": clean_str(candidate.get("short")),
            "title": clean_str(candidate.get("title")),
            "start": candidate.get("start"),
            "end": candidate.get("end"),
            "status": clean_str(candidate.get("status")),
            "fundingLine": candidate_line,
            "shared": len(shared),
        })
    recurring.sort(key=lambda r: r["shared"], reverse=True)
    return recurring
