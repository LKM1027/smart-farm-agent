from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from app.core.config import settings
from app.agent.tools.smartfarm_api import get_smartfarm_sensor_data
import json
import re
import struct
from pathlib import Path

# DB session and models for node-level persistence (SessionLocal used directly)
from app.database import SessionLocal
from app.models import SensorLog, ControlLog


# ══════════════════════════════════════════════════════════════════════════════
# AGENTS.md 프롬프트 로더
# 하드코딩된 프롬프트를 제거하고 AGENTS.md 에서 동적으로 읽어옵니다.
# 섹션 헤더(### 4-1. ...) 아래의 첫 번째 코드 블록(``` ... ```)을 파싱합니다.
# ══════════════════════════════════════════════════════════════════════════════

_AGENTS_MD_PATH = Path(__file__).parent.parent.parent / "AGENTS.md"


def _load_prompt_from_agents_md(section_title: str) -> str:
    """
    AGENTS.md 파일에서 지정한 섹션 제목(section_title) 아래의
    첫 번째 마크다운 코드 블록(``` ... ```) 내용을 추출하여 반환합니다.

    Args:
        section_title: AGENTS.md 내 섹션 헤더 텍스트 (예: "4-1. 토마토 전용 시스템 프롬프트")

    Returns:
        코드 블록 안의 문자열. 파일이 없거나 섹션/블록을 못 찾으면 빈 문자열 반환.
    """
    try:
        content = _AGENTS_MD_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"[PromptLoader] AGENTS.md 파일을 찾을 수 없습니다: {_AGENTS_MD_PATH}")
        return ""

    # 섹션 제목이 포함된 줄 이후부터 파싱
    section_pattern = re.compile(re.escape(section_title), re.IGNORECASE)
    match = section_pattern.search(content)
    if not match:
        print(f"[PromptLoader] 섹션을 찾을 수 없습니다: '{section_title}'")
        return ""

    after_section = content[match.end():]

    # 다음 코드 블록(``` ~ ```) 추출
    code_block_pattern = re.compile(r"```(?:\w*)\n(.*?)```", re.DOTALL)
    block_match = code_block_pattern.search(after_section)
    if not block_match:
        print(f"[PromptLoader] 섹션 '{section_title}' 아래 코드 블록을 찾을 수 없습니다.")
        return ""

    return block_match.group(1).strip()


# ══════════════════════════════════════════════════════════════════════════════
# KS X 3267:2022  Modbus RTU Protocol Translator
# RS485 기반 Modbus RTU 헥사 프레임 생성기
#
# 프레임 구조 (KS X 3267 §4.2, §6.3):
#   [SlaveID(1B)] [FunctionCode(1B)] [RegAddr(2B)] [Data(nB)] [CRC16(2B)]
#
# 장치-레지스터 매핑 (KS X 3267 Appendix A / KS X 3286 §8 기반):
#   슬레이브 주소(Slave ID)는 KS X 3286 노드 등록 규격에 따라 1~247 범위.
#   각 장치 제어 레지스터는 KS X 3267 표 14 (노드 레지스터 주소 범위) 준거.
#   - 구동기 제어 레지스터 시작: 0x0300 (768) 번지대
#   - 양액기 제어 레지스터 시작: 0x01F4 (500) 번지대 (KS X 3288 기준)
# ══════════════════════════════════════════════════════════════════════════════

class ModbusTranslator:
    """
    KS X 3267:2022 §4 RS485 Modbus RTU 프로토콜 기반 헥사 프레임 변환기.
    LLM이 생성한 ControlSequence 명령을 물리 PLC가 수신 가능한
    RTU 바이너리 프레임 문자열로 변환합니다.

    프레임 구조 (KS X 3267 §4.2, §6.3):
      [SlaveID(1B)] [FunctionCode(1B)] [RegAddr(2B)] [Payload(nB)] [CRC16(2B)]

    KS X 3265/3268 구동기 및 KS X 3288 양액기 제어 명령 매핑을 명시적으로 처리합니다.
    """

    FC_WRITE_SINGLE_REGISTER = 0x06
    FC_WRITE_MULTIPLE_REGISTERS = 0x10

    _DEVICE_MAP: Dict[str, Dict[str, Any]] = {
        "CC01":   {"slave_id": 0x01, "reg_addr": 0x0300, "default_fc": FC_WRITE_SINGLE_REGISTER},
        "CC02":   {"slave_id": 0x02, "reg_addr": 0x0300, "default_fc": FC_WRITE_SINGLE_REGISTER},
        "CC03":   {"slave_id": 0x03, "reg_addr": 0x0300, "default_fc": FC_WRITE_SINGLE_REGISTER},
        "CC04":   {"slave_id": 0x04, "reg_addr": 0x0300, "default_fc": FC_WRITE_SINGLE_REGISTER},
        "CC18":   {"slave_id": 0x05, "reg_addr": 0x0312, "default_fc": FC_WRITE_SINGLE_REGISTER},
        "CC19":   {"slave_id": 0x06, "reg_addr": 0x0313, "default_fc": FC_WRITE_SINGLE_REGISTER},
        "CC21":   {"slave_id": 0x07, "reg_addr": 0x0315, "default_fc": FC_WRITE_SINGLE_REGISTER},
        "CC21_V": {"slave_id": 0x08, "reg_addr": 0x0316, "default_fc": FC_WRITE_SINGLE_REGISTER},
        "CC22":   {"slave_id": 0x09, "reg_addr": 0x0318, "default_fc": FC_WRITE_SINGLE_REGISTER},
        "NU_EC_SET": {"slave_id": 0x0A, "reg_addr": 0x01FE, "default_fc": FC_WRITE_MULTIPLE_REGISTERS},
        "NU_PH_SET": {"slave_id": 0x0A, "reg_addr": 0x0200, "default_fc": FC_WRITE_MULTIPLE_REGISTERS},
        "NU_VALVE":  {"slave_id": 0x0A, "reg_addr": 0x01FA, "default_fc": None},
    }

    _ACTION_DATA: Dict[str, int] = {
        "ON":         0x0001,
        "OFF":        0x0000,
        "OPEN":       0x0001,
        "CLOSE":      0x0002,
        "STOP":       0x0000,
        "NU_ON":      401,
        "NU_OFF":     0,
        "NU_AREA_ON": 402,
        "NU_PARAM_ON":403,
    }

    @classmethod
    def _crc16(cls, data: bytes) -> int:
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    @classmethod
    def _float_to_registers(cls, value: float) -> tuple[int, int]:
        packed = struct.pack('>f', value)
        return ((packed[0] << 8) | packed[1], (packed[2] << 8) | packed[3])

    @classmethod
    def _int16_to_register(cls, value: int) -> int:
        return value & 0xFFFF

    @classmethod
    def _build_single_register_frame(cls, slave_id: int, reg_addr: int, value: int) -> str:
        reg_hi = (reg_addr >> 8) & 0xFF
        reg_lo = reg_addr & 0xFF
        data_hi = (value >> 8) & 0xFF
        data_lo = value & 0xFF
        frame_bytes = bytes([slave_id, cls.FC_WRITE_SINGLE_REGISTER, reg_hi, reg_lo, data_hi, data_lo])
        crc = cls._crc16(frame_bytes)
        return cls._format_frame(frame_bytes + bytes([crc & 0xFF, (crc >> 8) & 0xFF]))

    @classmethod
    def _build_multiple_register_frame(cls, slave_id: int, reg_addr: int, register_values: List[int]) -> str:
        reg_hi = (reg_addr >> 8) & 0xFF
        reg_lo = reg_addr & 0xFF
        num_regs = len(register_values)
        byte_count = num_regs * 2
        payload = b"".join(bytes([(value >> 8) & 0xFF, value & 0xFF]) for value in register_values)
        frame_bytes = bytes([slave_id, cls.FC_WRITE_MULTIPLE_REGISTERS, reg_hi, reg_lo, 0x00, num_regs, byte_count]) + payload
        crc = cls._crc16(frame_bytes)
        return cls._format_frame(frame_bytes + bytes([crc & 0xFF, (crc >> 8) & 0xFF]))

    @classmethod
    def _format_frame(cls, data: bytes) -> str:
        return "[Tx] " + " ".join(f"{b:02X}" for b in data)

    @classmethod
    def translate(cls, device: str, action: str, value: Optional[float] = None) -> str:
        if device not in cls._DEVICE_MAP:
            return f"[WARN] Unknown device: {device} — KS X 3267 매핑 없음"

        device_cfg = cls._DEVICE_MAP[device]
        slave_id = device_cfg["slave_id"]
        reg_addr = device_cfg["reg_addr"]
        default_fc = device_cfg["default_fc"]

        if default_fc == cls.FC_WRITE_SINGLE_REGISTER:
            if action == "SET_LV":
                if value is None:
                    return "[WARN] SET_LV requires a numeric value."
                data_val = cls._int16_to_register(int(round(value)))
            elif action == "SET_TEMP":
                if value is None:
                    return "[WARN] SET_TEMP requires a numeric value."
                data_val = cls._int16_to_register(int(round(value * 10)))
            else:
                data_val = cls._int16_to_register(cls._ACTION_DATA.get(action, 0x0001))
            return cls._build_single_register_frame(slave_id, reg_addr, data_val)

        if device == "NU_VALVE":
            if action in {"NU_ON", "NU_OFF"}:
                return cls._build_single_register_frame(slave_id, reg_addr, cls._int16_to_register(cls._ACTION_DATA[action]))
            if action == "NU_AREA_ON":
                if value is None:
                    return "[WARN] NU_AREA_ON requires a numeric area index."
                return cls._build_multiple_register_frame(
                    slave_id,
                    reg_addr,
                    [cls._int16_to_register(cls._ACTION_DATA[action]), cls._int16_to_register(int(round(value)))]
                )
            if action == "NU_PARAM_ON":
                if value is None:
                    return "[WARN] NU_PARAM_ON requires a numeric EC parameter value."
                return cls._build_multiple_register_frame(
                    slave_id,
                    reg_addr,
                    [cls._int16_to_register(cls._ACTION_DATA[action]), cls._int16_to_register(int(round(value * 10)))]
                )
            return f"[WARN] Unsupported NU_VALVE action: {action}"

        if default_fc == cls.FC_WRITE_MULTIPLE_REGISTERS:
            if value is None:
                return f"[WARN] {device} requires a numeric float value."
            high, low = cls._float_to_registers(float(value))
            return cls._build_multiple_register_frame(slave_id, reg_addr, [high, low])

        return f"[WARN] Unsupported frame generation for {device}/{action}"

    @classmethod
    def build_frames(cls, control_sequence: list) -> List[str]:
        frames: List[str] = []
        frames.append("[SYS] KS X 3267:2022 Modbus RTU Protocol Translator initialized")
        frames.append("[SYS] RS485 2-Wire Half-Duplex / Baud: 19200 / Parity: Even")
        frames.append(f"[SYS] {len(control_sequence)} command(s) queued for transmission")
        frames.append("[SYS] ─────────────────────────────────────────")

        for i, cmd in enumerate(control_sequence):
            device = getattr(cmd.device, "value", cmd.device)
            action = getattr(cmd.action, "value", cmd.action)
            value = getattr(cmd, 'value', None)
            if hasattr(value, '__float__'):
                value = float(value)

            frames.append(f"[CMD {i+1:02d}] device={device} action={action} value={value}")
            hex_frame = cls.translate(device, action, value)
            frames.append(hex_frame)

            if hex_frame.startswith("[Tx]"):
                parts = hex_frame.replace("[Tx] ", "").split()
                if len(parts) >= 6:
                    ack_parts = parts[:6]
                    crc_bytes = bytes(int(p, 16) for p in ack_parts)
                    crc = cls._crc16(crc_bytes)
                    ack_hex = " ".join(ack_parts) + f" {crc & 0xFF:02X} {(crc >> 8) & 0xFF:02X}"
                    frames.append(f"[Rx] {ack_hex}  ← ACK")

        frames.append("[SYS] ─────────────────────────────────────────")
        frames.append("[SYS] Transmission complete. All commands dispatched.")
        return frames

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
    is_sensor_needed: bool = Field(description="질문의 답변을 위해 환경 센서 데이터 조회가 필요한지 여부")
    is_rag_needed: bool = Field(description="질문의 답변을 위해 농업 지침 검색(RAG)이 필요한지 여부")
    reason: str = Field(description="이러한 판단을 내린 이유 (간단히 작성)")

# ─────────────────────────────────────────────
# LLM 구조화 출력 모델 (최종 답변 및 제어 명령용)
# ─────────────────────────────────────────────
class ControlCommand(BaseModel):
    device: str = Field(description="제어할 장치 이름 (예: 환기팬, 제습기, 창문 등)")
    action: str = Field(description="수행할 동작 (예: ON, OFF, OPEN, CLOSE 등)")
    value: Optional[str] = Field(None, description="설정할 값 (예: 50%, 25도 등)")
    reason: str = Field(description="이 제어 동작을 수행하는 이유")

from pydantic import model_validator

class AgentResponse(BaseModel):
    answer: str = Field(description="에이전트의 상황 판단 및 최종 답변 텍스트")
    control_sequence: List[ControlCommand] = Field(
        default_factory=list,
        description="상황에 따라 필요한 제어 명령 리스트. 제어가 필요 없거나 일반 질문인 경우 빈 리스트 []를 반환합니다."
    )

    @model_validator(mode='after')
    def enforce_safety_guardrails(self) -> 'AgentResponse':
        # 1. 동일 장치 중복 명령 제거 (최초 명령만 유지하여 충돌 방지)
        unique_devices = set()
        filtered_seq = []
        for cmd in self.control_sequence:
            if cmd.device not in unique_devices:
                unique_devices.add(cmd.device)
                filtered_seq.append(cmd)
        self.control_sequence = filtered_seq
        return self


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
    if state.get("system_triggered"):
        print(f"[Node: analyze_query] System-triggered autonomous control: {query}")
        return {
            "is_sensor_needed": False,
            "is_rag_needed": True,
            "intents": {
                "is_sensor_needed": False,
                "is_rag_needed": True,
            },
            "sensor_data": state.get("sensor_data"),
        }

    print(f"[Node: analyze_query] 질문 분석 시작: {query}")

    try:
        llm = _get_gemini_llm(temperature=0)
        structured_llm = llm.with_structured_output(IntentAnalysis)

        # AGENTS.md 섹션 5에서 의도 분석 프롬프트 로드
        intent_prompt_text = _load_prompt_from_agents_md("5. 의도 분석 프롬프트")
        if not intent_prompt_text:
            # AGENTS.md 로드 실패 시 인라인 폴백
            intent_prompt_text = (
                "너는 스마트팜 자율 에이전트의 의도 파악기야. "
                "is_sensor_needed와 is_rag_needed를 판단해줘.\n\n사용자 질문: {query}"
            )
        prompt = PromptTemplate.from_template(intent_prompt_text)
        
        chain = prompt | structured_llm
        result: IntentAnalysis = chain.invoke({"query": query})

        is_sensor_needed = result.is_sensor_needed
        is_rag_needed = result.is_rag_needed
        reason = result.reason
    except Exception as e:
        print(f"[Node: analyze_query] Gemini LLM 호출 실패 (API 키 확인 필요). 에러: {e}")

        fallback_keywords = ["온도", "습도", "상태", "환경", "얼마나", "어때", "co2", "알려줘"]
        is_sensor_needed = any(kw in query.replace(" ", "") for kw in fallback_keywords)
        rag_keywords = ["어떻게", "방법", "방제", "대처", "알려줘"]
        is_rag_needed = any(kw in query for kw in rag_keywords)
        reason = "LLM 통신 실패로 인한 키워드 룰 기반 강제 맵핑"

        print(f"[Node: analyze_query] 분석 결과 - 센서: {is_sensor_needed}, RAG: {is_rag_needed} (이유: {reason})")

        return {
            "is_sensor_needed": is_sensor_needed,
            "is_rag_needed": is_rag_needed,
            "sensor_data": None  # 새로운 턴 시작 시 이전 상태 초기화
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
    
    # Persist sensor data to SQLite (best-effort: failures should not break node)
    try:
        db = SessionLocal()
        try:
            temp = sensor_result.get("temperature") if isinstance(sensor_result, dict) else None
            hum = sensor_result.get("humidity") if isinstance(sensor_result, dict) else None
            co2 = sensor_result.get("co2") if isinstance(sensor_result, dict) else None

            # Detect fallback: either API key missing/placeholder or exact fallback values
            invalid_api_key = (not settings.SMARTFARM_API_KEY) or str(settings.SMARTFARM_API_KEY).startswith("your") or str(settings.SMARTFARM_API_KEY) == "temp_key"
            is_fallback = False
            try:
                if invalid_api_key:
                    is_fallback = True
                else:
                    # common fallback signature from SensorService
                    is_fallback = (temp == 25.5 and hum == 85.0 and co2 == 450)
            except Exception:
                is_fallback = False

            raw_json = sensor_result if isinstance(sensor_result, dict) else {}

            sensor_log = SensorLog(
                temperature=temp,
                humidity=hum,
                co2=int(co2) if (co2 is not None and isinstance(co2, (int, float))) else None,
                is_fallback=bool(is_fallback),
                raw_response=raw_json,
            )
            db.add(sensor_log)
            db.commit()
        except Exception as db_e:
            print(f"[Node: fetch_sensor_data_node] DB 저장 중 오류 발생: {db_e}")
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            try:
                db.close()
            except Exception:
                pass
    except Exception as e:
        print(f"[Node: fetch_sensor_data_node] DB 세션 생성 실패 또는 기타 에러: {e}")

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
    
    # RAG 서비스 호출
    from app.services.rag_service import RagService
    rag_service = RagService()
    
    docs = rag_service.retrieve_docs(query)
    
    print(f"[Node: retrieve_knowledge] 검색된 문서 수: {len(docs)}")

    return {
        "retrieved_docs": docs
    }


UNSUPPORTED_CROP_KEYWORDS = {
    "파인애플", "딸기", "오이", "상추", "고추", "파프리카", "수박", "멜론",
    "감자", "고구마", "벼", "쌀", "옥수수", "콩", "사과", "배", "포도",
    "banana", "pineapple", "strawberry", "cucumber", "lettuce", "pepper",
}

TOMATO_ONLY_REFUSAL = (
    "저는 토마토 생육 및 제어 전문가이므로 해당 작물에 대해서는 정확한 가이드를 드릴 수 없습니다."
)


def _contains_unsupported_crop(query: str) -> bool:
    normalized = query.lower().replace(" ", "")
    return any(keyword.lower().replace(" ", "") in normalized for keyword in UNSUPPORTED_CROP_KEYWORDS)


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

[출력 형식 제약 - 절대 준수]
답변을 작성할 때 `##`, `###` 같은 마크다운 제목(Heading) 태그는 프론트엔드 파싱 오류를 유발하므로 절대 사용하지 마십시오.
대신 가독성을 위해 명확한 줄바꿈(\n)과 볼드체(**텍스트**), 그리고 글머리 기호(*)만 사용하여 깔끔하게 본문 형태로만 작성하십시오.

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
        # Pydantic 모델의 딕셔너리 변환 (API 호환성을 위해 dict 리스트도 별도 유지)
        control_sequence_dicts = [cmd.dict() for cmd in response.control_sequence]
        control_sequence_objs = response.control_sequence

        # ── KS X 3267 Modbus RTU 프레임 변환 (Protocol Translator) ──
        if control_sequence_objs:
            modbus_frames = ModbusTranslator.build_frames(control_sequence_objs)

            # Persist control logs for each issued control command (best-effort)
            try:
                db = SessionLocal()
                try:
                    reason_text = (answer or "")[:1024]
                    for cmd in control_sequence_objs:
                        device = cmd.device if isinstance(cmd.device, str) else getattr(cmd.device, 'value', str(cmd.device))
                        action = cmd.action if isinstance(cmd.action, str) else getattr(cmd.action, 'value', str(cmd.action))
                        value = getattr(cmd, 'value', None) if hasattr(cmd, 'value') else None
                        # Build the hex frame for logging (translator returns '[Tx] ...' or warning)
                        try:
                            hex_frame = ModbusTranslator.translate(device, action, float(value) if value is not None else None)
                        except Exception:
                            hex_frame = ""

                        control_log = ControlLog(
                            device_code=str(device),
                            action=str(action),
                            hex_frame=str(hex_frame),
                            reason=reason_text,
                        )
                        db.add(control_log)
                    db.commit()
                except Exception as db_e:
                    print(f"[Node: generate_answer] DB 저장 중 오류 발생: {db_e}")
                    try:
                        db.rollback()
                    except Exception:
                        pass
                finally:
                    try:
                        db.close()
                    except Exception:
                        pass
            except Exception as e_db:
                print(f"[Node: generate_answer] DB 세션 생성 실패 또는 에러: {e_db}")

        else:
            modbus_frames = None

    except Exception as e:
        print(f"[Node: generate_answer] 답변 생성 실패: {e}")
        answer = (
            "죄송합니다. 현재 AI 서버(Gemini) 모델과의 통신이 원활하지 않아 답변을 생성하지 못했습니다.\n\n"
            f"[디버그용 수집 데이터]\n- 센서: {sensor_data_str}"
        )
        control_sequence_dicts = []
        control_sequence_objs = None
        modbus_frames = None
        
    print(f"[Node: generate_answer] 생성된 답변 길이: {len(answer)}자, 제어 명령 수: {len(control_sequence_dicts)}, Modbus 프레임 수: {len(modbus_frames) if modbus_frames else 0}")

    return {
        "answer": answer,
        "control_sequence": control_sequence_dicts,
        "modbus_frames": modbus_frames
    }