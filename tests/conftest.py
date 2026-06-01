"""
conftest.py — pytest 전역 설정

- sys.path에 프로젝트 루트를 추가하여 `from app.xxx import ...` 가 모든 테스트에서 동작하도록 합니다.
- .env 파일을 로드하여 환경변수를 주입합니다 (API 키 없이도 단위 테스트가 동작하도록 기본값 처리).
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path 맨 앞에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# .env 로드 (없어도 단위 테스트는 동작해야 함)
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# 단위 테스트에서 실제 LLM/DB 호출을 방지하기 위한 환경변수 기본값 설정
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_smartfarm.db")
os.environ.setdefault("GEMINI_API_KEY", "test-key-unit-tests-only")
os.environ.setdefault("SMARTFARM_API_KEY", "test-key-unit-tests-only")
os.environ.setdefault("SMARTFARM_FACILITY_ID", "TEST-FACILITY-001")
