from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

BASE_URL = "/api"

app = FastAPI()


@app.get(BASE_URL + "/")
async def root():
    return {"message": "Hello World"}


@app.get(BASE_URL + "/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
