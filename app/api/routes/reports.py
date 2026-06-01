from fastapi import APIRouter

router = APIRouter()

@router.get("/weekly", tags=["Weekly Reports"])
async def get_weekly_reports():
    """
    주간 리포트 목록을 반환하는 엔드포인트 (스텁).
    실제 구현 시 DB에서 WeeklyReport 레코드를 조회하여 반환합니다.
    """
    return {"reports": [], "message": "주간 리포트 기능이 준비 중입니다."}
