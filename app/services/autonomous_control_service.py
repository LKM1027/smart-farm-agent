from __future__ import annotations

import asyncio
from dataclasses import dataclass
import sys
from typing import Any, Dict, List, Optional

from app.agent.nodes import ModbusTranslator
from app.database import SessionLocal
from app.models import ControlLog
from app.schemas.agent_dto import ControlSequence, ControlAction, HardwareDevice
from app.services.agent_service import AgentService


@dataclass(frozen=True)
class CriticalAlert:
    metric: str
    value: float
    threshold: str
    message: str
    control_sequence: List[ControlSequence]


class AutonomousControlService:
    """Detect critical crop-environment anomalies and invoke the agent off-path."""

    @staticmethod
    def detect_critical_alert(sensor_data: Dict[str, Any]) -> Optional[CriticalAlert]:
        temperature = AutonomousControlService._to_float(sensor_data.get("temperature"))
        co2 = AutonomousControlService._to_float(sensor_data.get("co2"))

        if temperature is not None and temperature > 35.0:
            return CriticalAlert(
                metric="temperature",
                value=temperature,
                threshold="> 35.0C",
                message=f"현재 시설 온도가 {temperature:.1f}C로 토마토 생육 한계 임계치를 초과했습니다.",
                control_sequence=[
                    ControlSequence(
                        device=HardwareDevice.EXHAUST_FAN,
                        action=ControlAction.ON,
                        value=None,
                        description="고온 스트레스 완화를 위한 환풍기 즉시 가동",
                    ),
                    ControlSequence(
                        device=HardwareDevice.ROOF_VENT,
                        action=ControlAction.OPEN,
                        value=None,
                        description="상부 열 배출을 위한 천창 개방",
                    ),
                    ControlSequence(
                        device=HardwareDevice.SIDE_VENT,
                        action=ControlAction.OPEN,
                        value=None,
                        description="측면 환기로 온실 내부 열기 배출",
                    ),
                ],
            )

        if temperature is not None and temperature < 10.0:
            return CriticalAlert(
                metric="temperature",
                value=temperature,
                threshold="< 10.0C",
                message=f"현재 시설 온도가 {temperature:.1f}C로 저온 피해 임계치 아래입니다.",
                control_sequence=[
                    ControlSequence(
                        device=HardwareDevice.HVAC,
                        action=ControlAction.ON,
                        value=None,
                        description="저온 피해 방지를 위한 난방기 가동",
                    ),
                    ControlSequence(
                        device=HardwareDevice.ROOF_VENT,
                        action=ControlAction.CLOSE,
                        value=None,
                        description="열 손실 저감을 위한 천창 폐쇄",
                    ),
                    ControlSequence(
                        device=HardwareDevice.SIDE_VENT,
                        action=ControlAction.CLOSE,
                        value=None,
                        description="열 손실 저감을 위한 측창 폐쇄",
                    ),
                ],
            )

        if co2 is not None and co2 < 400.0:
            return CriticalAlert(
                metric="co2",
                value=co2,
                threshold="< 400ppm",
                message=f"현재 CO2 농도가 {co2:.0f}ppm으로 광합성 저해 임계치 아래입니다.",
                control_sequence=[
                    ControlSequence(
                        device=HardwareDevice.ROOF_VENT,
                        action=ControlAction.OPEN,
                        value=None,
                        description="외기 유입을 통한 CO2 농도 회복",
                    ),
                    ControlSequence(
                        device=HardwareDevice.CIRCULATION_FAN,
                        action=ControlAction.ON,
                        value=None,
                        description="온실 내부 공기 순환으로 CO2 분포 균일화",
                    ),
                ],
            )

        return None

    @staticmethod
    async def handle_critical_alert(alert: CriticalAlert, sensor_data: Dict[str, Any]) -> None:
        prompt = AutonomousControlService._build_system_prompt(alert)
        final_state: Dict[str, Any] = {}

        try:
            final_state = await asyncio.to_thread(
                AutonomousControlService._run_system_alert_sync,
                prompt,
                sensor_data,
            )
        except Exception as exc:
            print(f"[AutonomousControl] LangGraph invoke failed: {exc}")

        modbus_frames = final_state.get("modbus_frames") or []
        control_sequence = final_state.get("control_sequence") or []
        answer = final_state.get("answer") or ""

        if not modbus_frames:
            modbus_frames = ModbusTranslator.build_frames(alert.control_sequence)
            control_sequence = [cmd.model_dump() for cmd in alert.control_sequence]
            answer = (
                "LangGraph 응답에서 제어 시퀀스가 생성되지 않아 "
                "사전 정의된 긴급 안전 시퀀스로 Modbus 프레임을 생성했습니다."
            )
            AutonomousControlService._persist_command_logs(alert, modbus_frames, answer)

        report = AutonomousControlService._format_report(alert, control_sequence, modbus_frames, answer)
        AutonomousControlService._persist_summary_log(alert, modbus_frames, report)
        AutonomousControlService._print_intervention_report(report)

    @staticmethod
    async def handle_critical_alert_safe(alert: CriticalAlert, sensor_data: Dict[str, Any]) -> None:
        try:
            await AutonomousControlService.handle_critical_alert(alert, sensor_data)
        except Exception as exc:
            print(f"[AutonomousControl] critical alert task failed: {exc}")

    @staticmethod
    def _build_system_prompt(alert: CriticalAlert) -> str:
        command_lines = "\n".join(
            f"- {cmd.device.value} {cmd.action.value}"
            + (f" value={cmd.value}" if cmd.value is not None else "")
            + f": {cmd.description}"
            for cmd in alert.control_sequence
        )
        return (
            "시스템 긴급 알림: "
            f"{alert.message} 작물 피해를 막기 위해 KS X 3267 표준 도구를 사용하여 "
            "즉시 아래 제어 시퀀스를 실행하고 실제 Modbus RTU Hex 프레임을 생성하세요.\n"
            f"{command_lines}\n"
            "사용자 확인을 기다리지 말고 자율 관제 개입 리포트를 작성하세요."
        )

    @staticmethod
    def _run_system_alert_sync(prompt: str, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        return asyncio.run(
            AgentService.execute_system_alert(
                query=prompt,
                sensor_data=sensor_data,
            )
        )

    @staticmethod
    def _format_report(
        alert: CriticalAlert,
        control_sequence: List[Any],
        modbus_frames: List[str],
        answer: str,
    ) -> str:
        return (
            f"alert={alert.metric} value={alert.value} threshold={alert.threshold}\n"
            f"message={alert.message}\n"
            f"control_commands={len(control_sequence)} modbus_frames={len(modbus_frames)}\n"
            f"frames:\n" + "\n".join(modbus_frames) + "\n"
            f"agent_report:\n{answer}"
        )

    @staticmethod
    def _persist_command_logs(alert: CriticalAlert, modbus_frames: List[str], reason: str) -> None:
        tx_frames = [frame for frame in modbus_frames if frame.startswith("[Tx]")]
        try:
            with SessionLocal() as db:
                for cmd, frame in zip(alert.control_sequence, tx_frames):
                    db.add(
                        ControlLog(
                            device_code=cmd.device.value,
                            action=cmd.action.value,
                            hex_frame=frame,
                            reason=reason[:1024],
                        )
                    )
                db.commit()
        except Exception as exc:
            print(f"[AutonomousControl] command log persist failed: {exc}")

    @staticmethod
    def _persist_summary_log(alert: CriticalAlert, modbus_frames: List[str], report: str) -> None:
        try:
            with SessionLocal() as db:
                db.add(
                    ControlLog(
                        device_code="SYSTEM",
                        action="AUTONOMOUS_INTERVENTION",
                        hex_frame="\n".join(modbus_frames),
                        reason=report[:1024],
                    )
                )
                db.commit()
        except Exception as exc:
            print(f"[AutonomousControl] summary log persist failed: {exc}")

    @staticmethod
    def _print_intervention_report(report: str) -> None:
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            print(f"[🚨 자율 관제 개입]\n{report}")
        except UnicodeEncodeError:
            print(f"[ALERT 자율 관제 개입]\n{report}")

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
