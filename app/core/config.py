from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartFarm Agent"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str
    
    # API Keys
    GEMINI_API_KEY: str
    SMARTFARM_API_KEY: str
    SMARTFARM_FACILITY_ID: str = "PF_0025298_01"
    
    # Settings Config to load from .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        # env 파일이 없거나 필드가 누락되어도 에러를 발생시키지 않으려면 아래 주석 해제 (기본값은 에러 발생)
        # extra="ignore"
    )

# 전역 설정 객체 인스턴스
settings = Settings()
