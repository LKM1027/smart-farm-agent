from pydantic import BaseModel
from typing import Optional

# Java의 RequestDTO와 같은 역할
class ChatRequest(BaseModel):
    message: str
    facility_id: Optional[str] = "PF_0006032_01"  # 기본값 설정

# Java의 ResponseDTO와 같은 역할
class ChatResponse(BaseModel):
    answer: str
    status: str = "success"