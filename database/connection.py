import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import quote_plus

from pymongo import MongoClient
from pymongo.database import Database


@dataclass(frozen=True)
class DatabaseLogin:
    database_name: str
    username: str
    password: str


def _login() -> tuple[str, DatabaseLogin]:
    url = os.environ.get("MONGO_URL")
    login = DatabaseLogin(
        os.environ.get("DB_NAME"),
        os.environ.get("DB_USER"),
        os.environ.get("DB_PASS"),
    )
    missing = [
        name
        for name, value in (
            ("MONGO_URL", url),
            ("DB_NAME", login.database_name),
            ("DB_USER", login.username),
            ("DB_PASS", login.password),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Fehlende Umgebungsvariablen: {', '.join(missing)}")
    return url, login


@lru_cache(maxsize=1)
def _client(mongo_db_url: str, login: DatabaseLogin) -> MongoClient:
    uri = (
        f"mongodb://{quote_plus(login.username)}:{quote_plus(login.password)}"
        f"@{mongo_db_url}/{login.database_name}?authSource={login.database_name}"
    )
    return MongoClient(uri, serverSelectionTimeoutMS=5000)


def get_db_client() -> Database:
    url, login = _login()
    return _client(url, login)[login.database_name]