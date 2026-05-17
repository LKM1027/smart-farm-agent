from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from app.agent.nodes import analyze_query, fetch_sensor_data_node, diagnose_crop, retrieve_knowledge, generate_answer

class AgentState(TypedDict):
    """
    에이전트가 실행되는 동안 각 노드가 공유하고 수정할 상태(State)입니다.
    """
    query: str
    sensor_data: Optional[Dict[str, Any]]
    diagnosis: Optional[str]
    retrieved_docs: List[str]  # RAG를 통해 검색된 지식 문서 리스트
    control_sequence: Optional[List[Dict[str, Any]]]
    answer: Optional[str]
    is_sensor_needed: bool  # 센서 데이터 조회 필요 여부를 결정하는 라우팅 변수
    is_vision_needed: bool  # 비전 진단 필요 여부를 결정하는 라우팅 변수

def analyze_router(state: AgentState) -> str:
    """
    상태의 is_sensor_needed 와 is_vision_needed 값에 따라 다음 경로를 결정하는 라우팅 함수입니다.
    """
    if state.get("is_sensor_needed"):
        print("[Router] 판단: 센서 데이터 조회가 필요합니다. -> fetch_sensor_data_node")
        return "fetch_sensor_data_node"
    elif state.get("is_vision_needed"):
        print("[Router] 판단: 비전 진단이 필요합니다. -> diagnose_crop")
        return "diagnose_crop"
    else:
        print("[Router] 판단: 추가 조회가 불필요합니다. -> retrieve_knowledge")
        return "retrieve_knowledge"

def sensor_router(state: AgentState) -> str:
    """
    센서 데이터 조회 후, 비전 진단이 필요한지 확인하는 라우팅 함수입니다.
    """
    if state.get("is_vision_needed"):
        print("[Router] 판단: 센서 조회 완료. 비전 진단이 추가로 필요합니다. -> diagnose_crop")
        return "diagnose_crop"
    else:
        print("[Router] 판단: 센서 조회 완료. 비전 진단은 불필요합니다. -> retrieve_knowledge")
        return "retrieve_knowledge"

# 상태 그래프(StateGraph) 초기화
workflow = StateGraph(AgentState)

# 노드(Node) 추가
workflow.add_node("analyze_query", analyze_query)
workflow.add_node("fetch_sensor_data_node", fetch_sensor_data_node)
workflow.add_node("diagnose_crop", diagnose_crop)
workflow.add_node("retrieve_knowledge", retrieve_knowledge)
workflow.add_node("generate_answer", generate_answer)

# 엣지(Edge) 연결
# 1. 시작점 -> 의도 분석
workflow.add_edge(START, "analyze_query")

# 2. 의도 분석 -> (라우팅) -> 센서 데이터 조회 OR 비전 진단 OR 지식 검색
workflow.add_conditional_edges(
    "analyze_query",
    analyze_router,
    {
        "fetch_sensor_data_node": "fetch_sensor_data_node",
        "diagnose_crop": "diagnose_crop",
        "retrieve_knowledge": "retrieve_knowledge"
    }
)

# 3. 센서 데이터 조회 완료 시 -> (라우팅) -> 비전 진단 OR 지식 검색
workflow.add_conditional_edges(
    "fetch_sensor_data_node",
    sensor_router,
    {
        "diagnose_crop": "diagnose_crop",
        "retrieve_knowledge": "retrieve_knowledge"
    }
)

# 4. 비전 진단 완료 시 -> 지식 검색으로 이동
workflow.add_edge("diagnose_crop", "retrieve_knowledge")

# 5. 지식 검색 완료 시 -> 답변 생성으로 이동
workflow.add_edge("retrieve_knowledge", "generate_answer")

# 6. 답변 생성이 끝나면 전체 워크플로우 종료
workflow.add_edge("generate_answer", END)

# 그래프 컴파일
agent_graph = workflow.compile()
