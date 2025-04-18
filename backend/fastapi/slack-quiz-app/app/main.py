from fastapi import FastAPI
from app.api import slack

app = FastAPI()

app.include_router(slack.router)

@app.get("/")
async def root():
    return {"message": "Hello World"}