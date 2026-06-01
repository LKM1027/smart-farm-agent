from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import Column, Integer, Float, Boolean, String, DateTime, JSON, Text
from sqlalchemy.orm import declarative_base

from app.database import Base


def now_kst() -> datetime:
    """Return current time in KST (UTC+9) as timezone-aware datetime."""
    return datetime.now(timezone(timedelta(hours=9)))


class SensorLog(Base):
    __tablename__ = "sensor_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=now_kst)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    co2 = Column(Integer, nullable=True)
    is_fallback = Column(Boolean, nullable=False, default=False)
    raw_response = Column(JSON, nullable=True)


class ControlLog(Base):
    __tablename__ = "control_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=now_kst)
    device_code = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False)
    hex_frame = Column(String(256), nullable=True)
    reason = Column(String(1024), nullable=True)


class WeeklyReport(Base):
    """주간 AI 생육 분석 리포트를 저장하는 테이블."""
    __tablename__ = "weekly_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_week = Column(String(32), nullable=False, comment="리포트 대상 주차 (예: 2024-W22)")
    report_content = Column(Text, nullable=False, comment="마크다운 형식의 리포트 본문")
    created_at = Column(DateTime(timezone=True), nullable=False, default=now_kst)
