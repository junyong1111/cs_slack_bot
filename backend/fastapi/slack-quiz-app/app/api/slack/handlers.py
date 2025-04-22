from app.services.study_mode import run_network_learning_fsm, process_level_test_answers, study_advanced_topic, start_interview_session, get_next_interview_question, answer_user_question
from app.api.slack.app import slack_app
import json
import random
import re
import os
from slack_sdk.web.async_client import AsyncWebClient
from typing import List, Dict, Any, cast, Tuple
from app.chains.network_graph_fsm import run_fsm, NetworkGraphState
from app.services.study_mode import run_network_learning_fsm as original_run_network_learning_fsm
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

# 클라이언트 인스턴스 생성
slack_client = AsyncWebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

# 사용자별 상태 저장
user_state = {}

# 유효한 주제 정의 (주제 = [태그 리스트])
VALID_TOPICS = {
    "네트워크": [
        "네트워크 토폴리지",
        "OSI 7계층",
        "라우팅",
        "IP 주소체계 (IPv4, IPv6)",
        "서브넷 마스크와 클래스풀",
        "HTTP 프로토콜",
        "쿠키와 세션",
        "HTTP 메서드",
        "반이중화와 전이중화"
    ],
    "운영체제": ["프로세스", "스레드", "CPU 스케줄링", "메모리 관리", "파일 시스템", "가상 메모리", "교착 상태"],
    "데이터베이스": ["SQL", "인덱싱", "정규화", "트랜잭션", "관계형 DB", "NoSQL", "ACID"],
    "자료구조": ["배열", "연결 리스트", "스택", "큐", "트리", "그래프", "해시 테이블"],
    "알고리즘": ["정렬", "검색", "그래프 알고리즘", "다이나믹 프로그래밍", "그리디 알고리즘", "시간 복잡도", "공간 복잡도"],
    "웹": ["HTML", "CSS", "JavaScript", "HTTP", "REST API", "프론트엔드", "백엔드"]
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
    NONE = "none"

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

            # 테스트 문제 생성 함수 정의 (동적 생성 버전)
            async def generate_test_questions(topic):
                from app.services.openai_service import get_completion
                from app.prompts.fsm_prompts import level_test_prompt
                import json

                # 프롬프트 형식 사용하여 동적으로 문제 생성
                prompt = level_test_prompt.format(topic=topic)

                try:
                    # OpenAI API로 문제 생성
                    response = await get_completion(prompt=prompt, temperature=0.8)

                    # JSON 파싱
                    questions = json.loads(response)

                    # 객관식 문제에 대해 보기 정보 추가
                    for i, q in enumerate(questions):
                        q["question_text"] = q.get("question", "")  # 질문 텍스트 필드 통일

                        # OX 문제 처리
                        if q.get("type") == "OX":
                            q["correct_answer"] = q.get("answer", "O")

                        # 객관식 문제 처리
                        elif q.get("type") == "객관식":
                            q["correct_answer"] = q.get("answer", "A")

                            # 보기 옵션 매핑
                            options = {}
                            if "options" in q and isinstance(q["options"], dict):
                                options = q["options"]
                            elif "options" in q and isinstance(q["options"], list):
                                # 리스트를 딕셔너리로 변환
                                for idx, opt_text in enumerate(q["options"]):
                                    opt_key = chr(65 + idx)  # A, B, C, D...
                                    options[opt_key] = opt_text
                                q["options"] = options

                            # 주관식은 그대로 유지

                    return questions
                except Exception as e:
                    print(f"문제 생성 오류: {str(e)}")

                    # 오류 시 기본 문제 생성
                    return [
                        {
                            "type": "OX",
                            "question_text": f"{topic}의 기본 개념을 이해하고 있나요?",
                            "correct_answer": "O",
                            "level": "입문"
                        },
                        {
                            "type": "OX",
                            "question_text": f"{topic}의 심화 개념을 이해하고 있나요?",
                            "correct_answer": "X",
                            "level": "중급"
                        },
                        {
                            "type": "객관식",
                            "question_text": f"{topic}의 주요 용어는 무엇인가요?",
                            "options": {
                                "A": "기본 용어",
                                "B": "중급 용어",
                                "C": "고급 용어",
                                "D": "모두 다"
                            },
                            "correct_answer": "D",
                            "level": "중급"
                        },
                        {
                            "type": "객관식",
                            "question_text": f"{topic}의 핵심 원리는 무엇인가요?",
                            "options": {
                                "A": "핵심 원리 1",
                                "B": "핵심 원리 2",
                                "C": "핵심 원리 3",
                                "D": "위의 모든 것"
                            },
                            "correct_answer": "A",
                            "level": "고급"
                        }
                    ]

            # 비동기적으로 문제 생성 (실제로는 미리 준비된 문제 사용)
            await asyncio.sleep(1)  # 실제 생성처럼 약간의 지연
            questions = await generate_test_questions(topic)

            # 문제 저장
            user_state[user]["test_questions"] = questions

            # 문제 출력 (OX 2개, 객관식 2개, 주관식 1개)
            for i, q in enumerate(questions):
                if q["type"] == "OX":
                    # OX 문제는 버튼으로 처리
                    await say(
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*{i+1}. [OX 문제]*\n{q['question_text']}"
                                }
                            },
                            {
                                "type": "actions",
                                "block_id": f"ox_question_{i}",
                                "elements": [
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "O (맞음)",
                                            "emoji": True
                                        },
                                        "style": "primary",
                                        "value": f"ox_{i}_O",
                                        "action_id": f"ox_answer_{i}_O"
                                    },
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "X (틀림)",
                                            "emoji": True
                                        },
                                        "style": "danger",
                                        "value": f"ox_{i}_X",
                                        "action_id": f"ox_answer_{i}_X"
                                    }
                                ]
                            }
                        ]
                    )
                elif q["type"] == "객관식":
                    # 객관식도 버튼으로 처리
                    option_buttons = []
                    for j, opt in enumerate(q["options"]):
                        option_letter = chr(65 + j)  # A, B, C, D...
                        option_buttons.append({
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": f"{option_letter}",
                                "emoji": True
                            },
                            "value": f"mc_{i}_{option_letter}",
                            "action_id": f"mc_answer_{i}_{option_letter}"
                        })

                    await say(
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*{i+1}. [객관식 문제]*\n{q['question_text']}"
                                }
                            }
                        ]
                    )

                    # 각 객관식 옵션을 별도로 표시
                    for j, opt in enumerate(q["options"]):
                        option_letter = chr(65 + j)
                        await say(
                            blocks=[
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"*{option_letter}.* {opt}"
                                    }
                                }
                            ]
                        )

                    # 객관식 선택 버튼 표시
                    await say(
                        blocks=[
                            {
                                "type": "actions",
                                "block_id": f"mc_question_{i}",
                                "elements": option_buttons
                            }
                        ]
                    )
                else:
                    # 주관식 메시지 개선
                    await say(
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*{i+1}. [주관식 문제]*\n{q['question_text']}"
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "아래에 답변을 자유롭게 작성해주세요."
                                }
                            }
                        ]
                    )

            # 답변 안내 메시지 개선
            await say(
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*📝 답변 방법*"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "1. OX 문제: 위 버튼을 클릭하여 응답하세요.\n2. 객관식: '3번: C' 또는 '3: C' 형식으로 입력하세요.\n3. 주관식: '5번: 답변 내용' 형식으로 입력하세요."
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "모든 답변을 마치면 '답변 제출' 또는 '제출완료'라고 입력하세요."
                        }
                    }
                ]
            )
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
            steps = await original_run_network_learning_fsm(topic)

            # 태그 정보 저장
            for step in steps:
                if "주요 키워드" in step:
                    tags = [tag.strip() for tag in step.split("🧠 주요 키워드:")[1].split(",")]
                    user_state[user]["tags"] = tags

            # 순차적으로 메시지 전송 (한 번에 몇 개씩 묶어서 전송)
            batch_size = 1  # 한 번에 하나의 메시지만 보내도록 수정
            filtered_steps = [step for step in steps if "수준 테스트" not in step and "세부 학습 주제" not in step]

            for i in range(0, len(filtered_steps), batch_size):
                batch = filtered_steps[i:i+batch_size]
                for message in batch:
                    # 이모지 처리
                    if message.startswith("🧠") or message.startswith("📚") or message.startswith("📋"):
                        # 각 이모지 줄은 별도로 전송
                        await say(message)
                    else:
                        # 일반 텍스트는 그대로 전송
                        await say(message)
                    import asyncio
                    await asyncio.sleep(0.5)  # 메시지 간 약간의 지연

            # 학습 완료 안내
            await say("✅ 기본 개념 학습이 완료되었습니다. 더 공부하고 싶으시면 '공부시작'을 다시 입력하시거나 '질문 [주제] [질문내용]' 형식으로 질문해주세요.")

            # 상태 변경
            user_state[user]["mode"] = "learning_completed"
            return

        else:
            await say("❗ '초급', '중급', '고급' 중 하나를 선택해주세요.")
            return

    # 5. 테스트 응답 처리
    if user_state.get(user, {}).get("mode") == LearningMode.LEVEL_TEST and (text.lower() == "답변 제출" or text.lower() == "제출완료" or "번:" in text):
        topic = user_state[user]["topic"]

        # 테스트 응답 파싱
        answers = []

        # 버튼으로 저장된 OX 답변 먼저 처리
        if "user_ox_answers" in user_state.get(user, {}):
            for idx, ans in user_state[user]["user_ox_answers"].items():
                answers.append({"question_index": int(idx), "user_answer": ans})

        # 버튼으로 저장된 객관식 답변 처리
        if "user_mc_answers" in user_state.get(user, {}):
            for idx, ans in user_state[user]["user_mc_answers"].items():
                answers.append({"question_index": int(idx), "user_answer": ans})

        try:
            # 텍스트로 입력된 답변 처리
            if "번:" in text:
                # 여러 형식의 구분자 처리
                # 쉼표, 줄바꿈 또는 세미콜론으로 답변이 구분될 수 있음
                if ',' in text:
                    parts = text.split(',')
                elif '\n' in text:
                    parts = text.split('\n')
                elif ';' in text:
                    parts = text.split(';')
                else:
                    parts = [text]  # 하나의 답변만 있는 경우

                for part in parts:
                    part = part.strip()
                    if not part:  # 빈 문자열 건너뛰기
                        continue

                    # 다양한 형식 지원 (번:답, 번: 답, 번. 답, 번) 답, 번-답)
                    if ':' in part:
                        split_char = ':'
                    elif '.' in part and not part.startswith('http'):  # URL이 아닌 경우에만
                        split_char = '.'
                    elif ')' in part:
                        split_char = ')'
                    elif '-' in part:
                        split_char = '-'
                    else:
                        # 구분자가 없으면 질문 번호를 추출할 수 없음
                        continue

                    num_answer = part.split(split_char, 1)
                    if len(num_answer) == 2:
                        # 질문 번호에서 숫자만 추출
                        import re
                        num_str = re.search(r'\d+', num_answer[0])
                        if num_str:
                            q_num = int(num_str.group()) - 1
                            answer = num_answer[1].strip()
                            answers.append({"question_index": q_num, "user_answer": answer})

                # 답변이 없으면 에러 발생
                if not answers:
                    raise ValueError("답변을 찾을 수 없습니다")

            # 채점 및 수준 평가
            await say(
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "🔍 *테스트 결과를 분석 중입니다...*"
                        }
                    }
                ]
            )

            # 정답 및 해설 제공
            await say(
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "📝 *정답 및 해설*:"
                        }
                    }
                ]
            )

            # 사용자 답변 정보 저장 (맞춘 문제 추적)
            correct_answers = []

            # 각 문제별 정답과 해설을 별도의 메시지로 처리
            for i, q in enumerate(user_state[user]["test_questions"]):
                answer_msg = ""

                # 사용자 답변 확인
                user_answer = ""
                for ans in answers:
                    if ans["question_index"] == i:
                        user_answer = ans["user_answer"].strip()
                        break

                is_correct = False

                if q["type"] == "OX":
                    # OX 문제 정답 확인
                    is_correct = user_answer.upper() == q["answer"]
                    answer_msg = f"{i+1}. [OX] {q['question_text']} (정답: {q['answer']})"
                    if not is_correct:
                        answer_msg += f" - *오답*: 입력하신 답변 '{user_answer}'"

                elif q["type"] == "객관식":
                    # 객관식 정답 변환 및 확인
                    correct_option_idx = ord(q["answer"]) - ord('A')
                    opt_text = q["options"][correct_option_idx] if 0 <= correct_option_idx < len(q["options"]) else q["answer"]

                    # 다양한 입력 형식 처리
                    if user_answer.upper() in ["A", "B", "C", "D"] and user_answer.upper() == q["answer"]:
                        is_correct = True
                    elif user_answer in ["1", "2", "3", "4"] and chr(64 + int(user_answer)) == q["answer"]:
                        is_correct = True
                    elif opt_text.lower() in user_answer.lower() or user_answer.lower() in opt_text.lower():
                        is_correct = True

                    answer_msg = f"{i+1}. [객관식] {q['question_text']} (정답: {q['answer']}. {opt_text})"
                    if not is_correct:
                        answer_msg += f" - *오답*: 입력하신 답변 '{user_answer}'"

                else:  # 주관식
                    # 주관식은 키워드 기반 평가
                    correct_keywords = extract_keywords(q["answer"])
                    user_keywords = extract_keywords(user_answer)

                    # OSI 7계층 같은 특별한 주제 확인
                    special_topics = ["osi", "osi 7", "osi 7계층", "7계층", "tcp/ip", "네트워크 계층"]
                    is_special_topic = any(topic.lower() in q["question_text"].lower() for topic in special_topics)

                    # 핵심 키워드 일치 여부 확인
                    matched_keywords = [k for k in user_keywords if any(similar(k, ck) for ck in correct_keywords)]
                    keyword_match_ratio = len(matched_keywords) / len(correct_keywords) if correct_keywords else 0

                    # 특별한 주제는 더 관대하게 평가 (25% 이상 일치하면 정답으로 간주)
                    threshold = 0.25 if is_special_topic else 0.5

                    # 전체 텍스트 유사도 확인
                    is_similar = similar(user_answer, q["answer"])

                    # 키워드 일치율이 기준치 이상이거나 전체 텍스트가 유사하면 정답으로 간주
                    is_correct = keyword_match_ratio >= threshold or is_similar

                    # 추가 검사: 장문 설명에서 여러 단계나 계층을 설명하는 경우 더 관대하게 평가
                    if not is_correct and len(user_answer) > 100:
                        # 계층 숫자나 주요 프로토콜 언급 확인
                        import re
                        layers = re.findall(r'L\d|계층 \d|레이어 \d|\d 계층|\d 레이어', user_answer)
                        protocols = re.findall(r'TCP|IP|UDP|HTTP|FTP|SMTP|DNS|MAC|ARP|ICMP', user_answer.upper())

                        if (len(layers) >= 3 or len(protocols) >= 3):
                            is_correct = True

                    answer_msg = f"{i+1}. [주관식] {q['question_text']}"
                    answer_msg += f"\n   모범답안: {q['answer']}"

                    if is_correct:
                        matched_percent = int(keyword_match_ratio * 100)
                        answer_msg += f"\n   👍 정답입니다! (키워드 일치도: 약 {matched_percent}%)"
                    else:
                        answer_msg += f"\n   ❗ 아쉽습니다. 핵심 키워드가 부족합니다."
                        if correct_keywords:
                            answer_msg += f"\n   참고할 핵심 키워드: {', '.join(correct_keywords[:5])}"

                # 결과 추적
                if is_correct:
                    correct_answers.append(i)

                await say(answer_msg)

            # 정답 수 다시 계산 (실제 채점 결과 기준)
            score = len(correct_answers)
            total = len(user_state[user]["test_questions"])

            # 수준 평가
            percentage = (score / total) * 100
            if percentage < 40:
                level = "beginner"
                level_display = "초급"
                message = "기초 개념부터 차근차근 배우는 것이 좋겠습니다."
                emoji = "🔰"
            elif percentage < 75:
                level = "intermediate"
                level_display = "중급"
                message = "기본 개념은 잘 이해하고 있으며, 심화 학습을 진행하면 좋겠습니다."
                emoji = "🏆"
            else:
                level = "advanced"
                level_display = "고급"
                message = "이미 높은 수준의 이해도를 가지고 있습니다. 전문적인 내용을 학습하면 좋겠습니다."
                emoji = "🎓"

            # 결과 표시 개선
            await say(
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"📊 *테스트 결과*: {total}문제 중 {score}문제 정답"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"🎯 현재 *{topic}* 이해도는 *{level_display}* 수준으로 평가되었습니다."
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{emoji} {message}"
                        }
                    }
                ]
            )

            # 사용자 수준 저장
            user_state[user]["user_level"] = level

            # 학습 준비 메시지
            await say("📚 기본 개념을 준비 중입니다... 잠시만 기다려주세요.")

            # FSM 실행하여 기본 개념 설명 (백그라운드에서 처리)
            steps = await original_run_network_learning_fsm(topic)

            # 태그 정보 저장
            for step in steps:
                if "주요 키워드" in step:
                    tags = [tag.strip() for tag in step.split("🧠 주요 키워드:")[1].split(",")]
                    user_state[user]["tags"] = tags

            # 순차적으로 메시지 전송 (한 번에 몇 개씩 묶어서 전송)
            batch_size = 1  # 한 번에 하나의 메시지만 보내도록 수정
            filtered_steps = [step for step in steps if "수준 테스트" not in step and "세부 학습 주제" not in step]

            for i in range(0, len(filtered_steps), batch_size):
                batch = filtered_steps[i:i+batch_size]
                for message in batch:
                    # 이모지 처리
                    if message.startswith("🧠") or message.startswith("📚") or message.startswith("📋"):
                        # 각 이모지 줄은 별도로 전송
                        await say(message)
                    else:
                        # 일반 텍스트는 그대로 전송
                        await say(message)
                    import asyncio
                    await asyncio.sleep(0.5)  # 메시지 간 약간의 지연

            # 학습 완료 안내
            await say("✅ 기본 개념 학습이 완료되었습니다. 더 공부하고 싶으시면 '공부시작'을 다시 입력하시거나 '질문 [주제] [질문내용]' 형식으로 질문해주세요.")

            # 상태 변경
            user_state[user]["mode"] = "learning_completed"
            return

        except Exception as e:
            await say(f"❗ 응답 형식을 인식할 수 없습니다. 아래와 같은 형식으로 입력해주세요:\n'1번: O, 2번: X, 3번: C'\n또는\n'1: O\n2: X\n3: C'\n\n오류 내용: {str(e)}")
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
            await say(
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*📝 다음 문제들에 답해보세요:*"
                        }
                    }
                ]
            )
            for i, question in enumerate(result["questions"]):
                if question["type"] == "OX":
                    # OX 문제는 버튼으로 처리
                    await say(
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*{i+1}. [OX 문제]*\n{question['question_text']}"
                                }
                            },
                            {
                                "type": "actions",
                                "block_id": f"ox_question_{i}",
                                "elements": [
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "O (맞음)",
                                            "emoji": True
                                        },
                                        "style": "primary",
                                        "value": f"ox_{i}_O",
                                        "action_id": f"ox_answer_{i}_O"
                                    },
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "X (틀림)",
                                            "emoji": True
                                        },
                                        "style": "danger",
                                        "value": f"ox_{i}_X",
                                        "action_id": f"ox_answer_{i}_X"
                                    }
                                ]
                            }
                        ]
                    )
                elif question["type"] == "객관식":
                    # 객관식도 버튼으로 처리
                    option_buttons = []
                    for j, opt in enumerate(question["options"]):
                        option_letter = chr(65 + j)  # A, B, C, D...
                        option_buttons.append({
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": f"{option_letter}",
                                "emoji": True
                            },
                            "value": f"mc_{i}_{option_letter}",
                            "action_id": f"mc_answer_{i}_{option_letter}"
                        })

                    await say(
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*{i+1}. [객관식 문제]*\n{question['question_text']}"
                                }
                            }
                        ]
                    )

                    # 각 객관식 옵션을 별도로 표시
                    for j, opt in enumerate(question["options"]):
                        option_letter = chr(65 + j)
                        await say(
                            blocks=[
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"*{option_letter}.* {opt}"
                                    }
                                }
                            ]
                        )

                    # 객관식 선택 버튼 표시
                    await say(
                        blocks=[
                            {
                                "type": "actions",
                                "block_id": f"mc_question_{i}",
                                "elements": option_buttons
                            }
                        ]
                    )
                else:
                    # 주관식 메시지 개선
                    await say(
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*{i+1}. [주관식 문제]*\n{question['question_text']}"
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "아래에 답변을 자유롭게 작성해주세요."
                                }
                            }
                        ]
                    )

            # 퀴즈 답변 안내
            await say(
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*📝 답변 방법*"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "1. OX 문제: 위 버튼을 클릭하여 응답하세요.\n2. 객관식: '2번: C' 형식으로 입력하세요.\n3. 주관식: '3번: 답변 내용' 형식으로 입력하세요."
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "모든 답변을 마치면 '정답 확인'이라고 입력하세요."
                        }
                    }
                ]
            )
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
        await say(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "📝 *퀴즈 정답입니다*"
                    }
                }
            ]
        )

        for i, question in enumerate(user_state[user].get("quiz_questions", [])):
            if question["type"] == "OX":
                # OX 문제 정답 표시 개선
                correct_answer = question["answer"]

                # 사용자 답변 확인 (버튼 또는 텍스트 입력)
                user_answer = ""
                if "user_quiz_ox_answers" in user_state.get(user, {}) and i in user_state[user]["user_quiz_ox_answers"]:
                    user_answer = user_state[user]["user_quiz_ox_answers"][i]

                is_correct = user_answer == correct_answer

                result_icon = "✅" if is_correct else "❌"
                result_text = "정답입니다!" if is_correct else "오답입니다."

                await say(
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*{i+1}. [OX 문제]* {question['question_text']}"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*정답: {correct_answer}*"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"{result_icon} {result_text}" + (f" 입력하신 답변: {user_answer}" if user_answer else "")
                            }
                        }
                    ]
                )
            elif question["type"] == "객관식":
                # 객관식 정답 개선
                correct_answer_idx = ord(question["answer"]) - ord('A')
                correct_text = f"{question['answer']}. {question['options'][correct_answer_idx]}"

                options_text = []
                for j, opt in enumerate(question["options"]):
                    option_letter = chr(65 + j)
                    if option_letter == question["answer"]:
                        options_text.append(f"*{option_letter}. {opt}* ✅")
                    else:
                        options_text.append(f"{option_letter}. {opt}")

                await say(
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*{i+1}. [객관식 문제]* {question['question_text']}"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "*정답:*\n" + "\n".join(options_text)
                            }
                        }
                    ]
                )
            else:
                # 주관식 정답 개선
                await say(
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*{i+1}. [주관식 문제]* {question['question_text']}"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*모범 답안:* {question['answer']}"
                            }
                        }
                    ]
                )

        # 면접 연습 권유 메시지 개선
        await say(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🎉 *퀴즈가 끝났습니다. 다음으로 무엇을 하시겠습니까?*"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "1️⃣ 면접 질문 연습",
                                "emoji": True
                            },
                            "value": "interview_practice",
                            "action_id": "select_interview_practice"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "2️⃣ 새 주제 공부",
                                "emoji": True
                            },
                            "value": "new_topic",
                            "action_id": "select_new_topic"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "3️⃣ 질문하기",
                                "emoji": True
                            },
                            "value": "ask_question",
                            "action_id": "select_ask_question"
                        }
                    ]
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
                                "*다른 주제를 선택해볼까요?*\n"
                                "*아래 CS 필수 지식 카테고리 중 하나를 선택해주세요!*"
                            )
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "네트워크",
                                    "emoji": True
                                },
                                "value": "network",
                                "action_id": "topic_network"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "운영체제",
                                    "emoji": True
                                },
                                "value": "os",
                                "action_id": "topic_os"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "데이터베이스",
                                    "emoji": True
                                },
                                "value": "database",
                                "action_id": "topic_db"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "자료구조/알고리즘",
                                    "emoji": True
                                },
                                "value": "ds_algo",
                                "action_id": "topic_ds_algo"
                            }
                        ]
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

# 키워드 추출 함수
def extract_keywords(text):
    """텍스트에서 핵심 키워드를 추출합니다."""
    # 불용어(stopwords) 정의
    stopwords = ["이", "그", "저", "것", "수", "등", "및", "에서", "에게", "으로", "로", "이다", "있다", "하다", "이는", "통해", "위해", "따라", "의해", "때문에", "위한", "있는", "있습니다", "합니다", "입니다", "그리고", "또한", "그러나", "하지만", "이지만", "그래서", "따라서", "그러므로", "그리하여", "때문에", "이러한", "그러한", "이런", "그런"]

    # 특수문자 및 숫자 제거
    import re
    clean_text = re.sub(r'[^\w\s]', ' ', text)
    clean_text = re.sub(r'\d+', ' ', clean_text)

    # 단어 분리 및 불용어 제거
    words = [word.strip().lower() for word in clean_text.split() if len(word.strip()) > 1]
    keywords = [word for word in words if word not in stopwords]

    return keywords

# 문자열 유사도 함수
def similar(a, b):
    """두 문자열의 유사도를 확인합니다."""
    if not a or not b:
        return False

    a = a.lower()
    b = b.lower()

    # 완전 일치
    if a == b:
        return True

    # 한 문자열이 다른 문자열에 포함되는 경우
    if a in b or b in a:
        return True

    # 자카드 유사도 계산 (Levenshtein 없이 구현)
    words_a = set(a.split())
    words_b = set(b.split())

    if not words_a or not words_b:
        return False

    intersection = len(words_a.intersection(words_b))
    union = len(words_a.union(words_b))

    if union == 0:
        return False

    jaccard = intersection / union
    return jaccard >= 0.3  # 30% 이상 유사하면 유사한 것으로 판단

# OX 버튼 핸들러 수정
@slack_app.action(re.compile("ox_answer_(\d+)_([OX])"))
async def handle_ox_button(ack, body, action, respond):
    try:
        await ack()

        # 액션 ID에서 정보 추출
        match = re.match(r"ox_answer_(\d+)_([OX])", action["action_id"])
        if not match:
            await respond("알 수 없는 응답입니다.")
            return

        question_idx = int(match.group(1))
        answer = match.group(2)

        # 유저 정보 및 채널 정보 추출
        user = body["user"]["id"]
        channel = body.get("channel", {}).get("id")

        # 현재 사용자 모드 확인
        current_mode = user_state.get(user, {}).get("mode", None)

        if current_mode == LearningMode.LEVEL_TEST:
            # 수준 테스트 모드일 경우 OX 답변 저장
            if "user_ox_answers" not in user_state.get(user, {}):
                user_state[user]["user_ox_answers"] = {}

            user_state[user]["user_ox_answers"][str(question_idx)] = answer

            # 버튼 클릭 확인 메시지 (임시 메시지)
            await slack_client.chat_postEphemeral(
                channel=channel,
                user=user,
                text=f"✅ 수준 테스트 OX 질문 {question_idx+1}에 '{answer}' 답변이 저장되었습니다."
            )

            # 버튼 비활성화 처리 업데이트
            try:
                original_message = body["message"]
                new_blocks = original_message["blocks"]

                # 버튼 블록 찾기 (actions 블록)
                for block_idx, block in enumerate(new_blocks):
                    if block["type"] == "actions":
                        for btn_idx, btn in enumerate(block["elements"]):
                            if btn["action_id"] == action["action_id"]:
                                # 클릭한 버튼 강조 표시
                                new_blocks[block_idx]["elements"][btn_idx]["style"] = "primary"
                            elif btn["action_id"].startswith(f"ox_answer_{question_idx}_"):
                                # 다른 버튼 스타일 제거
                                if "style" in new_blocks[block_idx]["elements"][btn_idx]:
                                    del new_blocks[block_idx]["elements"][btn_idx]["style"]

                # 업데이트된 메시지 전송
                await slack_client.chat_update(
                    channel=channel,
                    ts=original_message["ts"],
                    blocks=new_blocks,
                    text=original_message.get("text", "Quiz Question")
                )
            except Exception as update_err:
                print(f"메시지 업데이트 오류: {str(update_err)}")

        elif current_mode == LearningMode.QUIZ:
            # 퀴즈 모드일 경우 OX 답변 저장
            if "user_quiz_ox_answers" not in user_state.get(user, {}):
                user_state[user]["user_quiz_ox_answers"] = {}

            user_state[user]["user_quiz_ox_answers"][str(question_idx)] = answer

            # 버튼 클릭 확인 메시지 (임시 메시지)
            await slack_client.chat_postEphemeral(
                channel=channel,
                user=user,
                text=f"✅ 퀴즈 OX 질문 {question_idx+1}에 '{answer}' 답변이 저장되었습니다."
            )

            # 버튼 비활성화 처리 업데이트
            try:
                original_message = body["message"]
                new_blocks = original_message["blocks"]

                # 버튼 블록 찾기 (actions 블록)
                for block_idx, block in enumerate(new_blocks):
                    if block["type"] == "actions":
                        for btn_idx, btn in enumerate(block["elements"]):
                            if btn["action_id"] == action["action_id"]:
                                # 클릭한 버튼 강조 표시
                                new_blocks[block_idx]["elements"][btn_idx]["style"] = "primary"
                            elif btn["action_id"].startswith(f"ox_answer_{question_idx}_"):
                                # 다른 버튼 스타일 제거
                                if "style" in new_blocks[block_idx]["elements"][btn_idx]:
                                    del new_blocks[block_idx]["elements"][btn_idx]["style"]

                # 업데이트된 메시지 전송
                await slack_client.chat_update(
                    channel=channel,
                    ts=original_message["ts"],
                    blocks=new_blocks,
                    text=original_message.get("text", "Quiz Question")
                )
            except Exception as update_err:
                print(f"메시지 업데이트 오류: {str(update_err)}")
        else:
            # 알 수 없는 모드
            await slack_client.chat_postEphemeral(
                channel=channel,
                user=user,
                text="⚠️ 현재 OX 응답을 처리할 수 없는 상태입니다. 질문 내용을 다시 확인해주세요."
            )

    except Exception as e:
        print(f"OX 버튼 처리 오류: {str(e)}")
        await respond(f"응답 처리 중 오류가 발생했습니다: {str(e)}")

# 객관식 버튼 핸들러 수정
@slack_app.action(re.compile("mc_answer_(\d+)_([A-D])"))
async def handle_mc_button(ack, body, action, respond):
    try:
        await ack()

        # 액션 ID에서 정보 추출
        match = re.match(r"mc_answer_(\d+)_([A-D])", action["action_id"])
        if not match:
            await respond("알 수 없는 응답입니다.")
            return

        question_idx = int(match.group(1))
        answer = match.group(2)

        # 유저 정보 및 채널 정보 추출
        user = body["user"]["id"]
        channel = body.get("channel", {}).get("id")

        # 현재 사용자 모드 확인
        current_mode = user_state.get(user, {}).get("mode", None)

        if current_mode == LearningMode.LEVEL_TEST:
            # 수준 테스트 모드일 경우 객관식 답변 저장
            if "user_mc_answers" not in user_state.get(user, {}):
                user_state[user]["user_mc_answers"] = {}

            user_state[user]["user_mc_answers"][str(question_idx)] = answer

            # 버튼 클릭 확인 메시지 (임시 메시지)
            await slack_client.chat_postEphemeral(
                channel=channel,
                user=user,
                text=f"✅ 수준 테스트 객관식 질문 {question_idx+1}에 '{answer}' 답변이 저장되었습니다."
            )

            # 버튼 비활성화 처리 업데이트
            try:
                original_message = body["message"]
                new_blocks = original_message["blocks"]

                # 버튼 블록 찾기 (actions 블록)
                for block_idx, block in enumerate(new_blocks):
                    if block["type"] == "actions":
                        for btn_idx, btn in enumerate(block["elements"]):
                            if btn["action_id"] == action["action_id"]:
                                # 클릭한 버튼 강조 표시
                                new_blocks[block_idx]["elements"][btn_idx]["style"] = "primary"
                            elif btn["action_id"].startswith(f"mc_answer_{question_idx}_"):
                                # 다른 버튼 스타일 제거
                                if "style" in new_blocks[block_idx]["elements"][btn_idx]:
                                    del new_blocks[block_idx]["elements"][btn_idx]["style"]

                # 업데이트된 메시지 전송
                await slack_client.chat_update(
                    channel=channel,
                    ts=original_message["ts"],
                    blocks=new_blocks,
                    text=original_message.get("text", "Quiz Question")
                )
            except Exception as update_err:
                print(f"메시지 업데이트 오류: {str(update_err)}")

        elif current_mode == LearningMode.QUIZ:
            # 퀴즈 모드의 객관식 답변 저장
            if "user_quiz_mc_answers" not in user_state.get(user, {}):
                user_state[user]["user_quiz_mc_answers"] = {}

            user_state[user]["user_quiz_mc_answers"][str(question_idx)] = answer

            # 버튼 클릭 확인 메시지 (임시 메시지)
            await slack_client.chat_postEphemeral(
                channel=channel,
                user=user,
                text=f"✅ 퀴즈 객관식 질문 {question_idx+1}에 '{answer}' 답변이 저장되었습니다."
            )

            # 버튼 비활성화 처리 업데이트
            try:
                original_message = body["message"]
                new_blocks = original_message["blocks"]

                # 버튼 블록 찾기 (actions 블록)
                for block_idx, block in enumerate(new_blocks):
                    if block["type"] == "actions":
                        for btn_idx, btn in enumerate(block["elements"]):
                            if btn["action_id"] == action["action_id"]:
                                # 클릭한 버튼 강조 표시
                                new_blocks[block_idx]["elements"][btn_idx]["style"] = "primary"
                            elif btn["action_id"].startswith(f"mc_answer_{question_idx}_"):
                                # 다른 버튼 스타일 제거
                                if "style" in new_blocks[block_idx]["elements"][btn_idx]:
                                    del new_blocks[block_idx]["elements"][btn_idx]["style"]

                # 업데이트된 메시지 전송
                await slack_client.chat_update(
                    channel=channel,
                    ts=original_message["ts"],
                    blocks=new_blocks,
                    text=original_message.get("text", "Quiz Question")
                )
            except Exception as update_err:
                print(f"메시지 업데이트 오류: {str(update_err)}")
        else:
            # 알 수 없는 모드
            await slack_client.chat_postEphemeral(
                channel=channel,
                user=user,
                text="⚠️ 현재 객관식 응답을 처리할 수 없는 상태입니다. 질문 내용을 다시 확인해주세요."
            )
    except Exception as e:
        print(f"객관식 버튼 처리 오류: {str(e)}")
        await respond(f"응답 처리 중 오류가 발생했습니다: {str(e)}")

# 면접 연습 및 새 주제 버튼 핸들러 추가
@slack_app.action("select_interview_practice")
async def handle_interview_practice(ack, body, say):
    await ack()
    user = body["user"]["id"]
    topic = user_state.get(user, {}).get("topic", "네트워크")

    steps = await start_interview_session(topic)
    user_state[user]["mode"] = LearningMode.INTERVIEW
    user_state[user]["interview_index"] = 0

    for step in steps:
        await say(step)

@slack_app.action("select_new_topic")
async def handle_new_topic(ack, body, say):
    await ack()
    user = body["user"]["id"]

    # 주제 선택으로 돌아가기
    user_state[user] = {"mode": LearningMode.SELECTING_TOPIC}

    await say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "📘 *다른 주제를 선택해볼까요?*\n*아래 CS 필수 지식 카테고리 중 하나를 선택해주세요!*"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "네트워크",
                            "emoji": True
                        },
                        "value": "network",
                        "action_id": "topic_network"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "운영체제",
                            "emoji": True
                        },
                        "value": "os",
                        "action_id": "topic_os"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "데이터베이스",
                            "emoji": True
                        },
                        "value": "database",
                        "action_id": "topic_db"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "자료구조/알고리즘",
                            "emoji": True
                        },
                        "value": "ds_algo",
                        "action_id": "topic_ds_algo"
                    }
                ]
            }
        ]
    )

@slack_app.action("select_ask_question")
async def handle_ask_question(ack, body, say):
    await ack()

    await say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "💬 *특정 개념에 대해 질문하실 수 있습니다.*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "'질문 [주제] [질문내용]' 형식으로 입력해주세요. 예: '질문 OSI 7계층 각 계층의 역할은 무엇인가요?'"
                }
            }
        ]
    )

# 주제 선택 버튼 핸들러 추가
@slack_app.action(re.compile("topic_(.+)"))
async def handle_topic_selection(ack, body, action):
    await ack()

    # 액션 ID에서 주제 추출
    match = re.match(r"topic_(.+)", action["action_id"])
    if match:
        topic_key = match.group(1)

        user = body["user"]["id"]

        # 주제 맵핑
        topic_mapping = {
            "network": "네트워크",
            "os": "운영체제",
            "db": "데이터베이스",
            "ds_algo": "자료구조"
        }

        topic = topic_mapping.get(topic_key, "네트워크")

        # 기존 핸들러와 동일한 로직 실행
        user_state[user] = {"mode": LearningMode.SELECTING_LEVEL, "topic": topic}

        await slack_client.chat_postMessage(
            channel=body["channel"]["id"],
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"💡 *{topic}* 학습을 시작합니다! 학습 수준을 선택해주세요:"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "초급",
                                "emoji": True
                            },
                            "value": "beginner",
                            "action_id": "level_beginner"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "중급",
                                "emoji": True
                            },
                            "value": "intermediate",
                            "action_id": "level_intermediate"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "고급",
                                "emoji": True
                            },
                            "value": "advanced",
                            "action_id": "level_advanced"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "테스트로 결정",
                                "emoji": True
                            },
                            "value": "test",
                            "action_id": "level_test"
                        }
                    ]
                }
            ]
        )

# 레벨 선택 버튼 핸들러 추가
@slack_app.action(re.compile("level_(.+)"))
async def handle_level_selection(ack, body, action):
    await ack()

    # 액션 ID에서 레벨 추출
    match = re.match(r"level_(.+)", action["action_id"])
    if match:
        level = match.group(1)

        user = body["user"]["id"]
        topic = user_state.get(user, {}).get("topic", "네트워크")

        if level == "test":
            # 테스트 모드로 전환
            user_state[user]["mode"] = LearningMode.LEVEL_TEST

            # 테스트 시작 메시지
            await slack_client.chat_postMessage(
                channel=body["channel"]["id"],
                text="📝 *수준 테스트를 시작합니다*"
            )
            await slack_client.chat_postMessage(
                channel=body["channel"]["id"],
                text="테스트는 OX 문제 2개, 객관식 문제 2개, 주관식 문제 1개로 구성됩니다."
            )
            await slack_client.chat_postMessage(
                channel=body["channel"]["id"],
                text="🔍 테스트 문제를 생성하고 있습니다..."
            )

            # 테스트 문제 생성 및 표시 로직 호출
            # (여기서 generate_test_questions 함수를 호출하는 로직이 필요하지만, 위 코드에 없어 실제 구현은 생략)
        else:
            # 선택된 레벨로 설정
            level_display = {"beginner": "초급", "intermediate": "중급", "advanced": "고급"}.get(level, "초급")
            user_state[user]["user_level"] = level

            await slack_client.chat_postMessage(
                channel=body["channel"]["id"],
                text=f"✅ *{level_display}* 수준으로 설정되었습니다. {topic} 학습을 시작합니다!"
            )

            # 수준별 다른 메시지 추가
            if level == "beginner":
                await slack_client.chat_postMessage(
                    channel=body["channel"]["id"],
                    text="🔰 기초 개념부터 차근차근 설명해 드리겠습니다."
                )
            elif level == "intermediate":
                await slack_client.chat_postMessage(
                    channel=body["channel"]["id"],
                    text="🏆 기본 개념은 빠르게 살펴보고 심화 내용을 중점적으로 학습하겠습니다."
                )
            else:  # advanced
                await slack_client.chat_postMessage(
                    channel=body["channel"]["id"],
                    text="🎓 전문적인 내용 위주로 학습을 진행하겠습니다."
                )

            # 학습 준비 메시지
            await slack_client.chat_postMessage(
                channel=body["channel"]["id"],
                text="📚 기본 개념을 준비 중입니다... 잠시만 기다려주세요."
            )

            # 실제 학습 시작 (기존 코드의 로직을 재활용)
            steps = await run_network_learning_fsm(topic)

            # 기존 코드와 같이 메시지 전송
            for step in steps:
                if step.startswith("🧠") or step.startswith("📚") or step.startswith("📋"):
                    await slack_client.chat_postMessage(
                        channel=body["channel"]["id"],
                        text=step
                    )
                else:
                    await slack_client.chat_postMessage(
                        channel=body["channel"]["id"],
                        text=step
                    )
                import asyncio
                await asyncio.sleep(0.5)

            # 학습 완료 안내
            await slack_client.chat_postMessage(
                channel=body["channel"]["id"],
                text="✅ 기본 개념 학습이 완료되었습니다. 더 공부하고 싶으시면 '공부시작'을 다시 입력하시거나 '질문 [주제] [질문내용]' 형식으로 질문해주세요."
            )

            # 상태 변경
            user_state[user]["mode"] = "learning_completed"

# 테스트 완료 응답 처리 부분 수정
@slack_app.action("test_done")
async def handle_test_done(ack, body, respond):
    await ack()

    user = body["user"]["id"]
    channel = body.get("channel", {}).get("id")

    # 테스트 문제와 정답
    test_questions = user_state.get(user, {}).get("test_questions", [])

    if not test_questions:
        await respond("테스트 문제가 없습니다. 다시 테스트를 시작해주세요.")
        return

    # 사용자 응답 처리
    answers = []

    # 버튼으로 저장된 OX 답변 처리
    if "user_ox_answers" in user_state.get(user, {}):
        for q_idx, ans in user_state[user]["user_ox_answers"].items():
            q_idx = int(q_idx)
            if q_idx < len(test_questions):
                answers.append(ans)

    # 버튼으로 저장된 객관식 답변 처리
    if "user_mc_answers" in user_state.get(user, {}):
        for q_idx, ans in user_state[user]["user_mc_answers"].items():
            q_idx = int(q_idx)
            if q_idx < len(test_questions):
                answers.append(ans)

    # 사용자 응답이 없는 경우
    if not answers:
        await respond("응답한 답변이 없습니다. 테스트 질문에 답해주세요.")
        return

    # 정답 비교
    correct_answers = [q["correct_answer"] for q in test_questions]

    # 사용자 응답과 정답 비교 (응답한 문제만)
    correct_count = 0
    for i, ans in enumerate(answers):
        if i < len(correct_answers) and ans == correct_answers[i]:
            correct_count += 1

    accuracy = correct_count / len(answers) if answers else 0

    # 사용자 수준 평가
    try:
        # 사용자 답변 형식 맞추기
        formatted_responses = []
        for i, ans in enumerate(answers):
            if i < len(test_questions):
                formatted_responses.append({
                    "user_answer": ans,
                    "correct_answer": test_questions[i]["correct_answer"] if i < len(correct_answers) else ""
                })

        # 수준 평가 (기본값 설정)
        user_level = "입문"

        # 정답 비율에 따른 수준 결정
        if accuracy >= 0.8:
            user_level = "고급"
        elif accuracy >= 0.5:
            user_level = "중급"
        else:
            user_level = "입문"

        # 수준별 결과 메시지
        result_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*테스트 결과*\n총 {len(answers)}문제 중 {correct_count}문제 정답! ({accuracy:.1%})"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*평가된 수준: {user_level}*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "테스트에 응답한 내용을 바탕으로 수준을 평가했습니다. 학습을 시작하시겠습니까?"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "학습 시작하기",
                            "emoji": True
                        },
                        "style": "primary",
                        "value": user_level,
                        "action_id": "start_learning"
                    }
                ]
            }
        ]

        # 정답 표시 추가
        answer_texts = []
        user_answer_texts = []

        for i, question in enumerate(test_questions):
            if i < len(answers):
                user_ans = answers[i]
                correct_ans = question["correct_answer"]
                q_text = question["question_text"]

                # OX 문제 여부 확인
                is_ox = correct_ans in ["O", "X"]

                if is_ox:
                    prefix = "✅" if user_ans == correct_ans else "❌"
                    answer_texts.append(f"{prefix} Q{i+1}. {q_text}\n   정답: {correct_ans}, 내 답변: {user_ans}")
                else:
                    # 객관식인 경우
                    prefix = "✅" if user_ans == correct_ans else "❌"

                    # 보기 텍스트 추출
                    options = question.get("options", {})
                    correct_text = options.get(correct_ans, correct_ans)
                    user_text = options.get(user_ans, user_ans)

                    answer_texts.append(f"{prefix} Q{i+1}. {q_text}\n   정답: {correct_ans}({correct_text}), 내 답변: {user_ans}({user_text})")

        if answer_texts:
            result_blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*질문별 결과*\n" + "\n\n".join(answer_texts)
                }
            })

        # 결과 표시
        await slack_client.chat_postMessage(
            channel=channel,
            blocks=result_blocks,
            text="테스트 결과입니다."
        )

        # 사용자 상태 업데이트
        user_state[user]["level"] = user_level
        user_state[user]["mode"] = LearningMode.NONE

        # 테스트 응답 데이터 초기화
        if "user_ox_answers" in user_state[user]:
            del user_state[user]["user_ox_answers"]
        if "user_mc_answers" in user_state[user]:
            del user_state[user]["user_mc_answers"]

    except Exception as e:
        logger.error(f"테스트 결과 처리 중 오류: {str(e)}")
        await respond(f"테스트 결과 처리 중 오류가 발생했습니다: {str(e)}")