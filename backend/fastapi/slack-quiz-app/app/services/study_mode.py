from app.prompts.fsm_prompts import (
    concept_explanation_prompt,
    tag_extraction_prompt,
    quiz_generation_prompt,
    user_question_prompt,
    level_test_prompt,
    subtopic_extraction_prompt,
    advanced_topic_prompt,
    interview_questions_prompt
)
from app.chains.network_graph_fsm import (
    run_fsm,
    generate_level_test,
    evaluate_user_level,
    extract_subtopics,
    explain_advanced_topic,
    generate_interview_questions,
    NetworkGraphState
)
from typing import Dict, List, Any, Tuple, cast
import asyncio
import random

async def run_network_learning_fsm(topic: str) -> List[str]:
    """
    네트워크 학습 FSM을 실행하고 단계별 결과를 반환합니다.
    """
    # 바로 초기 응답을 위한 단계별 메시지
    initial_steps = [
        f"🔍 *{topic}*에 대한 기본 개념을 알아봅시다.",
        f"주요 개념을 정리하고 있습니다... 잠시만 기다려주세요."
    ]

    # 실제 FSM 실행 (시간이 오래 걸릴 수 있음)
    final_state = await run_fsm(topic)

    # 결과 정리
    steps = []

    # 1. 태그 추출 결과
    if "tags" in final_state:
        tags = final_state["tags"]
        tags_str = ", ".join(tags)
        steps.append(f"🧠 주요 키워드: {tags_str}")

    # 2. 기본 개념 설명
    if "explanation" in final_state:
        explanation = final_state["explanation"]
        steps.append(f"📚 기본 개념 설명:\n{explanation}")

    # 3. 수준 테스트 문제 (있는 경우)
    if "level_test_questions" in final_state and final_state["level_test_questions"]:
        questions = final_state["level_test_questions"]
        steps.append("📝 수준 테스트:")
        for i, q in enumerate(questions):
            if q["type"] == "OX":
                steps.append(f"{i+1}. [OX] {q['question']}")
            elif q["type"] == "객관식":
                options = "\n   ".join([f"{chr(65+j)}. {opt}" for j, opt in enumerate(q["options"])])
                steps.append(f"{i+1}. [객관식] {q['question']}\n   {options}")
            else:
                steps.append(f"{i+1}. [주관식] {q['question']}")

    # 4. 세부 학습 주제 (있는 경우)
    if "subtopics" in final_state and final_state["subtopics"]:
        subtopics = final_state["subtopics"]
        steps.append("📋 세부 학습 주제:")
        for i, subtopic in enumerate(subtopics):
            steps.append(f"{i+1}. {subtopic['title']}: {subtopic['description']}")

    return initial_steps + steps

async def process_level_test_answers(topic: str, answers: List[Dict[str, Any]]) -> Tuple[List[str], Dict[str, Any]]:
    """
    사용자의 수준 테스트 답변을 처리하고 결과를 반환합니다.
    """
    # 즉시 응답할 초기 메시지
    initial_steps = [
        "📊 테스트 결과를 분석 중입니다...",
        "☕ 잠시만 기다려주세요..."
    ]

    # 이 함수는 FSM 상태를 직접 조작합니다
    state: Dict[str, Any] = {
        "topic": topic,
        "tags": [],
        "mode": "learning",
        "current_index": 0,
        "explanation": "",
        "user_question": "",
        "level_test_questions": [],
        "level_test_responses": answers,
        "user_level": "",
        "subtopics": [],
        "selected_subtopic": "",
        "interview_questions": [],
        "current_interview_index": 0
    }

    # 먼저 테스트 생성
    state = generate_level_test(cast(NetworkGraphState, state))

    # 사용자 수준 평가
    state = evaluate_user_level(cast(NetworkGraphState, state))
    user_level = state["user_level"]

    # 사용자 수준에 맞는 서브토픽 추출
    state = extract_subtopics(cast(NetworkGraphState, state))

    # 결과 메시지 구성
    steps = []
    steps.append(f"📊 *테스트 결과*: 현재 {topic} 이해도는 *{user_level}* 수준으로 평가되었습니다.")

    # 수준별 메시지
    if user_level == "beginner":
        steps.append("🔰 기초부터 차근차근 학습하는 것을 추천합니다.")
    elif user_level == "intermediate":
        steps.append("🏆 기본 개념은 잘 이해하고 있습니다. 좀 더 심화된 주제를 학습해보세요.")
    else:  # advanced
        steps.append("🎓 이미 높은 수준의 이해도를 갖고 계십니다. 전문적인 주제를 더 공부해보세요.")

    # 추천 서브토픽 목록
    if state["subtopics"]:
        steps.append("\n📋 *추천 학습 주제*:")
        for i, subtopic in enumerate(state["subtopics"]):
            steps.append(f"{i+1}. {subtopic['title']}: {subtopic['description']}")
        steps.append("\n공부하고 싶은 주제의 번호를 입력해주세요.")

    return initial_steps + steps, state

async def study_advanced_topic(topic: str, subtopic_index: int, user_level: str) -> List[str]:
    """
    선택한 서브토픽에 대한 심화 학습을 제공합니다.
    """
    # 즉시 응답할 초기 메시지
    initial_steps = [
        f"📚 선택한 주제에 대한 심화 학습을 준비 중입니다...",
        "💡 곧 자세한 내용이 제공됩니다."
    ]

    # FSM 상태 초기화
    state: Dict[str, Any] = {
        "topic": topic,
        "tags": [],
        "mode": "advanced",
        "current_index": 0,
        "explanation": "",
        "user_question": "",
        "level_test_questions": [],
        "level_test_responses": [],
        "user_level": user_level,
        "subtopics": [],
        "selected_subtopic": subtopic_index,
        "interview_questions": [],
        "current_interview_index": 0
    }

    # 서브토픽 추출 (필요한 경우)
    state = extract_subtopics(cast(NetworkGraphState, state))

    # 선택한 서브토픽이 범위 내에 있는지 확인
    if subtopic_index < 0 or subtopic_index >= len(state["subtopics"]):
        return initial_steps + ["❌ 잘못된 주제 번호입니다. 다시 시도해주세요."]

    # 심화 주제 설명
    state = explain_advanced_topic(cast(NetworkGraphState, state))

    steps = []
    selected_subtopic = state["subtopics"][subtopic_index]["title"]
    steps.append(f"🔍 *{selected_subtopic}* 심화 학습")

    if "advanced_explanation" in state:
        steps.append(state["advanced_explanation"])

    # 추가 학습 안내
    steps.append("\n💬 더 알고 싶은 내용이 있으면 '질문 [주제] [질문내용]' 형식으로 질문하세요.")
    steps.append("🎯 면접 질문을 연습해보고 싶다면 '면접 시작'이라고 입력하세요.")

    return initial_steps + steps

async def start_interview_session(topic: str, subtopic: str = "", user_level: str = "intermediate") -> List[str]:
    """
    면접 세션을 시작하고 첫 번째 질문을 제공합니다.
    """
    # 즉시 응답할 초기 메시지
    initial_steps = [
        "🎯 *면접 질문 연습을 준비 중입니다*",
        "📝 실제 면접에서 자주 나오는 질문들을 준비하고 있습니다..."
    ]

    # FSM 상태 초기화
    state: Dict[str, Any] = {
        "topic": topic,
        "tags": [],
        "mode": "interview",
        "current_index": 0,
        "explanation": "",
        "user_question": "",
        "level_test_questions": [],
        "level_test_responses": [],
        "user_level": user_level,
        "subtopics": [],
        "selected_subtopic": subtopic,
        "interview_questions": [],
        "current_interview_index": 0
    }

    # 면접 질문 생성
    state = generate_interview_questions(cast(NetworkGraphState, state))

    steps = []
    steps.append(f"🎤 *{topic} 관련 면접 질문 연습*")

    if not state["interview_questions"]:
        steps.append("❌ 면접 질문을 생성하는데 문제가 발생했습니다. 다시 시도해주세요.")
        return initial_steps + steps

    # 첫 번째 질문 가져오기
    first_question = state["interview_questions"][0]
    steps.append(f"질문 1: {first_question['question']}")

    # 사용 방법 안내
    steps.append("\n💡 질문에 답변을 생각해보세요. 그런 다음 '정답 확인'을 입력하면 모범 답안을 보여드립니다.")
    steps.append("⏭️ 다음 질문으로 넘어가려면 '다음 질문'이라고 입력하세요.")

    return initial_steps + steps

async def get_next_interview_question(topic: str, index: int, user_level: str = "intermediate") -> Tuple[List[str], bool]:
    """
    다음 면접 질문을 제공합니다.
    """
    # 즉시 응답할 초기 메시지
    initial_steps = [
        "🔄 다음 면접 질문을 준비 중입니다..."
    ]

    # FSM 상태 초기화
    state: Dict[str, Any] = {
        "topic": topic,
        "tags": [],
        "mode": "interview",
        "current_index": 0,
        "explanation": "",
        "user_question": "",
        "level_test_questions": [],
        "level_test_responses": [],
        "user_level": user_level,
        "subtopics": [],
        "selected_subtopic": "",
        "interview_questions": [],
        "current_interview_index": index
    }

    # 면접 질문이 없으면 생성
    if not state["interview_questions"]:
        state = generate_interview_questions(cast(NetworkGraphState, state))

    # 현재 인덱스의 질문 가져오기
    state = get_interview_question(cast(NetworkGraphState, state))

    steps = []

    # 모든 질문을 다 봤는지 확인
    is_completed = False
    if index >= len(state["interview_questions"]):
        steps.append("🎉 *모든 면접 질문을 완료했습니다!*")
        steps.append("다시 연습하려면 '면접 시작'을, 다른 주제를 선택하려면 '공부시작'을 입력하세요.")
        is_completed = True
        return initial_steps + steps, is_completed

    # 현재 질문 표시
    current_question = state["interview_questions"][index]
    steps.append(f"질문 {index+1}: {current_question['question']}")

    # 이전 질문의 모범 답안 표시 (있는 경우)
    if index > 0:
        prev_question = state["interview_questions"][index-1]
        steps.append(f"\n✅ 이전 질문 답변:")
        steps.append(f"Q: {prev_question['question']}")
        steps.append(f"A: {prev_question['answer']}")

    # 사용 방법 안내
    steps.append("\n💡 질문에 답변을 생각해보세요. 그런 다음 '정답 확인'을 입력하면 모범 답안을 보여드립니다.")
    steps.append("⏭️ 다음 질문으로 넘어가려면 '다음 질문'이라고 입력하세요.")

    return initial_steps + steps, is_completed

async def answer_user_question(topic: str, tag_index: int, question: str) -> str:
    """
    사용자 질문에 답변합니다.
    """
    # 시간이 오래 걸릴 수 있는 비동기 처리
    from app.services.openai_service import get_completion

    # 즉시 응답할 텍스트
    initial_text = "질문에 대한 답변을 준비 중입니다..."

    # 프롬프트 구성
    prompt = user_question_prompt.format(topic=topic, tag=f"주제 {tag_index+1}", question=question)

    # 답변 생성
    try:
        response = await get_completion(prompt)
        return response.strip()
    except Exception as e:
        return f"답변을 생성하는 중 오류가 발생했습니다: {str(e)}"