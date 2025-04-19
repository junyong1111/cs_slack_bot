from langchain_core.prompts import PromptTemplate

tag_extraction_prompt = PromptTemplate.from_template(
    """'{topic}'에 대해 컴퓨터공학적으로 반드시 알아야 할 핵심 개념 키워드를 5~7개 정도 뽑아줘.
순수 키워드 리스트만 출력해줘. 설명은 포함하지 마."""
)

concept_explanation_prompt = PromptTemplate.from_template(
    """'{tag}'에 대해 컴퓨터공학 초보자도 이해할 수 있도록 설명해줘.

- 핵심 개념을 쉬운 언어로 설명
- 용어는 풀어서 설명
- 실제 예시 포함
- 너무 짧지 않게"""
)

user_question_prompt = PromptTemplate.from_template(
    """주제: {topic}
현재 설명 중인 개념: {tag}
사용자 질문: {question}

위 질문에 대해 자세하고 이해하기 쉽게 답변해주세요.
- 복잡한 용어는 풀어서 설명
- 실생활 예시가 있다면 포함
- 정확한 정보 제공"""
)

quiz_generation_prompt = PromptTemplate.from_template(
    """주제: {topic}
핵심 개념: {tags}

위 주제와 개념들에 대한 다양한 유형의 퀴즈 문제 3개를 만들어주세요.
- OX 문제 1개
- 객관식 문제 1개 (4개 보기 포함)
- 주관식 문제 1개

다음 JSON 형식으로 정확히 출력해주세요:
[
  {{"type": "OX", "question": "OX 문제 내용", "answer": "O 또는 X"}},
  {{"type": "객관식", "question": "객관식 문제 내용", "options": ["보기1", "보기2", "보기3", "보기4"], "answer": "정답 내용(보기 중 하나)"}},
  {{"type": "주관식", "question": "주관식 문제 내용", "answer": "정답 내용"}}
]

JSON 형식만 정확히 출력하고 다른 설명은 포함하지 마세요."""
)

# 사용자 수준 테스트를 위한 프롬프트 추가
level_test_prompt = PromptTemplate.from_template(
    """주제: {topic}
사용자 수준 평가를 위한 테스트 문제를 만들어주세요.
- OX 문제 2개: 기초 개념 확인용
- 객관식 문제 2개: 중요 개념 이해도 확인용 (4개 보기 포함)
- 주관식 문제 1개: 심화 개념 이해도 확인용

난이도는 다양하게 구성하여 사용자 수준을 정확히 파악할 수 있게 해주세요.
기본/중급/고급 개념이 골고루 포함되어야 합니다.

다음 JSON 형식으로 정확히 출력해주세요:
[
  {{"type": "OX", "question": "OX 문제 내용", "answer": "O 또는 X", "level": "기본/중급/고급", "topic": "관련 세부 토픽"}},
  {{"type": "OX", "question": "OX 문제 내용", "answer": "O 또는 X", "level": "기본/중급/고급", "topic": "관련 세부 토픽"}},
  {{"type": "객관식", "question": "객관식 문제 내용", "options": ["보기1", "보기2", "보기3", "보기4"], "answer": "정답 내용(보기 중 하나)", "level": "기본/중급/고급", "topic": "관련 세부 토픽"}},
  {{"type": "객관식", "question": "객관식 문제 내용", "options": ["보기1", "보기2", "보기3", "보기4"], "answer": "정답 내용(보기 중 하나)", "level": "기본/중급/고급", "topic": "관련 세부 토픽"}},
  {{"type": "주관식", "question": "주관식 문제 내용", "answer": "정답 내용", "level": "기본/중급/고급", "topic": "관련 세부 토픽"}}
]

JSON 형식만 정확히 출력하고 다른 설명은 포함하지 마세요."""
)

# 주제별 세부 개념 추출 프롬프트
subtopic_extraction_prompt = PromptTemplate.from_template(
    """주제: {topic}

이 주제에 대한 세부 학습 주제를 CS 우선순위에 맞게 5~7개 추출해주세요.
각 항목에는 제목과 짧은 설명이 포함되어야 합니다.

예시 (네트워크인 경우):
[
  {{"title": "OSI 7계층", "description": "네트워크 통신의 기본 구조와 각 계층별 역할 이해"}},
  {{"title": "TCP/IP", "description": "인터넷 통신의 핵심 프로토콜 구조와 작동 원리 학습"}},
  ...
]

다음 JSON 형식으로 정확히 출력해주세요:
[
  {{"title": "세부 주제 제목", "description": "간단한 설명"}},
  ...
]

JSON 형식만 정확히 출력하고 다른 설명은 포함하지 마세요."""
)

# 심화 학습 프롬프트
advanced_topic_prompt = PromptTemplate.from_template(
    """주제: {topic}
세부 주제: {subtopic}
사용자 레벨: {level}

위 주제에 대한 심화 학습 내용을 작성해주세요. 사용자의 현재 레벨({level})에 맞게 적절한 난이도로 설명해주세요.

다음 내용을 포함해주세요:
1. 개념 상세 설명
2. 실제 응용 사례
3. 관련 기술이나 최신 트렌드
4. 개발자/엔지니어 관점에서 중요한 포인트

설명은 명확하고 구조적으로 작성해주세요."""
)

# 면접 질문 생성 프롬프트
interview_questions_prompt = PromptTemplate.from_template(
    """주제: {topic}
세부 주제: {subtopic}
사용자 레벨: {level}

위 주제에 대한 개발자/엔지니어 면접 질문을 단계별로 생성해주세요:

1. 기본 면접 질문 (2-3개): 해당 주제의 핵심 개념 이해도를 확인하는 질문
2. 꼬리 질문 (각 기본 질문당 1-2개): 기본 질문에 이어 더 깊은 이해도를 확인하는 질문
3. 심화 면접 질문 (1-2개): 실무 적용력이나 문제 해결 능력을 확인하는 고난도 질문

다음 JSON 형식으로 정확히 출력해주세요:
[
  {{
    "basic": "기본 질문 내용",
    "followup": ["꼬리 질문1", "꼬리 질문2"],
    "answer": "모범 답변 요약"
  }},
  ... 기본 질문 2-3개 ...
  {{
    "advanced": "심화 질문 내용",
    "answer": "모범 답변 요약"
  }},
  ... 심화 질문 1-2개 ...
]

JSON 형식만 정확히 출력하고 다른 설명은 포함하지 마세요."""
)

# 사용자 응답 평가 프롬프트
answer_evaluation_prompt = PromptTemplate.from_template(
    """질문: {question}
정답 또는 모범 답안: {correct_answer}
사용자 응답: {user_answer}

위 사용자의 응답을 평가해주세요. 다음 기준으로 평가해주세요:
1. 정확성: 응답이 얼마나 정확한지
2. 완전성: 필요한 핵심 개념을 모두 포함했는지
3. 이해도: 개념을 얼마나 깊이 이해했는지

다음 JSON 형식으로 정확히 출력해주세요:
{{
  "score": 0~100 사이의 점수,
  "feedback": "구체적인 피드백 내용",
  "missing_points": ["놓친 중요 포인트1", "놓친 중요 포인트2", ...],
  "strengths": ["잘한 점1", "잘한 점2", ...]
}}

JSON 형식만 정확히 출력하고 다른 설명은 포함하지 마세요."""
)