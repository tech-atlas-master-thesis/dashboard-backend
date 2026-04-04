import os
from dataclasses import dataclass

from pymongo import MongoClient


@dataclass
class DatabaseLogin:
    database_name: str
    username: str
    password: str


def get_db_client():
    return _get_pipeline_client(
        os.environ.get("MONGO_URL"),
        DatabaseLogin(os.environ.get("DB_NAME"), os.environ.get("DB_USER"), os.environ.get("DB_PASS")),
    )


def _get_pipeline_client(mongo_db_url: str, login: DatabaseLogin):
    return MongoClient(
        f"mongodb://{login.username}:{login.password}@{mongo_db_url}/{login.database_name}?authSource={login.database_name}"
    )[login.database_name]
