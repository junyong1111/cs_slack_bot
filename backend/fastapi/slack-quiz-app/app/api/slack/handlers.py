from app.api.slack.app import slack_app

user_state = {}

VALID_TOPICS = {
    "네트워크": "network",
    "운영체제": "os",
    "데이터베이스": "database",
    "웹": "web",
    "자료구조": "ds",
    "알고리즘": "algo"
}

@slack_app.command("/기상미션")
async def handle_command(ack, respond):
    await ack()
    await respond("🌅 오늘의 문제를 준비하고 있어요...")

@slack_app.event("message")
async def handle_message(body, say):
    text = body["event"]["text"].strip()
    user = body["event"]["user"]

    # ✅ 1. 공부시작 처리 (return으로 바로 끝내기!)
    if text.lower() == "공부시작":
        user_state[user] = {"mode": "selecting_topic"}

        await say(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "📘 공부를 시작해볼까요?\n"
                            "*아래 CS 필수 지식 카테고리 중 하나를 선택해주세요!*"
                        )
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "1️⃣ 네트워크\n"
                            "2️⃣ 운영체제\n"
                            "3️⃣ 데이터베이스\n"
                            "4️⃣ 자료구조\n"
                            "5️⃣ 알고리즘\n"
                            "6️⃣ 웹"
                        )
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "💬 예: '운영체제'라고 입력해주세요!"
                        }
                    ]
                }
            ]
        )
        return  # ✅ 공부시작 후에는 바로 return!

    # ✅ 2. 주제 선택 처리
    if user_state.get(user, {}).get("mode") == "selecting_topic":
        if text not in VALID_TOPICS:
            await say(f"❗ 잘못된 주제입니다. 가능한 주제: {', '.join(VALID_TOPICS.keys())}")
            return

        topic_key = VALID_TOPICS[text]
        user_state[user] = {"mode": "learning", "topic": topic_key}

        await say(f"🧠 *{text}*에 대해 공부를 시작할게요! 잠시만요...")

        # 👉 LangGraph 호출 (지금은 mock)
        explanation = "test"
        await say(f"📘 *{text} 개념 설명:*\n{explanation}")