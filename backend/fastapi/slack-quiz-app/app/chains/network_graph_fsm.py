from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Literal, List, Dict, Any, cast, Union, Type
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from app.prompts.fsm_prompts import tag_extraction_prompt, concept_explanation_prompt, level_test_prompt, subtopic_extraction_prompt, advanced_topic_prompt, interview_questions_prompt
import os
from app.core.config import OPENAI_API_KEY  # api_key 설정을 위해 config에서 가져옴
import json
import asyncio

# API 키 설정 (None이 아닌 경우에만)
if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
else:
    # 환경 변수에 API 키가 없는 경우 기본 키 설정 (실제 사용 시 교체 필요)
    os.environ["OPENAI_API_KEY"] = "your-openai-api-key-here"

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

class NetworkGraphState(TypedDict):
    topic: str
    tags: List[str]
    current_index: int
    explanation: str
    questions: List[Dict[str, Any]]
    user_question: str
    mode: Literal["explain", "question", "quiz", "level_test", "subtopic_selection", "advanced_topic", "interview"]
    level_test_questions: List[Dict[str, Any]]
    level_test_responses: List[Dict[str, Any]]
    user_level: str
    subtopics: List[Dict[str, str]]
    selected_subtopic: str
    interview_questions: List[Dict[str, Any]]
    current_interview_index: int

def extract_tags(state: NetworkGraphState) -> NetworkGraphState:
    topic = state["topic"]
    response = llm.invoke(tag_extraction_prompt.format(topic=topic))
    response_text = response.content if hasattr(response, 'content') else str(response)
    tags = [line.strip("-• ").strip() for line in response_text.splitlines() if line.strip()]

    # NetworkGraphState 타입으로 명시적 캐스팅
    return cast(NetworkGraphState, {
        "topic": topic,
        "tags": tags,
        "current_index": 0,
        "explanation": "",
        "questions": [],
        "user_question": "",
        "mode": "explain",
        "level_test_questions": [],
        "level_test_responses": [],
        "user_level": "beginner",
        "subtopics": [],
        "selected_subtopic": "",
        "interview_questions": [],
        "current_interview_index": 0
    })

def explain_current_tag(state: NetworkGraphState) -> NetworkGraphState:
    tag = state["tags"][state["current_index"]]
    response = llm.invoke(concept_explanation_prompt.format(tag=tag))
    response_text = response.content if hasattr(response, 'content') else str(response)
    return cast(NetworkGraphState, {**state, "explanation": response_text})

def next_tag(state: NetworkGraphState) -> NetworkGraphState:
    return cast(NetworkGraphState, {**state, "current_index": state["current_index"] + 1, "explanation": ""})

def answer_user_question(state: NetworkGraphState) -> NetworkGraphState:
    from app.prompts.fsm_prompts import user_question_prompt

    question = state["user_question"]
    tag = state["tags"][state["current_index"]]
    topic = state["topic"]

    response = llm.invoke(user_question_prompt.format(
        topic=topic, tag=tag, question=question
    ))

    response_text = response.content if hasattr(response, 'content') else str(response)
    return cast(NetworkGraphState, {**state, "explanation": response_text, "mode": "explain"})

def generate_quiz(state: NetworkGraphState) -> NetworkGraphState:
    from app.prompts.fsm_prompts import quiz_generation_prompt

    topic = state["topic"]
    tags = state["tags"]

    response = llm.invoke(quiz_generation_prompt.format(
        topic=topic, tags=", ".join(tags)
    ))

    # 퀴즈 형식: [{"type": "객관식", "question": "...", "options": [...], "answer": "..."}, ...]
    import json
    try:
        # content가 있는지 확인하고 문자열로 처리
        content = response.content if hasattr(response, 'content') else str(response)
        questions = json.loads(str(content))  # 확실하게 문자열 변환
    except Exception as e:
        # 파싱 오류시 기본 질문
        questions = [{"type": "OX", "question": f"{topic}에 대한 간단한 질문입니다.", "answer": "O"}]

    return cast(NetworkGraphState, {**state, "questions": questions, "mode": "quiz"})

# 새로 추가된 함수: 사용자 수준 테스트 문제 생성
def generate_level_test(state: NetworkGraphState) -> NetworkGraphState:
    topic = state["topic"]

    # 수준 테스트 문제 생성
    response = llm.invoke(level_test_prompt.format(topic=topic))
    response_text = response.content if hasattr(response, 'content') else str(response)

    try:
        questions = json.loads(str(response_text))
    except Exception as e:
        # 파싱 오류시 기본 질문
        questions = [
            {"type": "OX", "question": f"{topic}의 기본 개념에 대한 질문입니다.", "answer": "O", "level": "기본", "topic": "기본 개념"},
            {"type": "OX", "question": f"{topic}의 중급 개념에 대한 질문입니다.", "answer": "X", "level": "중급", "topic": "중급 개념"}
        ]

    return cast(NetworkGraphState, {**state, "level_test_questions": questions, "mode": "level_test"})

# 사용자 수준 평가 함수
def evaluate_user_level(state: NetworkGraphState) -> NetworkGraphState:
    responses = state["level_test_responses"]
    if not responses:
        return cast(NetworkGraphState, {**state, "user_level": "beginner"})

    # 정답 수 계산
    correct_count = 0
    total_questions = len(responses)

    for response in responses:
        if response.get("user_answer") == response.get("correct_answer"):
            correct_count += 1

    # 정답 비율에 따른 레벨 결정
    accuracy = correct_count / total_questions if total_questions > 0 else 0

    if accuracy >= 0.8:
        user_level = "advanced"
    elif accuracy >= 0.5:
        user_level = "intermediate"
    else:
        user_level = "beginner"

    return cast(NetworkGraphState, {**state, "user_level": user_level, "mode": "subtopic_selection"})

# 세부 주제 추출 함수
def extract_subtopics(state: NetworkGraphState) -> NetworkGraphState:
    topic = state["topic"]

    # 세부 주제 추출
    response = llm.invoke(subtopic_extraction_prompt.format(topic=topic))
    response_text = response.content if hasattr(response, 'content') else str(response)

    try:
        subtopics = json.loads(str(response_text))
    except Exception as e:
        # 파싱 오류시 기본 주제
        subtopics = [
            {"title": f"{topic} 기본", "description": "기본 개념 설명"},
            {"title": f"{topic} 심화", "description": "심화 개념 설명"}
        ]

    return cast(NetworkGraphState, {**state, "subtopics": subtopics})

# 심화 주제 학습 함수
def explain_advanced_topic(state: NetworkGraphState) -> NetworkGraphState:
    topic = state["topic"]
    subtopic = state["selected_subtopic"]
    user_level = state["user_level"]

    # 심화 주제 설명
    response = llm.invoke(advanced_topic_prompt.format(
        topic=topic,
        subtopic=subtopic,
        level=user_level
    ))
    response_text = response.content if hasattr(response, 'content') else str(response)

    return cast(NetworkGraphState, {**state, "explanation": response_text, "mode": "advanced_topic"})

# 면접 질문 생성 함수
def generate_interview_questions(state: NetworkGraphState) -> NetworkGraphState:
    topic = state["topic"]
    subtopic = state["selected_subtopic"] if state["selected_subtopic"] else topic
    user_level = state["user_level"]

    # 면접 질문 생성
    response = llm.invoke(interview_questions_prompt.format(
        topic=topic,
        subtopic=subtopic,
        level=user_level
    ))
    response_text = response.content if hasattr(response, 'content') else str(response)

    try:
        questions = json.loads(str(response_text))
    except Exception as e:
        # 파싱 오류시 기본 질문
        questions = [
            {"basic": f"{topic}의 주요 개념은 무엇인가요?", "followup": ["왜 중요한가요?"], "answer": "기본 개념 설명"},
            {"advanced": f"{topic}을 실무에 어떻게 적용할 수 있나요?", "answer": "실무 적용 방법"}
        ]

    return cast(NetworkGraphState, {
        **state,
        "interview_questions": questions,
        "current_interview_index": 0,
        "mode": "interview"
    })

# 다음 면접 질문으로 이동
def next_interview_question(state: NetworkGraphState) -> NetworkGraphState:
    return cast(NetworkGraphState, {
        **state,
        "current_interview_index": state["current_interview_index"] + 1
    })

# 인터뷰 질문 가져오기
def get_interview_question(state: NetworkGraphState) -> NetworkGraphState:
    """
    현재 인덱스의 인터뷰 질문을 가져옵니다.
    """
    index = state["current_interview_index"]

    # 인덱스가 범위를 벗어난 경우 처리
    if index >= len(state["interview_questions"]):
        return state

    # 현재 질문 정보 추출
    current_question = state["interview_questions"][index]

    # 기본 질문이 'basic' 키에 있고, 심화 질문이 'advanced' 키에 있는 경우 처리
    if "basic" in current_question:
        question = current_question["basic"]
    elif "advanced" in current_question:
        question = current_question["advanced"]
    else:
        question = "질문을 가져올 수 없습니다."

    # 질문 형식 통일을 위해 state 업데이트
    updated_question = {
        "question": question,
        "answer": current_question.get("answer", "")
    }

    # 해당 인덱스의 질문 업데이트
    interview_questions = state["interview_questions"].copy()
    interview_questions[index] = {**current_question, **updated_question}

    return cast(NetworkGraphState, {
        **state,
        "interview_questions": interview_questions
    })

# 타입 힌팅 없이 조건부 라우팅 함수 정의 (LangGraph는 이 함수의 반환 타입을 자체적으로 처리함)
def decide_next_step(state):
    # 모드에 따라 다음 단계 결정
    if state["mode"] == "question":
        return "answer_question"

    if state["mode"] == "quiz":
        return "generate_quiz"

    if state["mode"] == "level_test":
        return "generate_level_test"

    if state["mode"] == "subtopic_selection":
        # 세부 주제가 없으면 추출
        if not state["subtopics"]:
            return "extract_subtopics"
        # 세부 주제가 선택되었으면 심화 학습
        if state["selected_subtopic"]:
            return "explain_advanced_topic"

    if state["mode"] == "advanced_topic":
        # 심화 학습 후 퀴즈로
        if state.get("explanation"):
            return "generate_quiz"

    if state["mode"] == "interview":
        return "generate_interview_questions"

    # 모든 태그를 설명했으면 수준 테스트로
    if state["current_index"] >= len(state["tags"]):
        return "generate_level_test"

    # 그 외에는 계속 설명
    return "explain_tag"

graph = StateGraph(state_schema=NetworkGraphState)
graph.add_node("extract_tags", extract_tags)
graph.add_node("explain_tag", explain_current_tag)
graph.add_node("next_tag", next_tag)
graph.add_node("answer_question", answer_user_question)
graph.add_node("generate_quiz", generate_quiz)
graph.add_node("generate_level_test", generate_level_test)
graph.add_node("evaluate_user_level", evaluate_user_level)
graph.add_node("extract_subtopics", extract_subtopics)
graph.add_node("explain_advanced_topic", explain_advanced_topic)
graph.add_node("generate_interview_questions", generate_interview_questions)
graph.add_node("next_interview_question", next_interview_question)

# 진입점 설정
graph.set_entry_point("extract_tags")

# 상태 전이 로직
graph.add_conditional_edges(
    "extract_tags",
    decide_next_step
)

graph.add_conditional_edges(
    "next_tag",
    decide_next_step
)

# 기존 엣지
graph.add_edge("explain_tag", "next_tag")
graph.add_edge("answer_question", "next_tag")

# 새로운 엣지
graph.add_edge("generate_level_test", "evaluate_user_level")
graph.add_edge("evaluate_user_level", "extract_subtopics")
graph.add_edge("extract_subtopics", "explain_advanced_topic")
graph.add_edge("explain_advanced_topic", "generate_quiz")
graph.add_edge("generate_quiz", "generate_interview_questions")
graph.add_edge("generate_interview_questions", "next_interview_question")
graph.add_edge("next_interview_question", END)

network_graph_fsm = graph.compile()

# 네트워크 FSM 실행 함수 (핵심 함수)
async def run_fsm(topic: str) -> NetworkGraphState:
    """
    주어진 주제에 대한 네트워크 학습 FSM을 실행하고 최종 상태를 반환합니다.
    """
    # 초기 상태 설정
    initial_state: NetworkGraphState = {
        "topic": topic,
        "tags": [],
        "current_index": 0,
        "explanation": "",
        "questions": [],
        "user_question": "",
        "mode": "explain",
        "level_test_questions": [],
        "level_test_responses": [],
        "user_level": "beginner",
        "subtopics": [],
        "selected_subtopic": "",
        "interview_questions": [],
        "current_interview_index": 0
    }

    # 순차적으로 FSM 단계 실행
    state = extract_tags(initial_state)

    # 기본 개념 설명 (첫 번째 태그만)
    if state["tags"]:
        state = explain_current_tag(state)

    # 태그 추출 및 기본 설명까지만 진행하고 반환
    return state