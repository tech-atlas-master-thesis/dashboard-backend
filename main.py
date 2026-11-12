import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api import analysis, datasets, details, network, search

CACHE_SECONDS = int(os.environ.get("CACHE_SECONDS", "86400"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def cache_header(request: Request, call_next):
    response = await call_next(request)
    if (
        CACHE_SECONDS > 0
        and request.method == "GET"
        and "/data/" in request.url.path
        and response.status_code == 200
    ):
        response.headers["Cache-Control"] = f"public, max-age={CACHE_SECONDS}, immutable"
    return response

app.include_router(datasets.router)
app.include_router(network.router)
app.include_router(analysis.router)
app.include_router(details.router)
app.include_router(search.router)