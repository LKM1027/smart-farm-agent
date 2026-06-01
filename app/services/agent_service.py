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
        initial_state = {
            "query": query,
            "sensor_data": None,
            "retrieved_docs": [],
            "control_sequence": None,
            "answer": None,
            "is_sensor_needed": False,
            "is_unsupported_crop": False,
        }

        # LangGraph 비동기 invoke() 실행
        final_state = await agent_graph.ainvoke(initial_state)

        return final_state

    @staticmethod
    async def execute_system_alert(query: str, sensor_data: dict) -> dict:
        """
        시스템 자동 알림에서 호출하는 LangGraph 에이전트 실행 메서드.
        이미 수집된 sensor_data 를 초기 상태에 주입합니다.
        """
        initial_state = {
            "query": query,
            "sensor_data": sensor_data,
            "retrieved_docs": [],
            "control_sequence": None,
            "answer": None,
            "is_sensor_needed": False,   # 이미 sensor_data 가 주입되어 있으므로 False
            "is_unsupported_crop": False,
        }

        return await agent_graph.ainvoke(initial_state)
