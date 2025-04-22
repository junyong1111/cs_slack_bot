from slack_bolt.async_app import AsyncApp
from app.core.config import SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET

# Slack 앱 초기화 - 인터랙티브 메시지 처리 가능하도록 설정
slack_app = AsyncApp(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
    process_before_response=True,
    ignoring_self_events_enabled=True
)