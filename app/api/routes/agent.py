from fastapi import APIRouter
from app.schemas.agent_dto import ChatRequest, ChatResponse
from app.services.agent_service import AgentService

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    사용자의 질의를 받아 LangGraph 에이전트를 통해 상황을 판단하고 
    제어 시퀀스를 포함한 응답을 반환합니다.
    """
    # 서비스 레이어를 호출하여 LangGraph 워크플로우 실행
    final_state = AgentService.execute_chat(request.query)
    
    # 상태(State) 딕셔너리에서 필요한 값을 추출하여 DTO(Response Model)로 변환
    response = ChatResponse(
        answer=final_state.get("answer") or "응답을 생성하지 못했습니다.",
        diagnosis=final_state.get("diagnosis"),
        control_sequence=final_state.get("control_sequence") or []
    )
    
    return response
