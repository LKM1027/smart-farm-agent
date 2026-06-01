from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Union
from enum import Enum


# ──────────────────────────────────────────────────────────────────────────────
# KS X 3266:2022  스마트 온실을 위한 센서 인터페이스
# ──────────────────────────────────────────────────────────────────────────────
class SensorCode(str, Enum):
    """
    KS X 3266:2022 표준 센서 항목 코드 (온실 통합 제어기 ↔ 센서 노드 인터페이스)
    측정 범위 및 단위는 KS X 3266 표 3(13종 센서 규격 요약) 기준
    """
    TEMPERATURE   = "TI"      # 온도 (℃),  측정 범위: -20 ~ 80 ℃
    HUMIDITY      = "HI"      # 상대습도 (%), 측정 범위: 0 ~ 100 %
    CO2           = "CI"      # CO₂ 농도 (ppm), 0 ~ 3,000 ppm
    SOLAR         = "SI"      # 일사량 (W/m²), 0 ~ 2,000 W/m²
    WIND_DIR      = "WDI"     # 풍향 (°), 0 ~ 360°
    WIND_SPEED    = "WSI"     # 풍속 (m/s), 0 ~ 40 m/s
    RAIN          = "RI"      # 강우 감지 (ON/OFF)
    QUANTUM       = "QI"      # 광양자량 (μmol/m²/s), 0 ~ 2,000
    SOIL_MOISTURE = "SMI"     # 토양 수분 (% vol), 0 ~ 50 % vol
    SOIL_TENSION  = "STI"     # 토양 수분 장력 (kPa), 0 ~ -100 kPa
    EC            = "EI"      # 전기전도도 / 양액 EC (dS/m), 0 ~ 10 dS/m
    PH            = "PI"      # 수소이온농도 / 양액 pH, 2 ~ 12 pH
    SOIL_TEMP     = "SOILTI"  # 지온 (℃), -20 ~ 80 ℃


# ──────────────────────────────────────────────────────────────────────────────
# KS X 3265:2022  스마트 온실을 위한 구동기 인터페이스
# ──────────────────────────────────────────────────────────────────────────────
class HardwareDevice(str, Enum):
    """
    KS X 3265:2022 구동기 인터페이스 표준 장치 코드 (fatrCode 기반)
    +
    KS X 3288:2022 양액기 노드 Modbus 인터페이스 기반 양액기 제어 코드 (신규 추가)

    작동 방식 분류 (KS X 3265 §4.3):
      [스위치 정/OFF/역 방식] 천창, 측창, 보온커튼, 차광막 → ControlAction: OPEN/STOP/CLOSE
      [ON/OFF 방식]          환풍기, 유동팬, 관수모터, 관수밸브, 냉난방기 → ControlAction: ON/OFF
      [양액기 Modbus 제어]   KS X 3288 제어 명령 코드(401~403) 기반 → ControlAction: NU_ON/NU_OFF/NU_AREA_ON/NU_PARAM_ON
    """
    # ── KS X 3265 구동기 (9종) ──
    ROOF_VENT       = "CC01"     # 천창 (천장 개폐기)    — 정/OFF/역 방향 제어
    SIDE_VENT       = "CC02"     # 측창 (측면 개폐기)    — 정/OFF/역 방향 제어
    THERMAL_SCREEN  = "CC03"     # 보온커튼             — 정/OFF/역 방향 제어
    SHADE_SCREEN    = "CC04"     # 차광막              — 정/OFF/역 방향 제어
    EXHAUST_FAN     = "CC18"     # 환풍기 (배기팬)      — ON/OFF (SET_LV 레벨 제어 가능)
    CIRCULATION_FAN = "CC19"     # 유동팬              — ON/OFF
    IRRIGATION_PUMP = "CC21"     # 관수모터 (관수펌프)   — ON/OFF
    IRRIGATION_VALVE = "CC21_V"  # 관수밸브 (구역 밸브) — ON/OFF
    HVAC            = "CC22"     # 냉난방기             — ON/OFF (SET_TEMP 목표온도 설정 가능)

    # ── KS X 3288 양액기 Modbus 제어 코드 (신규 추가, 3종) ──
    NU_EC_SET = "NU_EC_SET"   # 양액 EC 목표값 설정 (Modbus reg 510, float dS/m)
    NU_PH_SET = "NU_PH_SET"   # 양액 pH 목표값 설정 (Modbus reg 512, float pH)
    NU_VALVE  = "NU_VALVE"    # 관수 구역 밸브 작동 (Modbus reg 506-507, AREA_ON=402)


# ──────────────────────────────────────────────────────────────────────────────
# KS X 3265:2022  제어 액션 코드
# ──────────────────────────────────────────────────────────────────────────────
class ControlAction(str, Enum):
    """
    KS X 3265 §4.3 작동 방식 및 KS X 3288 제어 명령 코드에 기반한 제어 액션

    [일반 구동기 — KS X 3265]
      OPEN   : 천창/측창/커튼/차광막 — 정방향(열기) 동작
      STOP   : 천창/측창/커튼/차광막 — 정지(OFF)
      CLOSE  : 천창/측창/커튼/차광막 — 역방향(닫기) 동작
      ON     : 환풍기/유동팬/관수모터/관수밸브/냉난방기 — 작동 (코드값 1)
      OFF    : 환풍기/유동팬/관수모터/관수밸브/냉난방기 — 정지 (코드값 0)
      SET_LV : 환풍기 출력 레벨 설정 (0.0 ~ 100.0 %)
      SET_TEMP: 냉난방기 목표 온도 설정 (15.0 ~ 35.0 ℃)

    [양액기 — KS X 3288 §제어 명령 테이블]
      NU_ON      : 양액기 1회 관수 작동 시작 (기 설정 EC/pH 반영, 코드값 401)
      NU_OFF     : 양액기 강제 정지           (코드값 0)
      NU_AREA_ON : 구역 관수 시작             (구역 번호 → value 필드, 코드값 402)
      NU_PARAM_ON: 파라미터 관수              (EC·pH·구역을 value 필드에 담아 전달, 코드값 403)
    """
    # 방향성 구동기 (천창/측창/커튼/차광막)
    OPEN   = "OPEN"
    STOP   = "STOP"
    CLOSE  = "CLOSE"
    # ON/OFF 구동기 (환풍기/유동팬/펌프/밸브/냉난방기)
    ON     = "ON"
    OFF    = "OFF"
    # 수치 설정 (환풍기 레벨, 냉난방기 목표 온도)
    SET_LV   = "SET_LV"
    SET_TEMP = "SET_TEMP"
    # 양액기 전용 제어 명령 (KS X 3288)
    NU_ON       = "NU_ON"        # 양액기 작동 (기 설정값 사용)
    NU_OFF      = "NU_OFF"       # 양액기 강제 정지
    NU_AREA_ON  = "NU_AREA_ON"   # 구역 관수 (value = 구역 번호 int)
    NU_PARAM_ON = "NU_PARAM_ON"  # 파라미터 관수 (value = EC 설정값 float)
    # 양액기 설정 전용
    NU_EC_SET   = "NU_EC_SET"    # EC 목표값 설정
    NU_PH_SET   = "NU_PH_SET"    # pH 목표값 설정


# ──────────────────────────────────────────────────────────────────────────────
# 채팅 요청 모델
# ──────────────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    """사용자가 에이전트에게 보내는 질의 모델"""
    query: str = Field(
        ...,
        description="사용자의 질문이나 명령",
        examples=["현재 온실 상태 어때?", "토마토 잎이 노란데 진단해줘."]
    )


# ──────────────────────────────────────────────────────────────────────────────
# 제어 시퀀스 모델 (안전 제어 레이어 포함)
# ──────────────────────────────────────────────────────────────────────────────
class ControlSequence(BaseModel):
    """
    에이전트가 결정한 개별 제어 명령 모델
    - device: KS X 3265 / KS X 3288 표준 코드만 허용
    - action: KS X 3265 §4.3 / KS X 3288 제어 명령 코드
    - value :
        · ON/OFF/OPEN/STOP/CLOSE → null (상태 제어, 코드값: 0=정지, 1=작동)
        · SET_LV   → float (0.0 ~ 100.0, 단위: %)
        · SET_TEMP → float (15.0 ~ 35.0, 단위: ℃)
        · NU_AREA_ON  → float (구역 번호, e.g., 1.0 ~ 10.0)
        · NU_PARAM_ON → float (EC 목표값, e.g., 2.5 dS/m)
        · NU_EC_SET   → float (EC 목표값, 0.0 ~ 10.0 dS/m)
        · NU_PH_SET   → float (pH 목표값, 2.0 ~ 12.0)
    """
    device: HardwareDevice = Field(
        ...,
        description="제어할 장치 (KS X 3265 / KS X 3288 표준 코드 필수)"
    )
    action: ControlAction = Field(
        ...,
        description="수행할 제어 액션 (KS X 3265 §4.3 / KS X 3288 제어 명령 코드)"
    )
    value: Optional[float] = Field(
        None,
        description=(
            "수치 제어 시 목표값. "
            "ON/OFF/OPEN/STOP/CLOSE → null, "
            "SET_LV → 0~100(%), SET_TEMP → 15~35(℃), "
            "NU_AREA_ON → 구역번호(int), NU_PARAM_ON/NU_EC_SET → EC값(dS/m), NU_PH_SET → pH값"
        )
    )
    description: str = Field(..., description="이 제어 동작을 수행하는 이유에 대한 설명")

    @model_validator(mode='after')
    def validate_action_for_device(self) -> 'ControlSequence':
        """KS 표준 준거 안전 가드레일 검증"""

        # ── 1. 수치 필드 필수 여부 검증 ──
        requires_value_actions = {
            ControlAction.SET_LV, ControlAction.SET_TEMP,
            ControlAction.NU_AREA_ON, ControlAction.NU_PARAM_ON,
            ControlAction.NU_EC_SET, ControlAction.NU_PH_SET,
        }
        if self.action in requires_value_actions and self.value is None:
            raise ValueError(f"Action '{self.action.value}' requires a numeric 'value'.")

        # ── 2. 장치별 허용 액션 및 안전 범위 검증 ──

        # 방향성 구동기 (천창/측창/커튼/차광막) — KS X 3265 §4.3
        DIRECTIONAL_DEVICES = {
            HardwareDevice.ROOF_VENT,
            HardwareDevice.SIDE_VENT,
            HardwareDevice.THERMAL_SCREEN,
            HardwareDevice.SHADE_SCREEN,
        }
        if self.device in DIRECTIONAL_DEVICES:
            allowed = {ControlAction.OPEN, ControlAction.STOP, ControlAction.CLOSE}
            if self.action not in allowed:
                raise ValueError(
                    f"{self.device.name}은 방향성 구동기로 OPEN/STOP/CLOSE만 지원합니다. "
                    f"(KS X 3265 §4.3) Got: {self.action.value}"
                )

        # 환풍기 (배기팬) — ON/OFF + SET_LV(0~100%)
        elif self.device == HardwareDevice.EXHAUST_FAN:
            allowed = {ControlAction.ON, ControlAction.OFF, ControlAction.SET_LV}
            if self.action not in allowed:
                raise ValueError(f"EXHAUST_FAN(CC18)은 ON/OFF/SET_LV만 지원합니다. Got: {self.action.value}")
            if self.action == ControlAction.SET_LV and not (0.0 <= self.value <= 100.0):
                raise ValueError(f"EXHAUST_FAN 레벨은 0~100%이어야 합니다. Got: {self.value}")

        # 유동팬 — ON/OFF만
        elif self.device == HardwareDevice.CIRCULATION_FAN:
            if self.action not in {ControlAction.ON, ControlAction.OFF}:
                raise ValueError(f"CIRCULATION_FAN(CC19)은 ON/OFF만 지원합니다. Got: {self.action.value}")

        # 관수모터/관수밸브 — ON/OFF만
        elif self.device in {HardwareDevice.IRRIGATION_PUMP, HardwareDevice.IRRIGATION_VALVE}:
            if self.action not in {ControlAction.ON, ControlAction.OFF}:
                raise ValueError(f"{self.device.name}은 ON/OFF만 지원합니다. Got: {self.action.value}")

        # 냉난방기 — ON/OFF + SET_TEMP(15~35℃)
        elif self.device == HardwareDevice.HVAC:
            allowed = {ControlAction.ON, ControlAction.OFF, ControlAction.SET_TEMP}
            if self.action not in allowed:
                raise ValueError(f"HVAC(CC22)는 ON/OFF/SET_TEMP만 지원합니다. Got: {self.action.value}")
            if self.action == ControlAction.SET_TEMP and not (15.0 <= self.value <= 35.0):
                raise ValueError(f"목표 온도는 안전 범위(15~35℃)를 초과할 수 없습니다. Got: {self.value}")

        # ── 양액기 EC 설정 (KS X 3288 reg 510) ──
        elif self.device == HardwareDevice.NU_EC_SET:
            if self.action != ControlAction.NU_EC_SET:
                raise ValueError("NU_EC_SET 장치는 NU_EC_SET 액션만 허용합니다.")
            if not (0.0 <= self.value <= 10.0):
                raise ValueError(f"EC 설정값은 0~10 dS/m 이어야 합니다. Got: {self.value}")

        # ── 양액기 pH 설정 (KS X 3288 reg 512) ──
        elif self.device == HardwareDevice.NU_PH_SET:
            if self.action != ControlAction.NU_PH_SET:
                raise ValueError("NU_PH_SET 장치는 NU_PH_SET 액션만 허용합니다.")
            if not (2.0 <= self.value <= 12.0):
                raise ValueError(f"pH 설정값은 2~12 이어야 합니다. Got: {self.value}")

        # ── 양액기 구역 관수 밸브 (KS X 3288 AREA_ON=402) ──
        elif self.device == HardwareDevice.NU_VALVE:
            allowed = {
                ControlAction.NU_ON, ControlAction.NU_OFF,
                ControlAction.NU_AREA_ON, ControlAction.NU_PARAM_ON,
            }
            if self.action not in allowed:
                raise ValueError(
                    f"NU_VALVE는 NU_ON/NU_OFF/NU_AREA_ON/NU_PARAM_ON만 허용합니다. Got: {self.action.value}"
                )
            if self.action == ControlAction.NU_AREA_ON and (self.value is None or self.value < 1):
                raise ValueError("NU_AREA_ON은 관수 구역 번호(1 이상)를 value에 명시해야 합니다.")

        return self


# ──────────────────────────────────────────────────────────────────────────────
# 에이전트 의도 플래그
# ──────────────────────────────────────────────────────────────────────────────
from typing import Any, Dict

class Intents(BaseModel):
    """에이전트가 판단한 사용자 의도 플래그"""
    is_sensor_needed: bool = Field(..., description="KS X 3266 센서 데이터 조회 작동 여부")
    is_rag_needed:    bool = Field(..., description="농진청 RAG 지식 검색 작동 여부")


# ──────────────────────────────────────────────────────────────────────────────
# 최종 통합 응답 모델
# ──────────────────────────────────────────────────────────────────────────────
class AgentFinalResponse(BaseModel):
    """프론트엔드 UI 시각화를 위한 최종 통합 응답 모델"""
    intents:          Intents                         = Field(..., description="에이전트의 상황 판단 플래그")
    sensor_data:      Optional[Dict[str, Any]]        = Field(None, description="KS X 3266 기반 실시간 센서 데이터 (TI/HI/CI/EI/PI 등)")
    control_sequence: Optional[List[ControlSequence]] = Field(None, description="KS X 3265/3288 준거 제어 시퀀스 리스트")
    answer:           str                             = Field(..., description="에이전트의 상황 판단 및 최종 답변 텍스트")
    modbus_frames:    Optional[List[str]]             = Field(
        None,
        description=(
            "KS X 3267:2022 Modbus RTU 헥사 프레임 배열 — 물리 장비(PLC) 직접 전송용. "
            "형식: '[Tx] SlaveID FC RegAddr(H) RegAddr(L) Data(H) Data(L) CRC(H) CRC(L)' "
            "예시: '[Tx] 01 06 01 2C 00 01 C8 0A'"
        )
    )
