from itertools import combinations
from core.values import as_oid_list, share

ACADEMIC_TYPES = {
    "UNIVERSITY", "Universität",
    "FACHHOCHSCHULE", "Fachhochschule",
    "RESEARCH_INSTITUTE", "Außeruniversitäre Forschungseinrichtung",
}

def participants(project: dict) -> set[str]:
    ids = {str(o) for o in as_oid_list(project.get("organisations"))}
    ids.update(str(o) for o in as_oid_list(project.get("projectLeader")))
    return ids


def projection(projects: list[dict]):
    neighbours: dict = {}
    edges = set()

    for project in projects:
        # Sortiert, damit ein Paar immer in derselben Reihenfolge entsteht und
        # (a, b) und (b, a) nicht beide in der Kantenmenge landen.
        ids = sorted(participants(project))
        for i in ids:
            neighbours.setdefault(i, set())
        for a, b in combinations(ids, 2):
            edges.add((a, b))
            neighbours[a].add(b)
            neighbours[b].add(a)

    return neighbours, edges


def component_sizes(neighbours: dict) -> list[int]:
    seen = set()
    sizes = []

    for start in neighbours:
        if start in seen:
            continue
        size = 0
        stack = [start]
        seen.add(start)
        while stack:
            node = stack.pop()
            size += 1
            for nb in neighbours[node]:
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        sizes.append(size)

    return sizes


def metrics(projects: list[dict], org_types: dict) -> dict:
    neighbours, edges = projection(projects)

    n = len(neighbours)
    e = len(edges)
    isolated = sum(1 for nb in neighbours.values() if not nb)

    sizes = component_sizes(neighbours)
    largest = max(sizes) if sizes else 0
    real = [s for s in sizes if s > 1]

    without_partner = sum(1 for p in projects if len(participants(p)) < 2)
    with_leader = [p for p in projects if as_oid_list(p.get("projectLeader"))]
    academic = sum(
        1 for p in with_leader
        if any(
            org_types.get(str(leader)) in ACADEMIC_TYPES
            for leader in as_oid_list(p["projectLeader"])
        )
    )

    return {
        "projects": len(projects),
        "projectsWithoutLeader": len(projects) - len(with_leader),
        "projectsWithoutPartner": without_partner,
        "projectsWithoutPartnerShare": share(without_partner, len(projects)),
        "organisations": n,
        "cooperations": e,
        "degreeMean": round(2 * e / n, 2) if n else 0.0,
        "isolated": isolated,
        "isolatedShare": share(isolated, n),
        "components": len(sizes),
        "componentsFromTwo": len(real),
        "largestComponent": largest,
        "largestComponentShare": share(largest, n),
        "density": round(2 * e / (n * (n - 1)), 6) if n > 1 else 0.0,
        "academicLead": academic,
        "academicLeadShare": share(academic, len(with_leader)),
    }
