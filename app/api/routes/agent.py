from fastapi import APIRouter
from app.schemas.agent_dto import ChatRequest
from app.services.agent_service import AgentService

router = APIRouter()

@router.post("/chat")
async def chat_with_agent(request: ChatRequest):
    """
    사용자의 질의를 받아 LangGraph 에이전트를 통해 상황을 판단하고 
    각 단계별 메타데이터와 제어 시퀀스를 포함한 통합 응답을 반환합니다.
    """
    # 서비스 레이어를 호출하여 LangGraph 워크플로우 실행
    final_state = await AgentService.execute_chat(request.query)
    
    # final_state에서 값을 안전하게 추출하여 순수 딕셔너리로 반환
    return {
        "intents": {
            "is_sensor_needed": final_state.get("is_sensor_needed", False),
            "is_rag_needed": final_state.get("is_rag_needed", False)
        },
        "sensor_data": final_state.get("sensor_data"),
        "control_sequence": final_state.get("control_sequence", []),
        "answer": final_state.get("answer", ""),
        "modbus_frames": final_state.get("modbus_frames")
    }