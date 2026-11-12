from fastapi import APIRouter

from api import BASE_URL
from database import get_db_client
from database.constants import DATASETS_COLLECTION

router = APIRouter(prefix=BASE_URL, tags=["datasets"])

ACTIVE_FILTER = {"active": True}
HIDDEN_FIELDS = {"created.by": 0}

@router.get("/pipelines")
def list_pipelines():
    db = get_db_client()[DATASETS_COLLECTION]
    return db.distinct("pipelineName", ACTIVE_FILTER)

@router.get("/datasets/{pipeline}")
def get_datasets(pipeline: str):
    db = get_db_client()[DATASETS_COLLECTION]
    return [
        {**dataset, "_id": str(dataset["_id"]), "pipeline": str(dataset["pipeline"])}
        for dataset in db.find({**ACTIVE_FILTER, "pipelineName": pipeline}, HIDDEN_FIELDS).sort({"_id": -1})
    ]
