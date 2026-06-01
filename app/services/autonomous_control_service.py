"""
AutonomousControlService 스텁 구현.

이 서비스는 온실 환경 데이터를 모니터링하고 임계값 초과 시 자율 제어 명령을 실행합니다.
현재는 임포트 오류 방지를 위한 스텁(stub)이며, 실제 기능은 추후 구현됩니다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class DeviceCode(str, Enum):
    VENT_FAN = "CC18"
    TOP_WINDOW = "CC01"
    SIDE_WINDOW = "CC02"


class ActionCode(str, Enum):
    ON = "ON"
    OFF = "OFF"
    OPEN = "OPEN"
    CLOSE = "CLOSE"


@dataclass
class ControlCommand:
    device: DeviceCode
    action: ActionCode
    description: str


@dataclass
class CriticalAlert:
    alert_type: str
    message: str
    control_sequence: List[ControlCommand] = field(default_factory=list)


class AutonomousControlService:
    """온실 임계값 감지 및 자율 제어 서비스 (스텁)"""

    # 온도 임계값 (℃)
    TEMP_CRITICAL_HIGH = 40.0

    @staticmethod
    def detect_critical_alert(sensor_data: dict) -> Optional[CriticalAlert]:
        """
        수집된 센서 데이터에서 임계 이상 상황을 감지합니다.
        임계 상황이 없으면 None을 반환합니다.
        """
        temperature = sensor_data.get("temperature")
        if temperature is not None and float(temperature) >= AutonomousControlService.TEMP_CRITICAL_HIGH:
            return CriticalAlert(
                alert_type="HIGH_TEMP",
                message=f"온도 임계값 초과: {temperature}℃",
                control_sequence=[
                    ControlCommand(DeviceCode.VENT_FAN, ActionCode.ON, "환기팬 가동"),
                    ControlCommand(DeviceCode.TOP_WINDOW, ActionCode.OPEN, "천창 개방"),
                    ControlCommand(DeviceCode.SIDE_WINDOW, ActionCode.OPEN, "측창 개방"),
                ],
            )
        return None

    @staticmethod
    async def handle_critical_alert_safe(alert: CriticalAlert, sensor_data: dict) -> None:
        """
        임계 경보를 처리하는 비동기 메서드입니다.
        실제 장비 제어 로직이 추후 이 메서드에 구현됩니다.
        """
        print(f"[AutonomousControlService] 임계 경보 처리 시작: {alert.alert_type}")
        for cmd in alert.control_sequence:
            print(f"  → 제어 명령: {cmd.device.value} {cmd.action.value} ({cmd.description})")
        print("[AutonomousControlService] 임계 경보 처리 완료")
