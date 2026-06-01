from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from app.core.config import settings
from app.agent.tools.smartfarm_api import get_smartfarm_sensor_data
import json

# ─────────────────────────────────────────────
# 지원 작물 가드레일 설정
# ─────────────────────────────────────────────
SUPPORTED_CROPS = ["토마토", "tomato"]
UNSUPPORTED_CROP_KEYWORDS = [
    "파인애플", "딸기", "수박", "오이", "고추", "상추", "배추", "사과",
    "포도", "복숭아", "망고", "바나나", "레몬", "블루베리", "체리",
    "pineapple", "strawberry", "watermelon", "cucumber", "pepper",
    "lettuce", "cabbage", "apple", "grape", "mango", "banana",
]
UNSUPPORTED_CROP_RESPONSE = (
    "본 시스템은 KS 표준 기반 토마토 전용 스마트팜 자율 관제 에이전트입니다. "
    "파인애플 등 타 작물의 생육 가이드는 지원하지 않습니다."
)

# ─────────────────────────────────────────────
# LLM 구조화 출력 모델 (의도 분석용)
# ─────────────────────────────────────────────
class IntentAnalysis(BaseModel):
    is_sensor_needed: bool = Field(
        description="질문이 온실·농장의 현재 상태(온도, 습도, CO2 등 환경 요인) 조회를 필요로 하는지 여부"
    )
    reason: str = Field(description="판단 이유 (간단히 작성)")

# ─────────────────────────────────────────────
# LLM 구조화 출력 모델 (최종 답변 및 제어 명령용)
# ─────────────────────────────────────────────
class ControlCommand(BaseModel):
    target: str = Field(description="제어할 장치 이름 (예: 환기팬, 제습기, 창문 등)")
    action: str = Field(description="수행할 동작 (예: ON, OFF, OPEN, CLOSE 등)")
    value: Optional[str] = Field(None, description="설정할 값 (예: 50%, 25도 등)")
    reason: str = Field(description="이 제어 동작을 수행하는 이유")

class AgentResponse(BaseModel):
    answer: str = Field(description="에이전트의 상황 판단 및 최종 답변 텍스트")
    control_sequence: List[ControlCommand] = Field(
        default_factory=list,
        description="상황에 따라 필요한 제어 명령 리스트. 제어가 필요 없거나 일반 질문인 경우 빈 리스트 []를 반환합니다."
    )


def _get_gemini_llm(temperature: float = 0):
    """Gemini LLM 인스턴스를 생성하는 헬퍼 함수"""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=temperature,
        google_api_key=settings.GEMINI_API_KEY
    )


# ─────────────────────────────────────────────
# 노드 1: 미지원 작물 가드레일
# ─────────────────────────────────────────────
def check_supported_crop(state: dict) -> dict:
    """
    사용자 질문에 미지원 작물 키워드가 포함되어 있는지 검사하는 가드레일 노드.
    미지원 작물이 감지되면 is_unsupported_crop=True 와 고정 방어 답변을 상태에 기록합니다.
    """
    query = state.get("query", "")
    query_lower = query.lower()

    detected = [kw for kw in UNSUPPORTED_CROP_KEYWORDS if kw.lower() in query_lower]

    if detected:
        print(f"[Node: check_supported_crop] ⛔ 미지원 작물 감지: {detected} → 가드레일 발동")
        return {
            "is_unsupported_crop": True,
            "answer": UNSUPPORTED_CROP_RESPONSE,
            "control_sequence": [],
        }

    print("[Node: check_supported_crop] ✅ 지원 작물 범위 내 질문 확인 → 계속 진행")
    return {"is_unsupported_crop": False}


# ─────────────────────────────────────────────
# 노드 2: 의도 분석 (텍스트·센서 오케스트레이션)
# ─────────────────────────────────────────────
def analyze_query(state: dict) -> dict:
    """
    사용자 질문을 LLM으로 분석하여 센서 데이터 조회 필요 여부를 결정하는 노드.
    텍스트 질의와 하드웨어 관제 오케스트레이션에 집중합니다.
    """
    query = state.get("query", "")
    print(f"[Node: analyze_query] 질문 분석 시작: {query}")

    try:
        llm = _get_gemini_llm(temperature=0)
        structured_llm = llm.with_structured_output(IntentAnalysis)

        prompt = PromptTemplate.from_template(
            "너는 스마트팜 자율 에이전트의 의도 파악기야. 사용자의 질문을 분석해서 "
            "온실 환경의 센서 데이터(온도, 습도, CO2, 광량 등) 조회가 필수적인지(is_sensor_needed) 판단해줘.\n\n"
            "사용자 질문: {query}"
        )

        chain = prompt | structured_llm
        result: IntentAnalysis = chain.invoke({"query": query})

        is_sensor_needed = result.is_sensor_needed
        reason = result.reason
    except Exception as e:
        print(f"[Node: analyze_query] Gemini LLM 호출 실패 (API 키 확인 필요). 에러: {e}")

        fallback_keywords = ["온도", "습도", "상태", "환경", "얼마나", "어때", "co2", "알려줘"]
        is_sensor_needed = any(kw in query.replace(" ", "") for kw in fallback_keywords)
        reason = "LLM 통신 실패로 인한 키워드 룰 기반 강제 맵핑"

    print(f"[Node: analyze_query] 분석 결과 - 센서 필요: {is_sensor_needed} (이유: {reason})")

    return {
        "is_sensor_needed": is_sensor_needed,
    }


# ─────────────────────────────────────────────
# 노드 3: 센서 데이터 조회
# ─────────────────────────────────────────────
async def fetch_sensor_data_node(state: dict) -> dict:
    """
    스마트팜 API 서비스를 호출하여 센서 데이터를 가져오고 상태를 업데이트하는 노드.
    is_sensor_needed 가 True 일 때만 실행됩니다.
    """
    print("[Node: fetch_sensor_data_node] 센서 데이터 조회 노드 실행")

    from app.services.sensor_service import SensorService
    from app.core.config import settings

    facility_id = state.get("facility_id", settings.SMARTFARM_FACILITY_ID)

    try:
        service = SensorService()
        sensor_result = await service.fetch_data(facility_id=facility_id)
    except Exception as e:
        print(f"[Node: fetch_sensor_data_node] API 서비스 호출 중 에러 발생: {e}")
        sensor_result = {}

    print(f"[Node: fetch_sensor_data_node] 조회 결과: {sensor_result}")

    return {
        "sensor_data": sensor_result
    }


# ─────────────────────────────────────────────
# 노드 4: RAG 지식 검색
# ─────────────────────────────────────────────
def retrieve_knowledge(state: dict) -> dict:
    """
    RAG 서비스를 호출하여 전문 지식을 검색하는 노드.
    질문 내용을 기반으로 관련 농업 지침을 가져옵니다.
    """
    print("[Node: retrieve_knowledge] RAG 지식 검색 노드 실행")
    query = state.get("query", "")

    from app.services.rag_service import RagService
    rag_service = RagService()

    docs = rag_service.retrieve_docs(query)

    print(f"[Node: retrieve_knowledge] 검색된 문서 수: {len(docs)}")

    return {
        "retrieved_docs": docs
    }


# ─────────────────────────────────────────────
# 노드 5: 최종 답변 생성
# ─────────────────────────────────────────────
def generate_answer(state: dict) -> dict:
    """
    수집된 모든 데이터(센서, RAG 지식)를 종합하여
    최종적으로 사용자에게 반환할 답변과 제어 시퀀스를 생성하는 노드.
    """
    print("[Node: generate_answer] 최종 답변 생성 시작")
    query = state.get("query", "")
    sensor_data = state.get("sensor_data", {})
    retrieved_docs = state.get("retrieved_docs", [])

    # 센서 데이터 포맷팅
    sensor_data_str = (
        json.dumps(sensor_data, ensure_ascii=False)
        if sensor_data
        else "센서 데이터가 필요하지 않은 질문이거나 조회되지 않음"
    )

    # 검색된 문서 포맷팅
    docs_str = "\n".join(retrieved_docs) if retrieved_docs else "검색된 관련 지침 없음"

    prompt_template = """너는 답변만 하는 게 아니라, 실제 온실의 장비를 제어하는 관리자야.
친절한 스마트팜 전문가로서 다음 데이터를 바탕으로 사용자의 질문에 답해줘.
센서 데이터가 있다면 그 수치가 적절한지도 판단해줘. (참고: 토마토 생육 적정 온도는 20~25도, 습도는 60~80%, CO2는 400~800ppm 수준임)

[중요 지시사항]
환경 개선이 필요한 경우 반드시 `control_sequence` 리스트에 환기팬 가동, 제습기 가동 같은 구체적인 장비 제어 명령을 포함해줘.
센서 데이터가 없거나 제어가 필요 없는 일반 질문일 경우 `control_sequence`는 빈 리스트 []로 반환해야 해.
만약 [검색된 농업 지침]이 존재할 경우, 이를 '농업기술길잡이(토마토)의 공인 지침'으로 간주하고 답변의 핵심 근거로 사용해야 해.
답변 시작 시 혹은 근거 제시 시 "농업기술길잡이(토마토) 지침에 따르면..."이라는 문구를 반드시 포함하여 신뢰도를 높여줘.

[사용자 질문]
{query}

[수집된 센서 데이터]
{sensor_data_str}

[검색된 농업 지침]
{docs_str}
"""

    try:
        llm = _get_gemini_llm(temperature=0.7)
        structured_llm = llm.with_structured_output(AgentResponse)

        prompt = PromptTemplate.from_template(prompt_template)
        chain = prompt | structured_llm

        response: AgentResponse = chain.invoke({
            "query": query,
            "sensor_data_str": sensor_data_str,
            "docs_str": docs_str
        })

        answer = response.answer
        control_sequence = [cmd.dict() for cmd in response.control_sequence]

    except Exception as e:
        print(f"[Node: generate_answer] 답변 생성 실패: {e}")
        answer = (
            "죄송합니다. 현재 AI 서버(Gemini) 모델과의 통신이 원활하지 않아 답변을 생성하지 못했습니다.\n\n"
            f"[디버그용 수집 데이터]\n- 센서: {sensor_data_str}"
        )
        control_sequence = []

    print(f"[Node: generate_answer] 생성된 답변 길이: {len(answer)}자, 제어 명령 수: {len(control_sequence)}")

    return {
        "answer": answer,
        "control_sequence": control_sequence,
    }
