"""
tests/unit/test_control_schemas.py

AGENTS.md §3 '하드웨어 제어 절대 규칙' 검증 테스트.

이 테스트가 실패하면 KS X 3265 / KS X 3288 안전 범위 가드레일이 무너진 것입니다.
배포 파이프라인에서 절대로 SKIP하거나 무시하지 마십시오.

테스트 대상: app/schemas/agent_dto.py — ControlSequence Pydantic model_validator
"""

import pytest
from pydantic import ValidationError

from app.schemas.agent_dto import (
    ControlAction,
    ControlSequence,
    HardwareDevice,
)


# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼: 정상 ControlSequence 생성 (검증 성공 케이스용)
# ─────────────────────────────────────────────────────────────────────────────

def _make_cmd(device: HardwareDevice, action: ControlAction, value=None, desc="테스트") -> ControlSequence:
    return ControlSequence(device=device, action=action, value=value, description=desc)


# ─────────────────────────────────────────────────────────────────────────────
# CC22 냉난방기 (HVAC) — SET_TEMP 안전 범위: 15.0 ~ 35.0 ℃
# AGENTS.md §3-1 / KS X 3265 §4.3
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.hardware
class TestHVACTemperatureGuardrail:
    """CC22 냉난방기 목표 온도 안전 범위 검증."""

    def test_hvac_set_temp_upper_limit_rejected(self):
        """36.0℃ → 상한(35.0℃) 초과이므로 ValueError 발생해야 함."""
        with pytest.raises((ValueError, ValidationError)):
            _make_cmd(HardwareDevice.HVAC, ControlAction.SET_TEMP, value=36.0)

    def test_hvac_set_temp_lower_limit_rejected(self):
        """14.0℃ → 하한(15.0℃) 미만이므로 ValueError 발생해야 함."""
        with pytest.raises((ValueError, ValidationError)):
            _make_cmd(HardwareDevice.HVAC, ControlAction.SET_TEMP, value=14.0)

    def test_hvac_set_temp_exactly_upper_boundary_accepted(self):
        """35.0℃ → 상한 경계값이므로 허용되어야 함."""
        cmd = _make_cmd(HardwareDevice.HVAC, ControlAction.SET_TEMP, value=35.0)
        assert cmd.value == 35.0

    def test_hvac_set_temp_exactly_lower_boundary_accepted(self):
        """15.0℃ → 하한 경계값이므로 허용되어야 함."""
        cmd = _make_cmd(HardwareDevice.HVAC, ControlAction.SET_TEMP, value=15.0)
        assert cmd.value == 15.0

    def test_hvac_set_temp_nominal_accepted(self):
        """25.0℃ → 정상 범위 중간값이므로 허용되어야 함."""
        cmd = _make_cmd(HardwareDevice.HVAC, ControlAction.SET_TEMP, value=25.0)
        assert cmd.value == 25.0

    def test_hvac_on_action_accepted(self):
        """CC22 ON 명령은 value 없이 허용되어야 함."""
        cmd = _make_cmd(HardwareDevice.HVAC, ControlAction.ON)
        assert cmd.device == HardwareDevice.HVAC
        assert cmd.action == ControlAction.ON

    def test_hvac_set_temp_without_value_rejected(self):
        """SET_TEMP 액션에 value가 없으면 거부되어야 함."""
        with pytest.raises((ValueError, ValidationError)):
            _make_cmd(HardwareDevice.HVAC, ControlAction.SET_TEMP, value=None)


# ─────────────────────────────────────────────────────────────────────────────
# CC18 환풍기 (EXHAUST_FAN) — SET_LV 안전 범위: 0.0 ~ 100.0 %
# AGENTS.md §3-1 / KS X 3265 §4.3
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.hardware
class TestExhaustFanLevelGuardrail:
    """CC18 환풍기 출력 레벨 안전 범위 검증."""

    def test_exhaust_fan_level_over_100_rejected(self):
        """101.0% → 상한(100.0%) 초과이므로 ValueError 발생해야 함."""
        with pytest.raises((ValueError, ValidationError)):
            _make_cmd(HardwareDevice.EXHAUST_FAN, ControlAction.SET_LV, value=101.0)

    def test_exhaust_fan_level_negative_rejected(self):
        """-1.0% → 하한(0.0%) 미만이므로 ValueError 발생해야 함."""
        with pytest.raises((ValueError, ValidationError)):
            _make_cmd(HardwareDevice.EXHAUST_FAN, ControlAction.SET_LV, value=-1.0)

    def test_exhaust_fan_level_100_accepted(self):
        """100.0% → 상한 경계값이므로 허용되어야 함."""
        cmd = _make_cmd(HardwareDevice.EXHAUST_FAN, ControlAction.SET_LV, value=100.0)
        assert cmd.value == 100.0

    def test_exhaust_fan_level_0_accepted(self):
        """0.0% → 하한 경계값이므로 허용되어야 함."""
        cmd = _make_cmd(HardwareDevice.EXHAUST_FAN, ControlAction.SET_LV, value=0.0)
        assert cmd.value == 0.0

    def test_exhaust_fan_level_65_accepted(self):
        """65.0% → 정상 범위이므로 허용되어야 함."""
        cmd = _make_cmd(HardwareDevice.EXHAUST_FAN, ControlAction.SET_LV, value=65.0)
        assert cmd.value == 65.0

    def test_exhaust_fan_set_lv_without_value_rejected(self):
        """SET_LV에 value가 없으면 거부되어야 함."""
        with pytest.raises((ValueError, ValidationError)):
            _make_cmd(HardwareDevice.EXHAUST_FAN, ControlAction.SET_LV, value=None)


# ─────────────────────────────────────────────────────────────────────────────
# 방향성 구동기 (천창/측창/보온커튼/차광막) — OPEN/STOP/CLOSE만 허용
# AGENTS.md §3-1 / KS X 3265 §4.3
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.hardware
class TestDirectionalActuatorGuardrail:
    """방향성 구동기에 ON/OFF 등 잘못된 액션 차단 검증."""

    @pytest.mark.parametrize("device", [
        HardwareDevice.ROOF_VENT,
        HardwareDevice.SIDE_VENT,
        HardwareDevice.THERMAL_SCREEN,
        HardwareDevice.SHADE_SCREEN,
    ])
    def test_directional_device_rejects_on_action(self, device):
        """방향성 구동기(CC01~CC04)에 ON 명령은 거부되어야 함."""
        with pytest.raises((ValueError, ValidationError)):
            _make_cmd(device, ControlAction.ON)

    @pytest.mark.parametrize("device", [
        HardwareDevice.ROOF_VENT,
        HardwareDevice.SIDE_VENT,
        HardwareDevice.THERMAL_SCREEN,
        HardwareDevice.SHADE_SCREEN,
    ])
    def test_directional_device_rejects_set_temp_action(self, device):
        """방향성 구동기에 SET_TEMP 명령은 거부되어야 함."""
        with pytest.raises((ValueError, ValidationError)):
            _make_cmd(device, ControlAction.SET_TEMP, value=25.0)

    def test_roof_vent_open_accepted(self):
        """천창(CC01) OPEN 명령은 허용되어야 함."""
        cmd = _make_cmd(HardwareDevice.ROOF_VENT, ControlAction.OPEN)
        assert cmd.device == HardwareDevice.ROOF_VENT

    def test_side_vent_close_accepted(self):
        """측창(CC02) CLOSE 명령은 허용되어야 함."""
        cmd = _make_cmd(HardwareDevice.SIDE_VENT, ControlAction.CLOSE)
        assert cmd.device == HardwareDevice.SIDE_VENT


# ─────────────────────────────────────────────────────────────────────────────
# 양액기 EC/pH 설정 안전 범위 (KS X 3288)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.hardware
class TestNutrientSystemGuardrail:
    """양액기 EC/pH 설정값 안전 범위 검증."""

    def test_ec_over_10_rejected(self):
        """EC 10.5 dS/m → 상한(10.0) 초과이므로 거부되어야 함."""
        with pytest.raises((ValueError, ValidationError)):
            _make_cmd(HardwareDevice.NU_EC_SET, ControlAction.NU_EC_SET, value=10.5)

    def test_ec_nominal_accepted(self):
        """EC 2.5 dS/m → 정상 범위이므로 허용되어야 함."""
        cmd = _make_cmd(HardwareDevice.NU_EC_SET, ControlAction.NU_EC_SET, value=2.5)
        assert cmd.value == 2.5

    def test_ph_over_12_rejected(self):
        """pH 12.5 → 상한(12.0) 초과이므로 거부되어야 함."""
        with pytest.raises((ValueError, ValidationError)):
            _make_cmd(HardwareDevice.NU_PH_SET, ControlAction.NU_PH_SET, value=12.5)

    def test_ph_under_2_rejected(self):
        """pH 1.0 → 하한(2.0) 미만이므로 거부되어야 함."""
        with pytest.raises((ValueError, ValidationError)):
            _make_cmd(HardwareDevice.NU_PH_SET, ControlAction.NU_PH_SET, value=1.0)

    def test_ph_nominal_accepted(self):
        """pH 6.0 → 정상 범위이므로 허용되어야 함."""
        cmd = _make_cmd(HardwareDevice.NU_PH_SET, ControlAction.NU_PH_SET, value=6.0)
        assert cmd.value == 6.0


# ─────────────────────────────────────────────────────────────────────────────
# 중복 명령 제거 가드레일 (AgentResponse safety_guardrails)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestDuplicateCommandGuardrail:
    """동일 장치에 중복 명령이 들어올 때 첫 번째만 유지되는지 검증."""

    def test_duplicate_device_deduplicated(self):
        """동일 장치(CC18)에 ON → SET_LV 순서로 들어오면 ON만 유지되어야 함."""
        from app.agent.nodes import AgentResponse

        raw = AgentResponse(
            answer="테스트",
            control_sequence=[
                ControlSequence(device=HardwareDevice.EXHAUST_FAN, action=ControlAction.ON, description="먼저"),
                ControlSequence(device=HardwareDevice.EXHAUST_FAN, action=ControlAction.SET_LV, value=60.0, description="중복"),
            ],
        )
        assert len(raw.control_sequence) == 1
        assert raw.control_sequence[0].action == ControlAction.ON

    def test_different_devices_both_kept(self):
        """서로 다른 장치(CC18, CC01)는 모두 유지되어야 함."""
        from app.agent.nodes import AgentResponse

        raw = AgentResponse(
            answer="테스트",
            control_sequence=[
                ControlSequence(device=HardwareDevice.EXHAUST_FAN, action=ControlAction.ON, description="환풍기"),
                ControlSequence(device=HardwareDevice.ROOF_VENT, action=ControlAction.OPEN, description="천창"),
            ],
        )
        assert len(raw.control_sequence) == 2
