import os
import openai
from openai import AsyncOpenAI
import asyncio
from typing import Optional, Dict, Any, List, Union, Callable, Awaitable

# OpenAI 클라이언트 설정
openai.api_key = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 재시도 설정
MAX_RETRIES = 3
RETRY_DELAY = 2  # 초 단위

# 모델 설정
DEFAULT_MODEL = "gpt-4o-mini"
TIMEOUT = 60  # 초 단위

async def get_completion(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    timeout: int = TIMEOUT
) -> str:
    """
    OpenAI API에 비동기로 요청하여 텍스트 완성을 가져옵니다.
    오류나 타임아웃 시 자동 재시도 기능을 포함합니다.

    Args:
        prompt: 입력 프롬프트
        model: 사용할 모델 이름
        temperature: 생성 다양성 (0~1)
        max_tokens: 최대 생성 토큰 수
        timeout: 요청 타임아웃(초)

    Returns:
        생성된 텍스트
    """
    for attempt in range(MAX_RETRIES):
        try:
            # 비동기 타임아웃 설정
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                ),
                timeout=timeout
            )

            content = response.choices[0].message.content
            return content if content is not None else "응답 내용이 없습니다."

        except asyncio.TimeoutError:
            if attempt < MAX_RETRIES - 1:
                # 지수 백오프로 재시도
                delay = RETRY_DELAY * (2 ** attempt)
                print(f"요청 타임아웃, {delay}초 후 재시도합니다... (시도 {attempt+1}/{MAX_RETRIES})")
                await asyncio.sleep(delay)
            else:
                return "죄송합니다. 응답 시간이 너무 오래 걸려 처리하지 못했습니다. 다시 시도해주세요."

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (2 ** attempt)
                print(f"오류 발생: {str(e)}, {delay}초 후 재시도합니다... (시도 {attempt+1}/{MAX_RETRIES})")
                await asyncio.sleep(delay)
            else:
                return f"죄송합니다. 오류가 발생했습니다: {str(e)}"

    # 모든 시도가 실패했을 경우의 기본 반환값
    return "응답을 받아오지 못했습니다. 잠시 후 다시 시도해주세요."

async def get_structured_completion(
    prompt: str,
    functions: List[Dict[str, Any]],
    model: str = "gpt-4-turbo",
    temperature: float = 0.2,
    timeout: int = TIMEOUT
) -> Dict[str, Any]:
    """
    함수 호출 형식으로 구조화된 응답을 받아옵니다.

    Args:
        prompt: 입력 프롬프트
        functions: 함수 스키마 목록
        model: 사용할 모델 이름
        temperature: 생성 다양성 (0~1)
        timeout: 요청 타임아웃(초)

    Returns:
        구조화된 응답 데이터
    """
    for attempt in range(MAX_RETRIES):
        try:
            # 함수 형식 변환 - OpenAI SDK와 호환되는 형식으로 변환
            from openai.types.chat import ChatCompletionToolParam
            converted_functions = []
            for func in functions:
                converted_functions.append({
                    "type": "function",
                    "function": func
                })

            # 비동기 타임아웃 설정
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    tools=converted_functions
                ),
                timeout=timeout
            )

            message = response.choices[0].message

            # 함수 호출 응답 확인
            if message.tool_calls and len(message.tool_calls) > 0:
                tool_call = message.tool_calls[0]
                function_name = tool_call.function.name
                function_args = tool_call.function.arguments

                # JSON 문자열을 파싱
                import json
                try:
                    parsed_args = json.loads(function_args)
                    return {
                        "function": function_name,
                        "args": parsed_args
                    }
                except json.JSONDecodeError:
                    return {
                        "function": function_name,
                        "args": function_args
                    }

            # 일반 텍스트 응답
            return {"text": message.content if message.content else "응답 내용이 없습니다."}

        except asyncio.TimeoutError:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (2 ** attempt)
                print(f"요청 타임아웃, {delay}초 후 재시도합니다... (시도 {attempt+1}/{MAX_RETRIES})")
                await asyncio.sleep(delay)
            else:
                return {"error": "타임아웃 오류"}

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (2 ** attempt)
                print(f"오류 발생: {str(e)}, {delay}초 후 재시도합니다... (시도 {attempt+1}/{MAX_RETRIES})")
                await asyncio.sleep(delay)
            else:
                return {"error": f"API 오류: {str(e)}"}

    # 모든 시도가 실패했을 경우의 기본 반환값
    return {"error": "응답을 받아오지 못했습니다."}

async def generate_with_stream(
    prompt: str,
    callback: Callable[[str], Awaitable[None]],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 2048
) -> None:
    """
    스트리밍 방식으로 텍스트를 생성하고 콜백 함수로 청크를 전달합니다.

    Args:
        prompt: 입력 프롬프트
        callback: 각 청크를 처리할 콜백 함수
        model: 사용할 모델 이름
        temperature: 생성 다양성 (0~1)
        max_tokens: 최대 생성 토큰 수
    """
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )

        # 스트림에서 청크 처리
        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                content = chunk.choices[0].delta.content
                if content:
                    await callback(content)

    except Exception as e:
        await callback(f"\n[오류 발생: {str(e)}]")