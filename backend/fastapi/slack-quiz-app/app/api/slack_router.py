from fastapi import APIRouter, Request
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from app.api.slack.app import slack_app

router = APIRouter()
slack_handler = AsyncSlackRequestHandler(slack_app)

@router.post("/slack/events")
async def slack_events(req: Request):
    return await slack_handler.handle(req)