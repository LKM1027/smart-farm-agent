from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from app.agent.nodes import (
    check_supported_crop,
    analyze_query,
    fetch_sensor_data_node,
    retrieve_knowledge,
    generate_answer,
)

class AgentState(TypedDict):
    """
    에이전트가 실행되는 동안 각 노드가 공유하고 수정할 상태(State)입니다.
    """
    query: str
    sensor_data: Optional[Dict[str, Any]]
    retrieved_docs: List[str]       # RAG를 통해 검색된 지식 문서 리스트
    control_sequence: Optional[List[Dict[str, Any]]]
    answer: Optional[str]

    # 의도 파악 플래그
    is_sensor_needed: bool

    # 미지원 작물 가드레일 플래그
    is_unsupported_crop: bool


# ─────────────────────────────────────────────
# 라우터: 가드레일 → 지원 작물 여부 분기
# ─────────────────────────────────────────────
def crop_guard_router(state: AgentState) -> str:
    """
    미지원 작물이 감지된 경우 즉시 답변 생성을 건너뛰고 종료합니다.
    지원 작물이면 의도 분석으로 진행합니다.
    """
    if state.get("is_unsupported_crop"):
        print("[Router] ⛔ 미지원 작물 감지 → END (가드레일 응답 반환)")
        return "end_with_guardrail"
    print("[Router] ✅ 지원 작물 → analyze_query")
    return "analyze_query"


# ─────────────────────────────────────────────
# 라우터: 의도 분석 → 센서 조회 여부 분기
# ─────────────────────────────────────────────
def analyze_router(state: AgentState) -> str:
    """
    is_sensor_needed 값에 따라 센서 조회 → RAG → 답변 경로를 결정합니다.
    """
    if state.get("is_sensor_needed"):
        print("[Router] 판단: 센서 데이터 조회가 필요합니다. → fetch_sensor_data_node")
        return "fetch_sensor_data_node"
    print("[Router] 판단: 센서 조회 불필요 → retrieve_knowledge")
    return "retrieve_knowledge"


# ─────────────────────────────────────────────
# 가드레일 종료 노드 (미지원 작물 응답 패스스루)
# ─────────────────────────────────────────────
def guardrail_response_node(state: AgentState) -> dict:
    """
    미지원 작물 가드레일 발동 시 check_supported_crop 에서 기록된
    answer / control_sequence 를 그대로 유지하며 그래프를 종료합니다.
    """
    print("[Node: guardrail_response_node] 가드레일 응답 반환 후 종료")
    return {}


# ─────────────────────────────────────────────
# 그래프 구성
# ─────────────────────────────────────────────
workflow = StateGraph(AgentState)

# 노드 등록
workflow.add_node("check_supported_crop", check_supported_crop)
workflow.add_node("guardrail_response_node", guardrail_response_node)
workflow.add_node("analyze_query", analyze_query)
workflow.add_node("fetch_sensor_data_node", fetch_sensor_data_node)
workflow.add_node("retrieve_knowledge", retrieve_knowledge)
workflow.add_node("generate_answer", generate_answer)

# 엣지 연결
# 1. START → 작물 지원 여부 가드레일
workflow.add_edge(START, "check_supported_crop")

# 2. 가드레일 → 미지원이면 guardrail_response_node, 지원이면 analyze_query
workflow.add_conditional_edges(
    "check_supported_crop",
    crop_guard_router,
    {
        "end_with_guardrail": "guardrail_response_node",
        "analyze_query": "analyze_query",
    }
)

# 3. 가드레일 응답 → END
workflow.add_edge("guardrail_response_node", END)

# 4. 의도 분석 → 센서 조회 OR RAG
workflow.add_conditional_edges(
    "analyze_query",
    analyze_router,
    {
        "fetch_sensor_data_node": "fetch_sensor_data_node",
        "retrieve_knowledge": "retrieve_knowledge",
    }
)

# 5. 센서 조회 완료 → RAG
workflow.add_edge("fetch_sensor_data_node", "retrieve_knowledge")

# 6. RAG 완료 → 답변 생성
workflow.add_edge("retrieve_knowledge", "generate_answer")

# 7. 답변 생성 → END
workflow.add_edge("generate_answer", END)

# 그래프 컴파일
agent_graph = workflow.compile()
