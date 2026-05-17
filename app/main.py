from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import agent

def get_application() -> FastAPI:
    # FastAPI 인스턴스 생성
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        description="Smart Farm Autonomous Agent API",
    )

    # CORS 미들웨어 설정 (웹 프론트엔드 연동 지원)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # 개발 편의를 위해 전체 허용. 운영 시 프론트엔드 도메인으로 제한해야 합니다.
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API 라우터 등록
    app.include_router(agent.router, prefix=f"{settings.API_V1_STR}/agent", tags=["Agent"])

    return app

app = get_application()

@app.get("/", tags=["Health Check"])
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}