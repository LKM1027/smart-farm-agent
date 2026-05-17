from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from app.core.config import settings
from app.agent.tools.smartfarm_api import get_smartfarm_sensor_data
import json

# LLM이 출력할 구조화된 데이터 모델 (의도 분석용)
class IntentAnalysis(BaseModel):
    is_sensor_needed: bool = Field(description="질문이 온실, 농장의 현재 상태(온도, 습도, CO2 등 환경 요인) 조회를 필요로 하는지 여부")
    is_vision_needed: bool = Field(description="질문이 작물 사진 분석이나 병해 진단, 증상 파악 등을 필요로 하는지 여부 ('사진', '병해', '진단', '증상' 등)")
    reason: str = Field(description="이러한 판단을 내린 이유 (간단히 작성)")

# LLM이 출력할 구조화된 데이터 모델 (최종 답변 및 제어 명령용)
class ControlCommand(BaseModel):
    target: str = Field(description="제어할 장치 이름 (예: 환기팬, 제습기, 창문 등)")
    action: str = Field(description="수행할 동작 (예: ON, OFF, OPEN, CLOSE 등)")
    value: Optional[str] = Field(None, description="설정할 값 (예: 50%, 25도 등)")
    reason: str = Field(description="이 제어 동작을 수행하는 이유 (예: 습도 저하를 통한 병해 확산 방지)")

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

def analyze_query(state: dict) -> dict:
    """
    사용자의 질문을 LLM으로 분석하여 의도를 파악하고,
    센서 데이터 조회가 필요한지 여부(is_sensor_needed)를 결정하는 노드입니다.
    """
    query = state.get("query", "")
    print(f"[Node: analyze_query] 질문 분석 시작: {query}")
    
    try:
        # Gemini LLM으로 교체
        llm = _get_gemini_llm(temperature=0)
        structured_llm = llm.with_structured_output(IntentAnalysis)
        
        prompt = PromptTemplate.from_template(
            "너는 스마트팜 자율 에이전트의 의도 파악기야. 사용자의 질문을 분석해서 "
            "온실 환경의 센서 데이터(예: 온도, 습도, CO2, 광량 등) 조회가 필수적인지(is_sensor_needed), "
            "그리고 작물의 사진 분석이나 병해 진단, 증상 확인이 필수적인지(is_vision_needed) 판단해줘.\n"
            "특히 '사진', '병해', '진단', '증상' 등의 키워드가 포함되어 있으면 is_vision_needed를 True로 설정해.\n\n"
            "사용자 질문: {query}"
        )
        
        chain = prompt | structured_llm
        result: IntentAnalysis = chain.invoke({"query": query})
        
        is_sensor_needed = result.is_sensor_needed
        is_vision_needed = result.is_vision_needed
        reason = result.reason
    except Exception as e:
        print(f"[Node: analyze_query] Gemini LLM 호출 실패 (API 키 확인 필요). 에러: {e}")
        
        fallback_keywords = ["온도", "습도", "상태", "환경", "얼마나", "어때", "co2", "알려줘"]
        is_sensor_needed = any(kw in query.replace(" ", "") for kw in fallback_keywords)
        vision_keywords = ["사진", "병해", "진단", "증상"]
        is_vision_needed = any(kw in query for kw in vision_keywords)
        reason = "LLM 통신 실패로 인한 키워드 룰 기반 강제 맵핑"

    print(f"[Node: analyze_query] 분석 결과 - 센서 필요: {is_sensor_needed}, 비전 필요: {is_vision_needed} (이유: {reason})")
    
    return {
        "is_sensor_needed": is_sensor_needed,
        "is_vision_needed": is_vision_needed
    }

async def fetch_sensor_data_node(state: dict) -> dict:
    """
    스마트팜 API 서비스를 호출하여 센서 데이터를 가져오고 상태를 업데이트하는 노드입니다.
    이 노드는 is_sensor_needed 가 True 일 때만 실행됩니다.
    """
    print("[Node: fetch_sensor_data_node] 센서 데이터 조회 노드 실행")
    
    from app.services.sensor_service import SensorService
    from app.core.config import settings
    
    # 상태값에 전달된 시설 ID가 없으면 환경변수의 기본값을 사용합니다.
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

def diagnose_crop(state: dict) -> dict:
    """
    YOLO 서비스를 호출하여 이미지에서 병해를 진단하고 상태를 업데이트하는 노드입니다.
    이 노드는 is_vision_needed 가 True 일 때만 실행됩니다.
    """
    print("[Node: diagnose_crop] 비전 진단 노드 실행")
    
    # 지연 로딩 방식을 사용하여 순환 참조나 불필요한 로딩을 피합니다.
    from app.services.yolo_service import YoloService
    yolo_service = YoloService()
    
    try:
        # 실제 환경에서는 상태에 있는 이미지 경로 등을 받아와서 넘겨야 합니다.
        result = yolo_service.diagnose(image_path=None)
        disease = result.get("disease", "Unknown")
        confidence = result.get("confidence", 0.0)
        diagnosis_str = f"진단 결과: {disease} (확률: {confidence*100:.1f}%)"
    except Exception as e:
        print(f"[Node: diagnose_crop] 비전 진단 중 에러 발생: {e}")
        diagnosis_str = "진단 실패"
        
    print(f"[Node: diagnose_crop] {diagnosis_str}")
    
    return {
        "diagnosis": diagnosis_str
    }

def retrieve_knowledge(state: dict) -> dict:
    """
    RAG 서비스를 호출하여 전문 지식을 검색하는 노드입니다.
    질문 내용이나 진단 결과를 기반으로 관련 농업 지침을 가져옵니다.
    """
    print("[Node: retrieve_knowledge] RAG 지식 검색 노드 실행")
    query = state.get("query", "")
    diagnosis = state.get("diagnosis", "")
    
    # RAG 서비스 호출
    from app.services.rag_service import RagService
    rag_service = RagService()
    
    # 질문 내용과 진단 결과를 합쳐서 검색 쿼리로 사용
    search_query = query
    if diagnosis and diagnosis != "진단 내용 없음":
        search_query += f" {diagnosis}"
        
    docs = rag_service.retrieve_docs(search_query)
    
    print(f"[Node: retrieve_knowledge] 검색된 문서 수: {len(docs)}")
    
    return {
        "retrieved_docs": docs
    }

def generate_answer(state: dict) -> dict:
    """
    수집된 모든 데이터(센서, 진단 결과 등)를 종합하여 
    최종적으로 사용자에게 반환할 답변과 제어 시퀀스를 생성하는 노드입니다.
    """
    print("[Node: generate_answer] 최종 답변 생성 시작")
    query = state.get("query", "")
    sensor_data = state.get("sensor_data", {})
    diagnosis = state.get("diagnosis", "진단 내용 없음")
    retrieved_docs = state.get("retrieved_docs", [])
    
    # 센서 데이터 포맷팅
    sensor_data_str = json.dumps(sensor_data, ensure_ascii=False) if sensor_data else "센서 데이터가 필요하지 않은 질문이거나 조회되지 않음"
    
    # 검색된 문서 포맷팅
    docs_str = "\n".join(retrieved_docs) if retrieved_docs else "검색된 관련 지침 없음"
    
    prompt_template = """너는 답변만 하는 게 아니라, 실제 온실의 장비를 제어하는 관리자야.
친절한 스마트팜 전문가로서 다음 데이터를 바탕으로 사용자의 질문에 답해줘.
센서 데이터가 있다면 그 수치가 적절한지도 판단해줘. (참고: 토마토 생육 적정 온도는 20~25도, 습도는 60~80%, CO2는 400~800ppm 수준임)

[중요 지시사항]
진단 결과가 '잎곰팡이병'이나 'Tomato_Leaf_Mold' 처럼 습도와 관련된 병해일 경우, 또는 센서 데이터상 환경 개선이 필요한 경우,
반드시 `control_sequence` 리스트에 환기팬 가동, 제습기 가동 같은 구체적인 장비 제어 명령을 포함해줘.
센서 데이터가 없거나 진단 결과가 없는 일반 질문일 경우, 또는 제어가 필요 없는 경우 `control_sequence`는 빈 리스트 []로 반환해야 해.
만약 [검색된 농업 지침]이 존재할 경우, 이를 '농업기술길잡이(토마토)의 공인 지침'으로 간주하고 답변의 핵심 근거로 사용해야 해.
답변 시작 시 혹은 근거 제시 시 "농업기술길잡이(토마토) 지침에 따르면..."이라는 문구를 반드시 포함하여 신뢰도를 높여줘.

[사용자 질문]
{query}

[수집된 센서 데이터]
{sensor_data_str}

[비전 진단 결과]
{diagnosis}

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
            "diagnosis": diagnosis,
            "docs_str": docs_str
        })
        
        answer = response.answer
        # Pydantic 모델의 딕셔너리 변환 (버전 호환성을 위해 dict() 사용)
        control_sequence = [cmd.dict() for cmd in response.control_sequence]
        
    except Exception as e:
        print(f"[Node: generate_answer] 답변 생성 실패: {e}")
        answer = (
            "죄송합니다. 현재 AI 서버(Gemini) 모델과의 통신이 원활하지 않아 답변을 생성하지 못했습니다.\n\n"
            f"[디버그용 수집 데이터]\n- 센서: {sensor_data_str}\n- 진단: {diagnosis}"
        )
        control_sequence = []
        
    print(f"[Node: generate_answer] 생성된 답변 길이: {len(answer)}자, 제어 명령 수: {len(control_sequence)}")
    
    return {
        "answer": answer,
        "control_sequence": control_sequence
    }

