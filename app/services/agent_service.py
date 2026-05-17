from app.agent.graph import agent_graph

class AgentService:
    """
    API 컨트롤러와 LangGraph 에이전트 간의 브릿지 역할을 하는 서비스 레이어
    """
    @staticmethod
    def execute_chat(query: str) -> dict:
        """
        사용자 질의를 받아 LangGraph 에이전트 워크플로우를 실행하고 결과를 반환합니다.
        """
        # 초기 상태 정의
        initial_state = {
            "query": query,
            "sensor_data": {},
            "diagnosis": None,
            "control_sequence": [],
            "answer": None
        }
        
        # LangGraph invoke() 실행
        final_state = agent_graph.invoke(initial_state)
        
        return final_state
