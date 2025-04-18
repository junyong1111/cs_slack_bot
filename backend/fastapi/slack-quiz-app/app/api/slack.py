from fastapi import APIRouter, Request
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from slack_bolt.async_app import AsyncApp
from app.core.config import SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET

router = APIRouter()

# Slack 앱 초기화
slack_app = AsyncApp(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
slack_handler = AsyncSlackRequestHandler(slack_app)

# 슬래시 커맨드 등록 예시
@slack_app.command("/기상미션")
async def handle_command(ack, respond):
    await ack()
    await respond("🌅 오늘의 문제를 준비하고 있어요...")

@router.post("/slack/events")
async def slack_events(req: Request):
    return await slack_handler.handle(req)