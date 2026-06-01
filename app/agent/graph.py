from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from app.agent.nodes import analyze_query, fetch_sensor_data_node, retrieve_knowledge, generate_answer

class AgentState(TypedDict):
    """
    에이전트가 실행되는 동안 각 노드가 공유하고 수정할 상태(State)입니다.
    """
    query: str
    sensor_data: Optional[Dict[str, Any]]
    retrieved_docs: List[str]  # RAG를 통해 검색된 지식 문서 리스트
    control_sequence: Optional[List[Dict[str, Any]]]
    answer: Optional[str]
    
    # 의도 파악 플래그
    intents: Dict[str, bool]
    is_sensor_needed: bool
    is_rag_needed: bool
    
    # UI 시각화를 위해 반환될 최종 패킹된 응답
    final_response: Any

def rag_router(state: AgentState) -> str:
    """
    is_rag_needed 값에 따라 RAG 노드를 거칠지 바로 답변 노드로 갈지 결정합니다.
    """
    if state.get("is_rag_needed"):
        print("[Router] 판단: RAG 지식 검색이 필요합니다. -> retrieve_knowledge")
        return "retrieve_knowledge"
    else:
        print("[Router] 판단: RAG 지식 검색은 불필요합니다. -> generate_answer")
        return "generate_answer"

def analyze_router(state: AgentState) -> str:
    """
    상태의 is_sensor_needed 값에 따라 다음 경로를 결정하는 라우팅 함수입니다.
    """
    if state.get("is_sensor_needed"):
        print("[Router] 판단: 센서 데이터 조회가 필요합니다. -> fetch_sensor_data_node")
        return "fetch_sensor_data_node"
    else:
        return rag_router(state)

def sensor_router(state: AgentState) -> str:
    """
    센서 데이터 조회 후 다음 경로를 결정하는 라우팅 함수입니다.
    """
    return rag_router(state)

# 상태 그래프(StateGraph) 초기화
workflow = StateGraph(AgentState)

# 노드(Node) 추가
workflow.add_node("analyze_query", analyze_query)
workflow.add_node("fetch_sensor_data_node", fetch_sensor_data_node)
workflow.add_node("retrieve_knowledge", retrieve_knowledge)
workflow.add_node("generate_answer", generate_answer)

# 엣지(Edge) 연결
# 1. 시작점 -> 의도 분석
workflow.add_edge(START, "analyze_query")

# 2. 의도 분석 -> (라우팅) -> 센서 데이터 조회 OR 지식 검색 OR 답변 생성
workflow.add_conditional_edges(
    "analyze_query",
    analyze_router,
    {
        "fetch_sensor_data_node": "fetch_sensor_data_node",
        "retrieve_knowledge": "retrieve_knowledge",
        "generate_answer": "generate_answer"
    }
)

# 3. 센서 데이터 조회 완료 시 -> (라우팅) -> 지식 검색 OR 답변 생성
workflow.add_conditional_edges(
    "fetch_sensor_data_node",
    sensor_router,
    {
        "retrieve_knowledge": "retrieve_knowledge",
        "generate_answer": "generate_answer"
    }
)

# 5. 지식 검색 완료 시 -> 답변 생성으로 이동
workflow.add_edge("retrieve_knowledge", "generate_answer")

# 6. 답변 생성이 끝나면 전체 워크플로우 종료
workflow.add_edge("generate_answer", END)

# 그래프 컴파일
agent_graph = workflow.compile()
