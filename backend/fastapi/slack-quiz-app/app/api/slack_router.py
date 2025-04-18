import json
from fastapi import APIRouter, Request
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from app.api.slack.app import slack_app

router = APIRouter()
slack_handler = AsyncSlackRequestHandler(slack_app)

@router.post("/slack/events")
async def slack_events(req: Request):
    body = await req.body()
    payload = json.loads(body)

    # 🔥 Slack URL 인증용 처리
    if payload.get("type") == "url_verification":
        return payload.get("challenge")

    # ✅ 일반 슬랙 이벤트 처리
    return await slack_handler.handle(req)