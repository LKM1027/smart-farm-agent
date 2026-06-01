from fastapi import APIRouter
from app.schemas.agent_dto import ChatRequest, ChatResponse, ControlSequence
from app.services.agent_service import AgentService
from typing import List, Optional

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    사용자의 질의를 받아 LangGraph 에이전트를 통해 상황을 판단하고
    각 단계별 메타데이터와 제어 시퀀스를 포함한 통합 응답을 반환합니다.
    """
    # 서비스 레이어를 호출하여 LangGraph 워크플로우 실행
    final_state = await AgentService.execute_chat(request.query)

    # 그래프 최종 상태에서 answer / control_sequence 를 직접 추출하여 ChatResponse 로 패킹
    answer: str = final_state.get("answer") or "에이전트 처리 중 내부 오류가 발생했습니다."
    raw_controls = final_state.get("control_sequence") or []

    # nodes.py 의 ControlCommand dict → ChatResponse 의 ControlSequence Pydantic 모델 변환
    control_sequence: Optional[List[ControlSequence]] = None
    if raw_controls:
        mapped = []
        for cmd in raw_controls:
            mapped.append(ControlSequence(
                device=cmd.get("target", cmd.get("device", "unknown")),
                action=cmd.get("action", ""),
                value=cmd.get("value"),
                description=cmd.get("reason", cmd.get("description", "")),
            ))
        control_sequence = mapped if mapped else None

    return ChatResponse(
        answer=answer,
        diagnosis=None,       # 비전 진단 기능은 현재 미사용
        control_sequence=control_sequence,
    )
