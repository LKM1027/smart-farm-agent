from app.agent.graph import agent_graph

class AgentService:
    """
    API 컨트롤러와 LangGraph 에이전트 간의 브릿지 역할을 하는 서비스 레이어
    """
    @staticmethod
    async def execute_chat(query: str) -> dict:
        """
        사용자 질의를 받아 LangGraph 에이전트 워크플로우를 실행하고 결과를 반환합니다.
        """
        # 초기 상태 정의
        initial_state = {
            "query": query,
            "sensor_data": None,
            "control_sequence": None,
            "answer": None,
            "intents": {
                "is_sensor_needed": False,
                "is_rag_needed": False
            }
        }
        
        # LangGraph 비동기 invoke() 실행
        final_state = await agent_graph.ainvoke(initial_state)
        
        return final_state

    @staticmethod
    async def execute_system_alert(query: str, sensor_data: dict) -> dict:
        """
        Invoke the LangGraph agent from a system-triggered alert without user input.
        """
        initial_state = {
            "query": query,
            "sensor_data": sensor_data,
            "control_sequence": None,
            "answer": None,
            "system_triggered": True,
            "intents": {
                "is_sensor_needed": False,
                "is_rag_needed": True,
            },
        }

        return await agent_graph.ainvoke(initial_state)
