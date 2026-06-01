"""
ReportService 스텁 구현.

주간 AI 생육/설비 리포트를 생성하고 배포하는 서비스입니다.
현재는 임포트 오류 방지를 위한 스텁(stub)이며, 실제 기능은 추후 구현됩니다.
"""
from __future__ import annotations

from typing import Dict


class ReportService:
    """주간 리포트 생성 및 배포 서비스 (스텁)"""

    def generate_markdown_reports(self) -> Dict[str, str]:
        """
        최근 7일간의 센서 로그를 기반으로 마크다운 형식의 리포트를 생성합니다.

        Returns:
            dict: {'farm_report': str, 'equipment_report': str}
        """
        farm_report = (
            "# 농업인용 주간 생육 리포트\n\n"
            "> 이 리포트는 자동 생성된 스텁입니다. 실제 데이터 기반 리포트 생성은 추후 구현됩니다.\n\n"
            "## 주간 환경 요약\n\n"
            "| 항목 | 평균값 |\n"
            "|------|--------|\n"
            "| 온도 | - |\n"
            "| 습도 | - |\n"
            "| CO2 | - |\n"
        )
        equipment_report = (
            "# 설비업체용 장비 점검 리포트\n\n"
            "> 이 리포트는 자동 생성된 스텁입니다. 실제 장비 로그 분석은 추후 구현됩니다.\n\n"
            "## 제어 이벤트 요약\n\n"
            "기록된 이벤트가 없습니다.\n"
        )
        return {"farm_report": farm_report, "equipment_report": equipment_report}

    def dispatch_report_via_mcp(self, title: str, content: str) -> None:
        """
        MCP(Message Control Protocol)를 통해 리포트를 배포합니다.
        실제 연동 구현 전 로그만 출력합니다.
        """
        print(f"[ReportService] 리포트 배포 (스텁): {title}")
        print(f"  → 내용 길이: {len(content)}자")
