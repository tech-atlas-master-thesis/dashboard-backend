from fastapi import APIRouter

from api import BASE_URL
from database import get_db_client
from database.constants import DATASETS_COLLECTION

router = APIRouter(prefix=BASE_URL, tags=["datasets"])

@router.get("/pipelines")
async def list_pipelines():
    db = get_db_client()[DATASETS_COLLECTION]
    return db.distinct("pipelineName")

@router.get("/datasets/{pipeline}")
async def get_datasets(pipeline: str):
    db = get_db_client()[DATASETS_COLLECTION]
    return [
        {**dataset, "_id": str(dataset["_id"]), "pipeline": str(dataset["pipeline"])}
        for dataset in db.find({"pipelineName": pipeline}).sort({"_id": -1})
    ]
