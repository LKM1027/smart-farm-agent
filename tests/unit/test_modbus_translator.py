"""
tests/unit/test_modbus_translator.py

KS X 3267:2022 Modbus RTU 프레임 변환기 단위 테스트.

AI(LLM)가 생성한 텍스트 명령이 정확한 RS485 Modbus RTU 16진수 프레임으로
변환되는지 검증합니다. 프레임 구조, CRC16 계산, 장치-레지스터 매핑을 테스트합니다.

테스트 대상: app/agent/nodes.py — ModbusTranslator 클래스
"""

import pytest

from app.agent.nodes import ModbusTranslator


# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼 함수
# ─────────────────────────────────────────────────────────────────────────────

def _parse_frame(frame_str: str) -> list[int]:
    """'[Tx] 05 06 03 12 00 01 XX XX' → [0x05, 0x06, 0x03, 0x12, 0x00, 0x01, ...]"""
    assert frame_str.startswith("[Tx]"), f"프레임이 [Tx]로 시작하지 않음: {frame_str!r}"
    hex_parts = frame_str.replace("[Tx] ", "").split()
    return [int(h, 16) for h in hex_parts]


def _verify_crc16(frame_bytes: list[int]) -> bool:
    """마지막 2바이트가 앞 바이트들의 CRC16(Modbus) 값인지 검증합니다."""
    data = bytes(frame_bytes[:-2])
    expected_crc = ModbusTranslator._crc16(data)
    actual_lo = frame_bytes[-2]
    actual_hi = frame_bytes[-1]
    return actual_lo == (expected_crc & 0xFF) and actual_hi == ((expected_crc >> 8) & 0xFF)


# ─────────────────────────────────────────────────────────────────────────────
# CC18 환풍기 (SlaveID=0x05, RegAddr=0x0312) 프레임 검증
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestExhaustFanFrame:
    """CC18 환풍기 Modbus RTU 프레임 생성 검증."""

    def test_exhaust_fan_on_frame_prefix(self):
        """CC18 ON → [Tx] 05 06 03 12 00 01 ... 형식이어야 함."""
        frame = ModbusTranslator.translate("CC18", "ON")
        assert frame.startswith("[Tx]"), f"프레임 형식 오류: {frame}"
        parts = _parse_frame(frame)
        assert parts[0] == 0x05, "SlaveID는 0x05여야 함"
        assert parts[1] == 0x06, "FunctionCode는 0x06(Write Single Register)여야 함"
        assert parts[2] == 0x03, "RegAddr High는 0x03이어야 함"
        assert parts[3] == 0x12, "RegAddr Low는 0x12이어야 함"
        assert parts[4] == 0x00, "Data High는 0x00이어야 함 (ON=0x0001)"
        assert parts[5] == 0x01, "Data Low는 0x01이어야 함 (ON=0x0001)"

    def test_exhaust_fan_on_crc_valid(self):
        """CC18 ON 프레임의 CRC16이 유효해야 함."""
        frame = ModbusTranslator.translate("CC18", "ON")
        parts = _parse_frame(frame)
        assert _verify_crc16(parts), f"CRC16 검증 실패: {frame}"

    def test_exhaust_fan_off_frame(self):
        """CC18 OFF → Data가 0x0000이어야 함."""
        frame = ModbusTranslator.translate("CC18", "OFF")
        parts = _parse_frame(frame)
        assert parts[4] == 0x00 and parts[5] == 0x00, "OFF 명령의 Data는 0x0000이어야 함"

    def test_exhaust_fan_set_lv_frame(self):
        """CC18 SET_LV 65 → Data가 65(0x0041)이어야 함."""
        frame = ModbusTranslator.translate("CC18", "SET_LV", value=65.0)
        parts = _parse_frame(frame)
        data_value = (parts[4] << 8) | parts[5]
        assert data_value == 65, f"SET_LV=65 기대하였으나 {data_value} 수신"

    def test_exhaust_fan_set_lv_crc_valid(self):
        """CC18 SET_LV 프레임의 CRC16이 유효해야 함."""
        frame = ModbusTranslator.translate("CC18", "SET_LV", value=50.0)
        parts = _parse_frame(frame)
        assert _verify_crc16(parts), f"CRC16 검증 실패: {frame}"

    def test_exhaust_fan_frame_length(self):
        """CC18 단일 레지스터 프레임은 8바이트여야 함 (슬레이브1+FC1+주소2+데이터2+CRC2)."""
        frame = ModbusTranslator.translate("CC18", "ON")
        parts = _parse_frame(frame)
        assert len(parts) == 8, f"프레임 길이 8 기대하였으나 {len(parts)} 수신"


# ─────────────────────────────────────────────────────────────────────────────
# CC01 천창 (SlaveID=0x01, RegAddr=0x0300) 프레임 검증
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestRoofVentFrame:
    """CC01 천창 Modbus RTU 프레임 생성 검증."""

    def test_roof_vent_open_slave_id(self):
        """CC01 OPEN → SlaveID는 0x01이어야 함."""
        frame = ModbusTranslator.translate("CC01", "OPEN")
        parts = _parse_frame(frame)
        assert parts[0] == 0x01, f"SlaveID 0x01 기대, {parts[0]:#04x} 수신"

    def test_roof_vent_open_reg_addr(self):
        """CC01 OPEN → RegAddr는 0x0300이어야 함."""
        frame = ModbusTranslator.translate("CC01", "OPEN")
        parts = _parse_frame(frame)
        reg_addr = (parts[2] << 8) | parts[3]
        assert reg_addr == 0x0300, f"RegAddr 0x0300 기대, {reg_addr:#06x} 수신"

    def test_roof_vent_open_data(self):
        """CC01 OPEN → Data는 0x0001이어야 함 (OPEN=1)."""
        frame = ModbusTranslator.translate("CC01", "OPEN")
        parts = _parse_frame(frame)
        data = (parts[4] << 8) | parts[5]
        assert data == 0x0001, f"OPEN=0x0001 기대, {data:#06x} 수신"

    def test_roof_vent_close_data(self):
        """CC01 CLOSE → Data는 0x0002이어야 함 (CLOSE=2)."""
        frame = ModbusTranslator.translate("CC01", "CLOSE")
        parts = _parse_frame(frame)
        data = (parts[4] << 8) | parts[5]
        assert data == 0x0002, f"CLOSE=0x0002 기대, {data:#06x} 수신"

    def test_roof_vent_stop_data(self):
        """CC01 STOP → Data는 0x0000이어야 함 (STOP=0)."""
        frame = ModbusTranslator.translate("CC01", "STOP")
        parts = _parse_frame(frame)
        data = (parts[4] << 8) | parts[5]
        assert data == 0x0000, f"STOP=0x0000 기대, {data:#06x} 수신"

    def test_roof_vent_crc_valid(self):
        """CC01 OPEN 프레임의 CRC16이 유효해야 함."""
        frame = ModbusTranslator.translate("CC01", "OPEN")
        parts = _parse_frame(frame)
        assert _verify_crc16(parts)


# ─────────────────────────────────────────────────────────────────────────────
# CC22 냉난방기 (SlaveID=0x09, RegAddr=0x0318) 프레임 검증
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestHVACFrame:
    """CC22 냉난방기 Modbus RTU 프레임 생성 검증."""

    def test_hvac_slave_id(self):
        """CC22 → SlaveID는 0x09이어야 함."""
        frame = ModbusTranslator.translate("CC22", "ON")
        parts = _parse_frame(frame)
        assert parts[0] == 0x09

    def test_hvac_set_temp_encoding(self):
        """CC22 SET_TEMP 25.0℃ → Data는 250(×10 인코딩)이어야 함."""
        frame = ModbusTranslator.translate("CC22", "SET_TEMP", value=25.0)
        parts = _parse_frame(frame)
        data = (parts[4] << 8) | parts[5]
        assert data == 250, f"SET_TEMP 25.0→250 기대, {data} 수신"

    def test_hvac_set_temp_35_encoding(self):
        """CC22 SET_TEMP 35.0℃ → Data는 350이어야 함."""
        frame = ModbusTranslator.translate("CC22", "SET_TEMP", value=35.0)
        parts = _parse_frame(frame)
        data = (parts[4] << 8) | parts[5]
        assert data == 350

    def test_hvac_crc_valid(self):
        """CC22 SET_TEMP 프레임의 CRC16이 유효해야 함."""
        frame = ModbusTranslator.translate("CC22", "SET_TEMP", value=22.0)
        parts = _parse_frame(frame)
        assert _verify_crc16(parts)


# ─────────────────────────────────────────────────────────────────────────────
# 알 수 없는 장치 처리
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestUnknownDeviceHandling:
    """알 수 없는 장치 코드 입력 시 안전하게 경고를 반환하는지 검증."""

    def test_unknown_device_returns_warn(self):
        """미등록 장치 코드 → [WARN]으로 시작하는 메시지 반환."""
        frame = ModbusTranslator.translate("CC99", "ON")
        assert frame.startswith("[WARN]"), f"경고 메시지 기대, {frame!r} 수신"

    def test_unknown_device_does_not_raise(self):
        """미등록 장치 코드 → 예외 없이 처리되어야 함."""
        result = ModbusTranslator.translate("INVALID_DEVICE", "ON")
        assert isinstance(result, str)


# ─────────────────────────────────────────────────────────────────────────────
# CRC16(Modbus) 알고리즘 자체 검증
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestCRC16Algorithm:
    """Modbus CRC16 계산 알고리즘 정확성 검증."""

    def test_crc16_known_value(self):
        """Modbus 표준 CRC16 알려진 값 검증.
        데이터: 01 06 00 01 00 01 → CRC: 0x9A98 (Lo=0x98, Hi=0x9A)
        """
        data = bytes([0x01, 0x06, 0x00, 0x01, 0x00, 0x01])
        crc = ModbusTranslator._crc16(data)
        # CRC16 Modbus 계산기 검증값
        assert crc == 0xca19, f"CRC16 0xCA19 기대, {crc:#06x} 수신"

    def test_crc16_empty_input(self):
        """빈 입력 → 초기값 0xFFFF 반환."""
        crc = ModbusTranslator._crc16(b"")
        assert crc == 0xFFFF

    def test_crc16_deterministic(self):
        """동일 입력 → 항상 동일한 CRC 반환 (결정론적)."""
        data = bytes([0x05, 0x06, 0x03, 0x12, 0x00, 0x01])
        assert ModbusTranslator._crc16(data) == ModbusTranslator._crc16(data)


# ─────────────────────────────────────────────────────────────────────────────
# build_frames() 전체 파이프라인 검증
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestBuildFramesPipeline:
    """build_frames()가 ControlSequence 리스트를 올바른 로그 형식으로 변환하는지 검증."""

    def test_build_frames_contains_sys_init(self):
        """결과에 KS X 3267 초기화 메시지가 포함되어야 함."""
        from app.schemas.agent_dto import ControlSequence, HardwareDevice, ControlAction

        cmds = [
            ControlSequence(device=HardwareDevice.EXHAUST_FAN, action=ControlAction.ON, description="test"),
        ]
        frames = ModbusTranslator.build_frames(cmds)
        assert any("KS X 3267:2022" in f for f in frames), "KS X 3267 초기화 메시지 없음"

    def test_build_frames_contains_tx_frame(self):
        """결과에 [Tx] 프레임이 포함되어야 함."""
        from app.schemas.agent_dto import ControlSequence, HardwareDevice, ControlAction

        cmds = [
            ControlSequence(device=HardwareDevice.ROOF_VENT, action=ControlAction.OPEN, description="test"),
        ]
        frames = ModbusTranslator.build_frames(cmds)
        tx_frames = [f for f in frames if f.startswith("[Tx]")]
        assert len(tx_frames) >= 1, "명령 1개에 대해 [Tx] 프레임이 1개 이상 있어야 함"

    def test_build_frames_contains_rx_ack(self):
        """[Tx] 다음에 [Rx] ACK 라인이 있어야 함."""
        from app.schemas.agent_dto import ControlSequence, HardwareDevice, ControlAction

        cmds = [
            ControlSequence(device=HardwareDevice.EXHAUST_FAN, action=ControlAction.ON, description="test"),
        ]
        frames = ModbusTranslator.build_frames(cmds)
        rx_frames = [f for f in frames if f.startswith("[Rx]")]
        assert len(rx_frames) >= 1, "[Rx] ACK 라인이 없음"

    def test_build_frames_transmission_complete(self):
        """결과 마지막에 전송 완료 메시지가 있어야 함."""
        from app.schemas.agent_dto import ControlSequence, HardwareDevice, ControlAction

        cmds = [
            ControlSequence(device=HardwareDevice.EXHAUST_FAN, action=ControlAction.ON, description="test"),
        ]
        frames = ModbusTranslator.build_frames(cmds)
        assert any("Transmission complete" in f for f in frames), "전송 완료 메시지 없음"

    def test_build_frames_cmd_count_logged(self):
        """command(s) queued 메시지에 정확한 명령 수가 표시되어야 함."""
        from app.schemas.agent_dto import ControlSequence, HardwareDevice, ControlAction

        cmds = [
            ControlSequence(device=HardwareDevice.EXHAUST_FAN, action=ControlAction.ON, description="t1"),
            ControlSequence(device=HardwareDevice.ROOF_VENT, action=ControlAction.OPEN, description="t2"),
        ]
        frames = ModbusTranslator.build_frames(cmds)
        count_msg = next((f for f in frames if "queued" in f), None)
        assert count_msg is not None and "2" in count_msg, f"명령 수(2) 로그 없음: {count_msg}"
