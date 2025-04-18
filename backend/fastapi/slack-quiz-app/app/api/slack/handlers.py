from app.api.slack.app import slack_app

@slack_app.command("/기상미션")
async def handle_command(ack, respond):
    await ack()
    await respond("🌅 오늘의 문제를 준비하고 있어요...")

# 다른 슬래시 커맨드도 여기에 추가하면 됨
# 예) /오답복습, /퀴즈리셋 등