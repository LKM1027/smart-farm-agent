from fastapi import APIRouter
from app.schemas.agent_dto import ChatRequest, AgentFinalResponse, Intents
from app.services.agent_service import AgentService

router = APIRouter()

@router.post("/chat", response_model=AgentFinalResponse)
async def chat_with_agent(request: ChatRequest):
    """
    사용자의 질의를 받아 LangGraph 에이전트를 통해 상황을 판단하고 
    각 단계별 메타데이터와 제어 시퀀스를 포함한 통합 응답을 반환합니다.
    """
    # 서비스 레이어를 호출하여 LangGraph 워크플로우 실행
    final_state = await AgentService.execute_chat(request.query)
    
    # generate_answer 노드에서 패킹한 최종 응답 객체를 바로 반환
    if "final_response" in final_state and final_state["final_response"] is not None:
        return final_state["final_response"]
        
    # 예외 상황 처리 (그래프가 정상적으로 끝까지 도달하지 못한 경우)
    return AgentFinalResponse(
        intents=Intents(is_sensor_needed=False, is_rag_needed=False),
        sensor_data=None,
        control_sequence=None,
        answer="에이전트 처리 중 내부 오류가 발생했습니다. (final_response 객체 누락)"
    )
