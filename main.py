from fastapi import FastAPI


BASE_URL = "/api"

app = FastAPI()


@app.get(BASE_URL + "/")
async def root():
    return {"message": "Hello World"}


@app.get(BASE_URL + "/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
