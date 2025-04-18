from slack_bolt.async_app import AsyncApp
from app.core.config import SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET

# Slack 앱 초기화
slack_app = AsyncApp(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)