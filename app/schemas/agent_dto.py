from pydantic import BaseModel, Field
from typing import List, Optional

class ChatRequest(BaseModel):
    """
    사용자가 에이전트에게 보내는 질의 모델
    """
    query: str = Field(
        ..., 
        description="사용자의 질문이나 명령", 
        examples=["현재 온실 상태 어때?", "토마토 잎이 노란데 진단해줘."]
    )

class ControlSequence(BaseModel):
    """
    에이전트가 결정한 개별 제어 명령 모델
    """
    device: str = Field(..., description="제어할 장치 이름 (예: window, fan, heater)")
    action: str = Field(..., description="수행할 동작 (예: open, close, turn_on, turn_off)")
    value: Optional[str] = Field(None, description="설정할 값 (예: 25, 100%)")
    description: str = Field(..., description="이 제어 동작을 수행하는 이유에 대한 설명")

class ChatResponse(BaseModel):
    """
    에이전트가 사용자에게 반환하는 최종 응답 모델
    """
    answer: str = Field(..., description="에이전트의 상황 판단 및 최종 답변 텍스트")
    diagnosis: Optional[str] = Field(None, description="YOLO 이미지 병해 진단 결과 (사진 첨부 질의일 경우)")
    control_sequence: Optional[List[ControlSequence]] = Field(
        None, description="생성된 디지털 제어 시퀀스 리스트"
    )
