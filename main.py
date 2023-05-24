import datetime

from fastapi import FastAPI
from pydantic import BaseModel


class Gracie(BaseModel):
    name: str
    hello_utc: datetime.datetime


app = FastAPI()


@app.get("/goodnight", response_model=Gracie)
async def goodnight():
    app.is_exposing = True

    goodnight = Gracie(name="Gracie", hello_utc=datetime.datetime.now())

    return goodnight
