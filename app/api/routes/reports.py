"""
주간 AI 리포트 생성 및 아카이브 API 라우터.

POST /api/reports/generate  → DB의 7일치 SensorLog를 일별 통계로 집계 후 LLM에 전달하여 마크다운 리포트 생성, WeeklyReport 테이블에 저장
GET  /api/reports           → 저장된 리포트 목록 반환 (최신순)
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from sqlalchemy import select

from app.core.config import settings
from app.database import SessionLocal
from app.models import SensorLog, WeeklyReport

router = APIRouter()


# ──────────────────────────────────────────────
# Pydantic 응답 스키마
# ──────────────────────────────────────────────

class DailyStat(BaseModel):
    date: str
    avg_temp: Optional[float]
    max_temp: Optional[float]
    min_temp: Optional[float]
    avg_humidity: Optional[float]
    avg_co2: Optional[float]
    record_count: int


class WeeklyReportOut(BaseModel):
    id: int
    report_week: str
    report_content: str
    created_at: str


class GenerateReportResponse(BaseModel):
    report_week: str
    report_content: str
    daily_stats: List[DailyStat]


# ──────────────────────────────────────────────
# 내부 유틸리티
# ──────────────────────────────────────────────

def _kst_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=9)))


def _iso_week_label(dt: datetime) -> str:
    """ISO 연도-주차 레이블 반환 (예: 2024-W22)"""
    iso_cal = dt.isocalendar()
    return f"{iso_cal[0]}-W{iso_cal[1]:02d}"


def _fetch_7day_sensor_logs() -> List[SensorLog]:
    """최근 7일 SensorLog 조회"""
    end_dt = _kst_now()
    start_dt = end_dt - timedelta(days=7)
    with SessionLocal() as db:
        stmt = (
            select(SensorLog)
            .where(SensorLog.timestamp >= start_dt)
            .order_by(SensorLog.timestamp.asc())
        )
        return list(db.scalars(stmt).all())


def _aggregate_daily_stats(logs: List[SensorLog]) -> List[DailyStat]:
    """
    토큰 한도 절감을 위해 SensorLog를 날짜별로 그룹화하여
    일별 평균/최고/최저 온습도 통계를 산출합니다.
    """
    grouped: Dict[str, Dict[str, List]] = defaultdict(lambda: {
        "temp": [], "humidity": [], "co2": [], "count": 0
    })

    for log in logs:
        if log.timestamp is None:
            continue
        # timezone-aware datetime → KST 날짜 문자열
        ts = log.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone(timedelta(hours=9)))
        date_key = ts.astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")

        if log.temperature is not None:
            grouped[date_key]["temp"].append(log.temperature)
        if log.humidity is not None:
            grouped[date_key]["humidity"].append(log.humidity)
        if log.co2 is not None:
            grouped[date_key]["co2"].append(log.co2)
        grouped[date_key]["count"] += 1

    daily_stats: List[DailyStat] = []
    for date_str in sorted(grouped.keys()):
        g = grouped[date_str]
        temps = g["temp"]
        hums = g["humidity"]
        co2s = g["co2"]
        daily_stats.append(
            DailyStat(
                date=date_str,
                avg_temp=round(sum(temps) / len(temps), 2) if temps else None,
                max_temp=round(max(temps), 2) if temps else None,
                min_temp=round(min(temps), 2) if temps else None,
                avg_humidity=round(sum(hums) / len(hums), 2) if hums else None,
                avg_co2=round(sum(co2s) / len(co2s), 2) if co2s else None,
                record_count=g["count"],
            )
        )
    return daily_stats


def _build_llm_prompt(daily_stats: List[DailyStat], week_label: str) -> str:
    """일별 통계 데이터를 LLM 프롬프트로 변환"""
    lines = [
        f"# 주간 센서 통계 데이터 ({week_label})\n",
        "| 날짜 | 평균온도(℃) | 최고온도 | 최저온도 | 평균습도(%) | 평균CO2(ppm) | 기록수 |",
        "|------|------------|---------|---------|------------|-------------|------|",
    ]
    for s in daily_stats:
        lines.append(
            f"| {s.date} | {s.avg_temp} | {s.max_temp} | {s.min_temp} "
            f"| {s.avg_humidity} | {s.avg_co2} | {s.record_count} |"
        )

    table_text = "\n".join(lines)

    return (
        "당신은 스마트팜 전문 농업 컨설턴트 AI입니다.\n"
        "아래 일간 통계 데이터를 바탕으로 농장주를 위한 주간 생육 분석 리포트를 마크다운 형식으로 작성하세요.\n\n"
        f"{table_text}\n\n"
        "## 작성 지침\n"
        "1. 리포트 제목: '## 주간 생육 분석 리포트 ({week_label})' 형식 사용\n"
        "2. 구성 섹션:\n"
        "   - 이번 주 환경 요약 (온도·습도·CO2 전반적 평가)\n"
        "   - 일별 이슈 분석 (특이사항이 있는 날짜 중심)\n"
        "   - 생육 적합도 평가 (온도·습도·CO2 각각 점수화)\n"
        "   - 다음 주 재배 관리 권고사항\n"
        "   - 결론\n"
        "3. 전문적이고 친절한 어조로, 마크다운 형식(헤딩, 볼드, 불릿) 사용\n"
        "4. 파이썬 코드, 딕셔너리, 변수명 등 코드 형태 노출 금지\n"
        "5. 데이터가 없는 날짜나 None 값은 '데이터 없음'으로 처리\n\n"
        f"리포트 기간: {week_label}\n"
        "위 지침을 따라 지금 바로 리포트를 작성해 주세요."
    ).replace("{week_label}", week_label)


def _call_gemini_llm(prompt_text: str) -> str:
    """Gemini LLM 호출 (동기)"""
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
        google_api_key=settings.GEMINI_API_KEY,
    )
    template = PromptTemplate.from_template("{input}")
    chain = template | llm
    result = chain.invoke({"input": prompt_text})
    if hasattr(result, "content"):
        return str(result.content).strip()
    return str(result).strip()


# ──────────────────────────────────────────────
# API 엔드포인트
# ──────────────────────────────────────────────

@router.post("/generate", response_model=GenerateReportResponse, summary="주간 AI 리포트 생성")
async def generate_weekly_report():
    """
    최근 7일 SensorLog를 일별 통계로 집계하고 Gemini LLM으로
    마크다운 주간 생육 분석 리포트를 생성한 뒤 DB에 저장합니다.
    """
    # 1. 센서 로그 조회
    try:
        logs = await asyncio.to_thread(_fetch_7day_sensor_logs)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"센서 데이터 조회 실패: {exc}")

    # 2. 일별 통계 집계 (토큰 절감용 전처리)
    daily_stats = _aggregate_daily_stats(logs)
    week_label = _iso_week_label(_kst_now())

    if not daily_stats:
        # 데이터가 없어도 리포트는 생성 (데이터 없음 안내 포함)
        report_content = (
            f"## 주간 생육 분석 리포트 ({week_label})\n\n"
            "> ⚠️ 최근 7일간 수집된 센서 데이터가 없습니다. "
            "데이터 수집 시스템을 확인해 주세요.\n"
        )
    else:
        # 3. LLM 호출하여 리포트 생성
        prompt = _build_llm_prompt(daily_stats, week_label)
        try:
            report_content = await asyncio.to_thread(_call_gemini_llm, prompt)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"LLM 리포트 생성 실패: {exc}")

    # 4. DB에 저장
    try:
        with SessionLocal() as db:
            new_report = WeeklyReport(
                report_week=week_label,
                report_content=report_content,
            )
            db.add(new_report)
            db.commit()
            db.refresh(new_report)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"리포트 DB 저장 실패: {exc}")

    return GenerateReportResponse(
        report_week=week_label,
        report_content=report_content,
        daily_stats=daily_stats,
    )


@router.get("", response_model=List[WeeklyReportOut], summary="주간 리포트 목록 조회")
async def list_weekly_reports():
    """
    DB에 저장된 주간 리포트 목록을 최신순으로 반환합니다.
    """
    try:
        with SessionLocal() as db:
            stmt = select(WeeklyReport).order_by(WeeklyReport.created_at.desc())
            reports = list(db.scalars(stmt).all())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"리포트 목록 조회 실패: {exc}")

    return [
        WeeklyReportOut(
            id=r.id,
            report_week=r.report_week,
            report_content=r.report_content,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in reports
    ]
