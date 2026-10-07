import json
import math

from bson import ObjectId
from bson.json_util import dumps


def clean_str(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str):
        return value.strip() or None
    return value

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

def share(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0

def serialise(value):
    return json.loads(dumps(value))
