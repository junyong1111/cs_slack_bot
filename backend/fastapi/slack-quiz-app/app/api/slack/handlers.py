from app.services.study_mode import run_network_learning_fsm, process_level_test_answers, study_advanced_topic, start_interview_session, get_next_interview_question, answer_user_question
from app.api.slack.app import slack_app
import json

# 사용자별 상태 저장
user_state = {}

# 유효한 주제 목록
VALID_TOPICS = {
    "네트워크": "network",
    "운영체제": "os",
    "데이터베이스": "database",
    "웹": "web",
    "자료구조": "ds",
    "알고리즘": "algo"
}

# 가능한 학습 모드 상태
class LearningMode:
    SELECTING_TOPIC = "selecting_topic"
    BASIC_LEARNING = "basic_learning"
    LEVEL_TEST = "level_test"
    SELECTING_SUBTOPIC = "selecting_subtopic"
    ADVANCED_LEARNING = "advanced_learning"
    QUIZ = "quiz"
    INTERVIEW = "interview"

@slack_app.command("/기상미션")
async def handle_command(ack, respond):
    await ack()
    await respond("🌅 오늘의 문제를 준비하고 있어요...")

@slack_app.event("message")
async def handle_message(body, say):
    text = body["event"]["text"].strip()
    user = body["event"]["user"]

    # 1. 공부시작 - 주제 선택 화면 표시
    if text.lower() == "공부시작":
        user_state[user] = {"mode": LearningMode.SELECTING_TOPIC}

        await say(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "📘 공부할 주제를 선택해주세요!\n"
                            "*아래 CS 필수 지식 카테고리 중 하나를 입력해주세요*"
                        )
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "• 네트워크\n"
                            "• 운영체제\n"
                            "• 데이터베이스\n"
                            "• 자료구조\n"
                            "• 알고리즘\n"
                            "• 웹"
                        )
                    }
                }
            ]
        )
        return

    # 2. 주제 선택 단계에서 사용자가 주제 입력
    if user_state.get(user, {}).get("mode") == LearningMode.SELECTING_TOPIC:
        if text not in VALID_TOPICS:
            await say(f"❗ 잘못된 주제입니다. 가능한 주제: {', '.join(VALID_TOPICS.keys())}")
            return

        topic = text
        # 학습 단계로 상태 변경
        user_state[user] = {
            "mode": "selecting_level_check",
            "topic": topic,
            "tags": [],
            "current_tag_index": 0,
            "user_level": "",
            "subtopics": [],
            "selected_subtopic": "",
            "interview_index": 0
        }

        # 레벨 체크 방식 선택 요청
        await say(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🧠 *{topic}* 공부를 시작합니다! 먼저 학습 수준을 확인하겠습니다."
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "학습 수준 확인 방식을 선택해주세요:"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "*1️⃣ 자가평가*: 본인의 수준을 직접 선택합니다 (초급/중급/고급)\n"
                            "*2️⃣ 테스트*: 간단한 OX, 객관식, 주관식 문제를 풀어서 확인합니다"
                        )
                    }
                }
            ]
        )
        return

    # 3. 레벨 체크 방식 선택
    if user_state.get(user, {}).get("mode") == "selecting_level_check":
        topic = user_state[user]["topic"]

        if text == "1" or "자가평가" in text or "직접" in text:
            # 자가평가 모드로 전환
            user_state[user]["mode"] = "self_assessment"

            await say(
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "본인의 수준을 선택해주세요:"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                "*초급*: 기본 개념을 배우고 싶습니다\n"
                                "*중급*: 기본 개념은 알고 있지만 심화 학습이 필요합니다\n"
                                "*고급*: 실무 수준이며 전문적인 내용을 배우고 싶습니다"
                            )
                        }
                    }
                ]
            )
            return

        elif text == "2" or "테스트" in text:
            # 테스트 모드로 전환
            user_state[user]["mode"] = LearningMode.LEVEL_TEST

            # 테스트 시작 메시지
            await say("📝 *수준 테스트를 시작합니다*")
            await say("테스트는 OX 문제 2개, 객관식 문제 2개, 주관식 문제 1개로 구성됩니다.")
            await say("🔍 테스트 문제를 생성하고 있습니다...")

            # 백그라운드에서 테스트 문제 생성
            import asyncio

            # 테스트 문제 생성 함수 정의 (간소화 버전)
            async def generate_test_questions(topic):
                if topic == "네트워크":
                    return [
                        {"type": "OX", "question": "OSI 7계층에서 물리 계층은 비트 단위의 데이터 전송을 담당한다.", "answer": "O"},
                        {"type": "OX", "question": "HTTP는 연결 지향형 프로토콜이다.", "answer": "X"},
                        {"type": "객관식", "question": "다음 중 전송 계층 프로토콜이 아닌 것은?",
                         "options": ["TCP", "UDP", "HTTP", "SCTP"], "answer": "C"},
                        {"type": "객관식", "question": "다음 중 IP 주소 클래스 A의 범위는?",
                         "options": ["1.0.0.0 ~ 126.255.255.255", "128.0.0.0 ~ 191.255.255.255", "192.0.0.0 ~ 223.255.255.255", "224.0.0.0 ~ 239.255.255.255"],
                         "answer": "A"},
                        {"type": "주관식", "question": "TCP의 3-way handshake 과정을 설명하시오.",
                         "answer": "1) 클라이언트가 서버에 SYN 패킷 전송 2) 서버가 클라이언트에 SYN+ACK 패킷 전송 3) 클라이언트가 서버에 ACK 패킷 전송으로 연결 수립"}
                    ]
                else:
                    # 다른 주제에 대한 기본 테스트 문제
                    return [
                        {"type": "OX", "question": f"{topic}의 기본 개념에 대한 OX 문제 1", "answer": "O"},
                        {"type": "OX", "question": f"{topic}의 기본 개념에 대한 OX 문제 2", "answer": "X"},
                        {"type": "객관식", "question": f"{topic}의 중요 개념에 대한 객관식 문제 1",
                         "options": ["선택지 A", "선택지 B", "선택지 C", "선택지 D"], "answer": "A"},
                        {"type": "객관식", "question": f"{topic}의 중요 개념에 대한 객관식 문제 2",
                         "options": ["선택지 A", "선택지 B", "선택지 C", "선택지 D"], "answer": "B"},
                        {"type": "주관식", "question": f"{topic}의 핵심 개념에 대해 설명하시오.",
                         "answer": f"{topic}의 핵심 개념에 대한 모범 답안입니다."}
                    ]

            # 비동기적으로 문제 생성 (실제로는 미리 준비된 문제 사용)
            await asyncio.sleep(1)  # 실제 생성처럼 약간의 지연
            questions = await generate_test_questions(topic)

            # 문제 저장
            user_state[user]["test_questions"] = questions

            # 문제 출력 (OX 2개, 객관식 2개, 주관식 1개)
            for i, q in enumerate(questions):
                if q["type"] == "OX":
                    await say(f"{i+1}. [OX] {q['question']}")
                elif q["type"] == "객관식":
                    options_text = "\n   ".join([f"{chr(65+j)}. {opt}" for j, opt in enumerate(q["options"])])
                    await say(f"{i+1}. [객관식] {q['question']}\n   {options_text}")
                else:
                    await say(f"{i+1}. [주관식] {q['question']}")

            # 답변 안내 메시지
            await say("\n답변 방법: '1번: O, 2번: X, 3번: C, 4번: A, 5번: TCP 연결 과정은...' 형식으로 모든 문제에 대한 답변을 한 번에 입력해주세요.")
            return

        else:
            await say("❗ 1번(자가평가) 또는 2번(테스트) 중 하나를 선택해주세요.")
            return

    # 4. 자가평가 응답 처리
    if user_state.get(user, {}).get("mode") == "self_assessment":
        topic = user_state[user]["topic"]

        level_map = {
            "초급": "beginner",
            "중급": "intermediate",
            "고급": "advanced"
        }

        if text.lower() in ["초급", "중급", "고급"]:
            user_level = level_map.get(text.lower(), "beginner")
            user_state[user]["user_level"] = user_level

            # 사용자 수준에 맞는 학습 시작
            await say(f"✅ *{text}* 수준으로 설정되었습니다. {topic} 학습을 시작합니다!")

            # 수준별 다른 메시지 추가
            if text.lower() == "초급":
                await say("🔰 기초 개념부터 차근차근 설명해 드리겠습니다.")
            elif text.lower() == "중급":
                await say("🏆 기본 개념은 빠르게 살펴보고 심화 내용을 중점적으로 학습하겠습니다.")
            else:  # 고급
                await say("🎓 전문적인 내용 위주로 학습을 진행하겠습니다.")

            # 학습 준비 메시지
            await say("📚 기본 개념을 준비 중입니다... 잠시만 기다려주세요.")

            # FSM 실행하여 기본 개념 설명 (백그라운드에서 처리)
            steps = await run_network_learning_fsm(topic)

            # 태그 정보 저장
            for step in steps:
                if "주요 키워드" in step:
                    tags = [tag.strip() for tag in step.split("🧠 주요 키워드:")[1].split(",")]
                    user_state[user]["tags"] = tags

            # 순차적으로 메시지 전송 (한 번에 몇 개씩 묶어서 전송)
            batch_size = 2
            filtered_steps = [step for step in steps if "수준 테스트" not in step and "세부 학습 주제" not in step]

            for i in range(0, len(filtered_steps), batch_size):
                batch = filtered_steps[i:i+batch_size]
                message = "\n\n".join(batch)
                await say(message)
                import asyncio
                await asyncio.sleep(0.5)

            # 학습 완료 안내
            await say("✅ 기본 개념 학습이 완료되었습니다. 더 공부하고 싶으시면 '공부시작'을 다시 입력하시거나 '질문 [주제] [질문내용]' 형식으로 질문해주세요.")

            # 상태 변경
            user_state[user]["mode"] = "learning_completed"
            return

        else:
            await say("❗ '초급', '중급', '고급' 중 하나를 선택해주세요.")
            return

    # 5. 테스트 응답 처리
    if user_state.get(user, {}).get("mode") == LearningMode.LEVEL_TEST and "번:" in text:
        topic = user_state[user]["topic"]

        # 테스트 응답 파싱
        answers = []
        try:
            parts = text.split(',')
            for part in parts:
                num_answer = part.split(':')
                if len(num_answer) == 2:
                    q_num = int(num_answer[0].strip().replace('번', '')) - 1
                    answer = num_answer[1].strip()
                    answers.append({"question_index": q_num, "user_answer": answer})
        except:
            await say("❗ 응답 형식이 올바르지 않습니다. '1번: O, 2번: X' 형식으로 입력해주세요.")
            return

        # 채점 및 수준 평가
        await say("🔍 테스트 결과를 분석 중입니다...")

        # 점수 계산
        score = 0
        total = len(user_state[user]["test_questions"])

        for ans in answers:
            q_idx = ans["question_index"]
            if q_idx < total:
                question = user_state[user]["test_questions"][q_idx]
                # 객관식 답변 정규화
                user_answer = ans["user_answer"].strip().upper()
                correct_answer = question["answer"]

                # 객관식 처리 수정
                if question["type"] == "객관식":
                    # 사용자가 A, B, C, D로 답변했다면 그대로 비교
                    pass

                if user_answer == correct_answer:
                    score += 1

        # 수준 평가
        percentage = (score / total) * 100
        if percentage < 40:
            level = "beginner"
            level_display = "초급"
            message = "기초 개념부터 차근차근 배우는 것이 좋겠습니다."
        elif percentage < 75:
            level = "intermediate"
            level_display = "중급"
            message = "기본 개념은 잘 이해하고 있으며, 심화 학습을 진행하면 좋겠습니다."
        else:
            level = "advanced"
            level_display = "고급"
            message = "이미 높은 수준의 이해도를 가지고 있습니다. 전문적인 내용을 학습하면 좋겠습니다."

        # 결과 표시
        await say(f"📊 *테스트 결과*: {total}문제 중 {score}문제 정답")
        await say(f"🎯 현재 {topic} 이해도는 *{level_display}* 수준으로 평가되었습니다.")
        await say(message)

        # 정답 및 해설 제공
        await say("\n📝 *정답 및 해설*:")
        for i, q in enumerate(user_state[user]["test_questions"]):
            if q["type"] == "OX":
                await say(f"{i+1}. [OX] {q['question']} (정답: {q['answer']})")
            elif q["type"] == "객관식":
                opt_idx = ord(q["answer"]) - ord('A')
                opt_text = q["options"][opt_idx] if 0 <= opt_idx < len(q["options"]) else q["answer"]
                await say(f"{i+1}. [객관식] {q['question']} (정답: {q['answer']}. {opt_text})")
            else:
                await say(f"{i+1}. [주관식] {q['question']} (모범답안: {q['answer']})")

        # 사용자 수준 저장
        user_state[user]["user_level"] = level

        # 학습 준비 메시지
        await say("📚 기본 개념을 준비 중입니다... 잠시만 기다려주세요.")

        # FSM 실행하여 기본 개념 설명 (백그라운드에서 처리)
        steps = await run_network_learning_fsm(topic)

        # 태그 정보 저장
        for step in steps:
            if "주요 키워드" in step:
                tags = [tag.strip() for tag in step.split("🧠 주요 키워드:")[1].split(",")]
                user_state[user]["tags"] = tags

        # 순차적으로 메시지 전송 (한 번에 몇 개씩 묶어서 전송)
        batch_size = 2
        filtered_steps = [step for step in steps if "수준 테스트" not in step and "세부 학습 주제" not in step]

        for i in range(0, len(filtered_steps), batch_size):
            batch = filtered_steps[i:i+batch_size]
            message = "\n\n".join(batch)
            await say(message)
            import asyncio
            await asyncio.sleep(0.5)

        # 학습 완료 안내
        await say("✅ 기본 개념 학습이 완료되었습니다. 더 공부하고 싶으시면 '공부시작'을 다시 입력하시거나 '질문 [주제] [질문내용]' 형식으로 질문해주세요.")

        # 상태 변경
        user_state[user]["mode"] = "learning_completed"
        return

    # 6. 학습 완료 후 선택지 처리
    if user_state.get(user, {}).get("mode") == "learning_completed":
        topic = user_state[user]["topic"]

        if text == "1" or "퀴즈" in text:
            # 퀴즈 모드로 전환
            user_state[user]["mode"] = LearningMode.QUIZ
            await say("📝 *퀴즈를 시작합니다*")

            # 여기서 퀴즈 생성 함수 호출
            from app.chains.network_graph_fsm import generate_quiz, NetworkGraphState
            from typing import Dict, Any, cast

            state: Dict[str, Any] = {
                "topic": topic,
                "tags": user_state[user].get("tags", []),
                "mode": "quiz",
                "questions": [],
                "current_index": 0,
                "explanation": "",
                "user_question": "",
                "level_test_questions": [],
                "level_test_responses": [],
                "user_level": "beginner",
                "subtopics": [],
                "selected_subtopic": "",
                "interview_questions": [],
                "current_interview_index": 0
            }

            result = generate_quiz(cast(NetworkGraphState, state))

            # 퀴즈 출력
            await say("다음 문제들에 답해보세요:")
            for i, question in enumerate(result["questions"]):
                if question["type"] == "OX":
                    await say(f"{i+1}. [OX] {question['question']}")
                elif question["type"] == "객관식":
                    options_text = "\n   ".join([f"{chr(65+j)}. {opt}" for j, opt in enumerate(question["options"])])
                    await say(f"{i+1}. [객관식] {question['question']}\n   {options_text}")
                else:
                    await say(f"{i+1}. [주관식] {question['question']}")

            # 퀴즈 답변 안내
            await say("답변을 완료하셨으면 '정답 확인'이라고 입력해주세요.")
            user_state[user]["quiz_questions"] = result["questions"]
            return

        elif text == "2" or "질문" in text:
            await say("💬 특정 개념에 대해 질문하실 수 있습니다.")
            await say("'질문 [주제] [질문내용]' 형식으로 입력해주세요. 예: '질문 OSI 7계층 각 계층의 역할은 무엇인가요?'")
            return

        elif text == "3" or "면접" in text:
            # 면접 질문 모드로 전환
            steps = await start_interview_session(topic)
            user_state[user]["mode"] = LearningMode.INTERVIEW
            user_state[user]["interview_index"] = 0

            for step in steps:
                await say(step)
            return

        else:
            await say("❗ 1, 2, 3 중 하나를 선택하거나, '질문 [주제] [질문내용]' 형식으로 질문해주세요.")
            return

    # 7. 정답 확인 요청
    if user_state.get(user, {}).get("mode") == LearningMode.QUIZ and text == "정답 확인":
        await say("📝 *퀴즈 정답입니다*")

        for i, question in enumerate(user_state[user].get("quiz_questions", [])):
            if question["type"] == "OX":
                await say(f"{i+1}. [OX] {question['question']} (정답: {question['answer']})")
            elif question["type"] == "객관식":
                options_text = "\n   ".join([f"{chr(65+j)}. {opt}" for j, opt in enumerate(question["options"])])
                await say(f"{i+1}. [객관식] {question['question']}\n   {options_text}\n   (정답: {question['answer']})")
            else:
                await say(f"{i+1}. [주관식] {question['question']} (정답: {question['answer']})")

        # 면접 연습 권유 메시지
        await say(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "퀴즈가 끝났습니다. 다음으로 무엇을 하시겠습니까?"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "*1️⃣ 면접 질문 연습*: 면접 질문으로 심화 연습을 해봅니다.\n"
                            "*2️⃣ 새 주제 공부*: 다른 주제를 선택합니다.\n"
                            "*3️⃣ 질문하기*: 특정 개념에 대해 질문합니다."
                        )
                    }
                }
            ]
        )
        user_state[user]["mode"] = "after_quiz"
        return

    # 8. 퀴즈 후 선택지 처리
    if user_state.get(user, {}).get("mode") == "after_quiz":
        if text == "1" or "면접" in text:
            topic = user_state[user]["topic"]
            steps = await start_interview_session(topic)
            user_state[user]["mode"] = LearningMode.INTERVIEW
            user_state[user]["interview_index"] = 0

            for step in steps:
                await say(step)
            return

        elif text == "2" or "새 주제" in text or "새주제" in text:
            # 주제 선택으로 돌아가기
            user_state[user] = {"mode": LearningMode.SELECTING_TOPIC}

            await say(
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                "📘 다른 주제를 선택해볼까요?\n"
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
                    }
                ]
            )
            return

        elif text == "3" or "질문" in text:
            await say("💬 특정 개념에 대해 질문하실 수 있습니다.")
            await say("'질문 [주제] [질문내용]' 형식으로 입력해주세요. 예: '질문 OSI 7계층 각 계층의 역할은 무엇인가요?'")
            return

        else:
            await say("❗ 1, 2, 3 중 하나를 선택하거나, '질문 [주제] [질문내용]' 형식으로 질문해주세요.")
            return

    # 9. 사용자 질문 처리 (모든 모드에서 가능)
    if text.startswith("질문") and len(text.split()) >= 3:
        parts = text.split(" ", 2)
        tag_name = parts[1]
        question = parts[2]
        topic = user_state.get(user, {}).get("topic", "네트워크")  # 기본값 설정

        # 태그 인덱스 찾기
        tags = user_state.get(user, {}).get("tags", [])

        if not tags:
            # 태그가 없으면 기본 태그 생성
            tags = ["OSI 7계층", "TCP/IP", "HTTP", "DNS", "라우팅"]
            user_state[user]["tags"] = tags

        try:
            tag_index = next((i for i, tag in enumerate(tags) if tag.lower() == tag_name.lower()), 0)
        except:
            tag_index = 0

        # 즉시 응답
        await say(f"🤔 '{tag_name}'에 대한 질문에 답변을 준비하고 있습니다...")

        # 질문 처리 (백그라운드)
        answer = await answer_user_question(topic, tag_index, question)

        # 결과 반환 (응답이 길다면 여러 메시지로 나눠서 전송)
        max_length = 2000
        if len(answer) <= max_length:
            await say(f"📝 *{tag_name}*에 대한 질문: '{question}'\n\n{answer}")
        else:
            # 긴 응답 분할 전송
            await say(f"📝 *{tag_name}*에 대한 질문: '{question}'\n")

            parts = []
            for i in range(0, len(answer), max_length):
                parts.append(answer[i:i+max_length])

            for i, part in enumerate(parts):
                await say(f"[{i+1}/{len(parts)}] {part}")
                import asyncio
                await asyncio.sleep(0.5)

        # 추가 질문 안내
        await say("더 질문하시려면 같은 형식으로 입력해주세요: '질문 [주제] [질문내용]'")
        return