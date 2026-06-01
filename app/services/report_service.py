from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.database import SessionLocal
from app.models import SensorLog, ControlLog
from app.services.rag_service import RagService
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI


class ReportService:
    """주간 리포트 생성을 위한 서비스 레이어."""

    def __init__(self) -> None:
        self.rag_service = RagService()

    @staticmethod
    def _kst_now() -> datetime:
        return datetime.now(timezone(timedelta(hours=9)))

    def _weekly_window(self) -> tuple[datetime, datetime]:
        end_date = self._kst_now()
        start_date = end_date - timedelta(days=7)
        return start_date, end_date

    def fetch_weekly_logs(self) -> Dict[str, Any]:
        start_date, end_date = self._weekly_window()

        sensor_logs: List[SensorLog] = []
        control_logs: List[ControlLog] = []

        try:
            with SessionLocal() as db:
                sensor_stmt = select(SensorLog).where(SensorLog.timestamp >= start_date)
                control_stmt = select(ControlLog).where(ControlLog.timestamp >= start_date)

                sensor_logs = db.scalars(sensor_stmt).all()
                control_logs = db.scalars(control_stmt).all()
        except SQLAlchemyError as error:
            print(f"[ReportService] DB 조회 오류: {error}")

        return {
            "sensor_logs": sensor_logs,
            "control_logs": control_logs,
            "start_date": start_date,
            "end_date": end_date,
        }

    def _aggregate_sensor_summary(self, sensor_logs: List[SensorLog]) -> Dict[str, Any]:
        if not sensor_logs:
            return {
                "average_temperature": None,
                "max_temperature": None,
                "min_temperature": None,
                "average_humidity": None,
                "average_co2": None,
                "fallback_count": 0,
                "record_count": 0,
            }

        temperatures = [log.temperature for log in sensor_logs if log.temperature is not None]
        humidities = [log.humidity for log in sensor_logs if log.humidity is not None]
        co2_values = [log.co2 for log in sensor_logs if log.co2 is not None]
        fallback_count = sum(1 for log in sensor_logs if log.is_fallback)

        return {
            "average_temperature": round(sum(temperatures) / len(temperatures), 2) if temperatures else None,
            "max_temperature": round(max(temperatures), 2) if temperatures else None,
            "min_temperature": round(min(temperatures), 2) if temperatures else None,
            "average_humidity": round(sum(humidities) / len(humidities), 2) if humidities else None,
            "average_co2": round(sum(co2_values) / len(co2_values), 2) if co2_values else None,
            "fallback_count": fallback_count,
            "record_count": len(sensor_logs),
        }

    def _aggregate_control_summary(self, control_logs: List[ControlLog]) -> Dict[str, Any]:
        device_usage: Dict[str, int] = {}
        for log in control_logs:
            key = log.device_code or "UNKNOWN"
            device_usage[key] = device_usage.get(key, 0) + 1

        return {
            "total_control_commands": len(control_logs),
            "device_usage_counts": device_usage,
        }

    def _build_context_summary(self, aggregated_data: Dict[str, Any]) -> str:
        sensor_summary = aggregated_data["sensor_summary"]
        control_summary = aggregated_data["control_summary"]

        return (
            f"[기간] {aggregated_data['start_date'].strftime('%Y-%m-%d %H:%M')} ~ "
            f"{aggregated_data['end_date'].strftime('%Y-%m-%d %H:%M')} (KST)\n"
            f"- 센서 기록 건수: {sensor_summary['record_count']}\n"
            f"- 평균 온도: {sensor_summary['average_temperature']}℃\n"
            f"- 최고 온도: {sensor_summary['max_temperature']}℃\n"
            f"- 최저 온도: {sensor_summary['min_temperature']}℃\n"
            f"- 평균 습도: {sensor_summary['average_humidity']}%\n"
            f"- 평균 CO2: {sensor_summary['average_co2']} ppm\n"
            f"- Fallback 발생 횟수: {sensor_summary['fallback_count']}회\n"
            f"- 총 제어 명령 수: {control_summary['total_control_commands']}\n"
            f"- 장치별 제어 횟수: {control_summary['device_usage_counts']}\n"
        )

    def compile_weekly_statistics(self) -> Dict[str, Any]:
        weekly_data = self.fetch_weekly_logs()
        sensor_summary = self._aggregate_sensor_summary(weekly_data["sensor_logs"])
        control_summary = self._aggregate_control_summary(weekly_data["control_logs"])

        return {
            "start_date": weekly_data["start_date"],
            "end_date": weekly_data["end_date"],
            "sensor_summary": sensor_summary,
            "control_summary": control_summary,
        }

    def _render_farm_report(self, stats: Dict[str, Any], docs: List[str]) -> str:
        sensor_summary = stats["sensor_summary"]
        control_summary = stats["control_summary"]
        guidance = "\n".join(f"- {doc}" for doc in docs) if docs else "관련 가이드라인이 로드되지 않았습니다."

        return (
            "# 농업인용 생육 리포트\n"
            "## 1. 요약\n"
            f"- 리포트 기간: {stats['start_date'].strftime('%Y-%m-%d')} ~ {stats['end_date'].strftime('%Y-%m-%d')}\n"
            f"- 평균 온도: {sensor_summary['average_temperature']}℃\n"
            f"- 최고 온도: {sensor_summary['max_temperature']}℃\n"
            f"- 최저 온도: {sensor_summary['min_temperature']}℃\n"
            f"- 평균 습도: {sensor_summary['average_humidity']}%\n"
            f"- 평균 CO2: {sensor_summary['average_co2']} ppm\n"
            f"- 통신 이상(Fallback) 횟수: {sensor_summary['fallback_count']}회\n"
            "\n"
            "## 2. 생육 환경 적합도 평가\n"
            f"- 온도 적합도: {self._score_temperature(sensor_summary['average_temperature'])}/100\n"
            f"- 습도 적합도: {self._score_humidity(sensor_summary['average_humidity'])}/100\n"
            f"- CO2 적합도: {self._score_co2(sensor_summary['average_co2'])}/100\n"
            "\n"
            "## 3. 다음 주 재배 관리 가이드\n"
            f"{self._build_growth_guidance(sensor_summary)}\n"
            "\n"
            "## 4. 이상 기후 대응책\n"
            f"{self._build_climate_adaptation(sensor_summary)}\n"
            "\n"
            "## 5. 참고 가이드라인\n"
            f"{guidance}\n"
        )

    def _render_farm_report(self, stats: Dict[str, Any], docs: List[str]) -> str:
        prompt_text = self._build_report_prompt(
            report_title="농업인용 생육 리포트",
            report_purpose=(
                "제공된 환경 센서 통계와 농진청 가이드(RAG)를 바탕으로, 이번 주 작물 생육 상태를 평가하고 "
                "온도/습도/CO2 관리에 대한 조언을 작성해 주세요. 전문적이고 친절한 농업 컨설턴트 톤으로 작성하며, "
                "절대 파이썬 코드나 딕셔너리 형태를 노출하지 않아야 합니다."
            ),
            stats=stats,
            docs=docs,
        )

        return self._invoke_gemini_report(prompt_text)

    def _render_equipment_report(self, stats: Dict[str, Any], docs: List[str]) -> str:
        prompt_text = self._build_report_prompt(
            report_title="설비업체용 장비 점검 리포트",
            report_purpose=(
                "제공된 장비 제어 횟수(Modbus 로그)를 분석하여 각 장비(펌프, 밸브 등)의 스트레스 지수와 "
                "유지보수 필요성을 평가해 주세요. 산업용 장비 점검 보고서 톤으로 작성하며, "
                "절대 파이썬 코드나 딕셔너리 형태를 노출하지 않아야 합니다."
            ),
            stats=stats,
            docs=docs,
        )

        return self._invoke_gemini_report(prompt_text)

    def _get_gemini_llm(self, temperature: float = 0.2) -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=temperature,
            google_api_key=settings.GEMINI_API_KEY,
        )

    def _format_stats_for_prompt(self, stats: Dict[str, Any]) -> str:
        sensor_summary = stats["sensor_summary"]
        control_summary = stats["control_summary"]
        device_entries = control_summary.get("device_usage_counts", {})

        device_lines = []
        for device, count in device_entries.items():
            device_lines.append(f"  - {device}: {count}회")

        return (
            f"- 리포트 기간: {stats['start_date'].strftime('%Y-%m-%d')} ~ {stats['end_date'].strftime('%Y-%m-%d')}\n"
            f"- 센서 기록 건수: {sensor_summary['record_count']}\n"
            f"- 평균 온도: {sensor_summary['average_temperature']}℃\n"
            f"- 최고 온도: {sensor_summary['max_temperature']}℃\n"
            f"- 최저 온도: {sensor_summary['min_temperature']}℃\n"
            f"- 평균 습도: {sensor_summary['average_humidity']}%\n"
            f"- 평균 CO2: {sensor_summary['average_co2']} ppm\n"
            f"- Fallback 발생 횟수: {sensor_summary['fallback_count']}회\n"
            f"- 총 제어 명령 수: {control_summary['total_control_commands']}\n"
            f"- 장치별 제어 횟수:\n{''.join(device_lines) if device_lines else '  - 없음'}"
        )

    def _build_docs_context(self, docs: List[str]) -> str:
        if not docs:
            return "관련 문서가 없습니다."

        doc_chunks: List[str] = []
        for idx, doc in enumerate(docs, start=1):
            cleaned = " ".join(str(doc).split())
            doc_chunks.append(f"문서 {idx}: {cleaned}")

        return "\n".join(doc_chunks)

    def _build_report_prompt(
        self,
        report_title: str,
        report_purpose: str,
        stats: Dict[str, Any],
        docs: List[str],
    ) -> str:
        return (
            f"당신은 스마트팜 리포트 생성 전문가입니다. 아래 지침을 строго 준수하고, 출력 내용은 반드시 마크다운 형식으로 작성하세요. "
            f"응답에는 절대 파이썬 코드, 딕셔너리, 변수명, 또는 코드 블록을 포함하지 마십시오. 문장을 완결형으로 작성하고 중간에 끊기지 않도록 하세요.\n\n"
            f"=== 리포트 유형 ===\n{report_title}\n\n"
            f"=== 작성 목적 ===\n{report_purpose}\n\n"
            f"=== 제공 데이터 ===\n{self._format_stats_for_prompt(stats)}\n\n"
            f"=== 참조 문서 요약 ===\n{self._build_docs_context(docs)}\n\n"
            f"위 정보를 바탕으로, {report_title}를 다음 구조로 작성하세요.\n"
            "1. 요약\n"
            "2. 주요 분석 결과\n"
            "3. 권장 관리 또는 유지보수 조치\n"
            "4. 결론 및 다음 주 권장 사항\n"
        )

    def _invoke_gemini_report(self, prompt_text: str) -> str:
        try:
            llm = self._get_gemini_llm()
            prompt = PromptTemplate.from_template("{input}")
            chain = prompt | llm
            result = chain.invoke({"input": prompt_text})

            if hasattr(result, "content"):
                return str(result.content).strip()
            if hasattr(result, "generations"):
                generations = getattr(result, "generations")
                if generations and len(generations) > 0 and len(generations[0]) > 0:
                    candidate = generations[0][0]
                    if hasattr(candidate, "text"):
                        return str(candidate.text).strip()
            return str(result).strip()
        except Exception as error:
            print(f"[ReportService] Gemini 호출 실패: {error}")
            return self._build_fallback_report(prompt_text)

    def _build_fallback_report(self, prompt_text: str) -> str:
        return (
            "# 리포트 생성 오류 안내\n"
            "LLM 연결에 실패하여 자동 생성 리포트를 제공할 수 없습니다.\n"
            "잠시 후 다시 시도해 주세요.\n"
        )

    @staticmethod
    def _score_temperature(value: Optional[float]) -> int:
        if value is None:
            return 50
        if 20 <= value <= 25:
            return 95
        if value < 20:
            return max(0, 95 - int((20 - value) * 3))
        return max(0, 95 - int((value - 25) * 4))

    @staticmethod
    def _score_humidity(value: Optional[float]) -> int:
        if value is None:
            return 50
        if 60 <= value <= 80:
            return 90
        if value < 60:
            return max(0, 90 - int((60 - value) * 2))
        return max(0, 90 - int((value - 80) * 2))

    @staticmethod
    def _score_co2(value: Optional[float]) -> int:
        if value is None:
            return 50
        if 400 <= value <= 800:
            return 90
        if value < 400:
            return max(0, 90 - int((400 - value) * 1))
        return max(0, 90 - int((value - 800) * 1))

    @staticmethod
    def _build_growth_guidance(sensor_summary: Dict[str, Any]) -> str:
        if sensor_summary["average_temperature"] is None:
            return "데이터가 부족하여 다음 주 관리 가이드를 생성할 수 없습니다."

        lines: List[str] = []
        avg_temp = sensor_summary["average_temperature"]
        avg_hum = sensor_summary["average_humidity"]
        avg_co2 = sensor_summary["average_co2"]

        if avg_temp < 20:
            lines.append("온도가 낮아지는 추세가 있으므로 난방을 보강하고 보온커튼을 점검하세요.")
        elif avg_temp > 25:
            lines.append("온도가 높으므로 환기와 차광막 조절을 통해 과열을 방지하세요.")
        else:
            lines.append("온도는 현재 적정 범위에 있으며, 유지 관리를 지속하세요.")

        if avg_hum is not None:
            if avg_hum < 60:
                lines.append("습도가 낮아져 잎 마름 및 수분 스트레스가 발생할 수 있으니 가습 또는 관수를 고려하세요.")
            elif avg_hum > 80:
                lines.append("습도가 높아 곰팡이 위험이 있으므로 환기 및 제습을 강화하세요.")
            else:
                lines.append("습도는 양호하므로 현 수준을 유지하세요.")

        if avg_co2 is not None:
            if avg_co2 < 400:
                lines.append("CO2가 낮아 광합성이 둔화될 수 있으므로 추가 CO2 공급을 검토하세요.")
            elif avg_co2 > 800:
                lines.append("CO2가 높아질 경우 환기를 통해 적정 수준으로 유지하세요.")
            else:
                lines.append("CO2 수준은 적정 범위에 있습니다.")

        return "\n".join(lines)

    @staticmethod
    def _build_climate_adaptation(sensor_summary: Dict[str, Any]) -> str:
        return (
            "- 저온/고온 기상 조건에는 가온 및 차광 시스템을 교차 활용하세요.\n"
            "- 강풍이나 폭우가 예보된 경우에는 천창과 차광막을 미리 닫아 시설 보호를 준비하세요.\n"
            "- 급격한 CO2 변화 시에는 환풍기와 압력 밸브 상태를 점검하세요."
        )

    @staticmethod
    def _calculate_equipment_stress(control_summary: Dict[str, Any]) -> str:
        total = control_summary.get("total_control_commands", 0)
        if total == 0:
            return "낮음"
        if total < 10:
            return "보통"
        if total < 25:
            return "다소 높음"
        return "높음"

    @staticmethod
    def _build_relay_maintenance(control_summary: Dict[str, Any]) -> str:
        device_entries = control_summary.get("device_usage_counts", {})
        lines: List[str] = []
        for device, count in device_entries.items():
            lines.append(f"- {device}: 약 {count}회 제어 이력. 릴레이 접점 마모를 고려하여 연 1회 이상 점검하세요.")
        if not lines:
            lines.append("- 최근 제어 로그가 없으므로 릴레이 점검 주기를 재평가하세요.")
        return "\n".join(lines)

    def generate_markdown_reports(self) -> Dict[str, str]:
        stats = self.compile_weekly_statistics()
        farm_docs = self.rag_service.retrieve_docs("토마토 생육 가이드라인")
        equipment_docs = self.rag_service.retrieve_docs("Modbus 통신 안정성 및 장비 점검")

        farm_report = self._render_farm_report(stats, farm_docs)
        equipment_report = self._render_equipment_report(stats, equipment_docs)

        return {
            "farm_report": farm_report,
            "equipment_report": equipment_report,
        }

    def dispatch_report_via_mcp(self, report_subject: str, report_markdown: str) -> Dict[str, Any]:
        """MCP 메시지 발송 모크업. 실제 확장이 가능한 구조로 설계."""
        payload = {
            "subject": report_subject,
            "message": report_markdown,
            "timestamp": self._kst_now().isoformat(),
            "destination": "MCP-EXTENSION-PLACEHOLDER",
            "status": "queued",
        }

        print(f"[ReportService] MCP 발송 큐에 추가: {report_subject}")
        return payload
