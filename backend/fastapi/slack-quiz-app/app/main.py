from fastapi import FastAPI
from app.api import slack_router
import app.api.slack.handlers  # 이 줄이 없으면 핸들러 등록 안 됨!

app = FastAPI()
app.include_router(slack_router.router)