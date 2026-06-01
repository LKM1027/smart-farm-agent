import asyncio

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.api.routes import agent, reports
from app import models
from app.database import engine, SessionLocal
from app.models import SensorLog
from app.services.autonomous_control_service import AutonomousControlService
from app.services.report_service import ReportService
from app.services.sensor_service import SensorService

# Ensure database tables are created when the application module is imported
models.Base.metadata.create_all(bind=engine)

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
    app.include_router(reports.router, prefix="/api/reports", tags=["Weekly Reports"])

    return app

app = get_application()

sensor_logger_task: asyncio.Task | None = None


def _generate_anomaly_briefing(anomaly_data: dict, control_summary: str) -> str:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.4,
        google_api_key=settings.GEMINI_API_KEY,
    )
    prompt = (
        "당신은 스마트팜 자율 관제 에이전트입니다. "
        f"현재 시설 내 온도가 {anomaly_data['temperature']}℃로 생육 한계점을 돌파했고, "
        f"습도는 {anomaly_data['humidity']}%, CO2는 {anomaly_data['co2']}ppm입니다. "
        f"시스템이 다음 제어를 실행했습니다: {control_summary}. "
        "이 상황과 조치 내역을 농장주에게 마크다운 형식으로 다급하고 짧게 브리핑하세요. "
        "우측 하드웨어 제어 테이블을 확인하라는 안내를 포함하세요."
    )
    response = llm.invoke(prompt)
    return getattr(response, "content", str(response))

async def sensor_log_worker() -> None:
    """백그라운드에서 주기적으로 센서 값을 읽어 DB에 저장합니다."""
    sensor_service = SensorService()
    while True:
        try:
            sensor_data = await sensor_service.fetch_data(settings.SMARTFARM_FACILITY_ID)
            temperature = sensor_data.get("temperature")
            humidity = sensor_data.get("humidity")
            co2 = sensor_data.get("co2")
            raw_response = sensor_data

            if temperature is None and humidity is None and co2 is None:
                print("[SensorLogger] 수집된 센서 데이터가 없어 저장을 건너뜁니다.")
            else:
                try:
                    with SessionLocal() as db:
                        db.add(
                            SensorLog(
                                temperature=float(temperature) if temperature is not None else None,
                                humidity=float(humidity) if humidity is not None else None,
                                co2=int(co2) if co2 is not None else None,
                                raw_response=raw_response,
                                is_fallback=(temperature == 25.5 and humidity == 85.0 and co2 == 450),
                            )
                        )
                        db.commit()
                        print(f"[SensorLogger] 센서 로그 저장 완료: temp={temperature}, hum={humidity}, co2={co2}")

                        alert = AutonomousControlService.detect_critical_alert(
                            {
                                "temperature": temperature,
                                "humidity": humidity,
                                "co2": co2,
                                "raw_response": raw_response,
                            }
                        )
                        if alert is not None:
                            asyncio.create_task(
                                AutonomousControlService.handle_critical_alert_safe(
                                    alert=alert,
                                    sensor_data={
                                        "temperature": temperature,
                                        "humidity": humidity,
                                        "co2": co2,
                                        "raw_response": raw_response,
                                    },
                                )
                            )
                except SQLAlchemyError as db_err:
                    print(f"[SensorLogger] DB 저장 오류: {db_err}")
                except Exception as db_err:
                    print(f"[SensorLogger] DB 저장 예외: {db_err}")
        except Exception as error:
            print(f"[SensorLogger] 센서 수집 중 예외 발생: {error}")

        await asyncio.sleep(600)  # 테스트를 위해 60초로 설정했습니다. 테스트 후 600초로 변경하세요.


@app.on_event("startup")
async def start_sensor_logger() -> None:
    global sensor_logger_task
    if sensor_logger_task is None or sensor_logger_task.done():
        sensor_logger_task = asyncio.create_task(sensor_log_worker())
        print("[SensorLogger] 백그라운드 센서 로그 스케줄러가 시작되었습니다.")


@app.on_event("shutdown")
async def stop_sensor_logger() -> None:
    global sensor_logger_task
    if sensor_logger_task is not None:
        sensor_logger_task.cancel()
        try:
            await sensor_logger_task
        except asyncio.CancelledError:
            print("[SensorLogger] 백그라운드 센서 로그 스케줄러가 정상 종료되었습니다.")


@app.get("/", tags=["Health Check"])
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}


@app.get("/api/test/sensor/latest", tags=["Simulation"])
async def get_latest_sensor_data():
    try:
        with SessionLocal() as db:
            stmt = (
                select(SensorLog)
                .order_by(SensorLog.timestamp.desc(), SensorLog.id.desc())
                .limit(1)
            )
            latest = db.scalars(stmt).first()
    except Exception as exc:
        print(f"[SensorLatest] latest sensor lookup failed: {exc}")
        raise HTTPException(status_code=500, detail="latest sensor lookup failed")

    if latest is None:
        return {
            "temperature": None,
            "humidity": None,
            "co2": None,
            "facility_id": settings.SMARTFARM_FACILITY_ID,
        }

    return {
        "temperature": latest.temperature,
        "humidity": latest.humidity,
        "co2": latest.co2,
        "facility_id": settings.SMARTFARM_FACILITY_ID,
        "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
    }


@app.post("/api/test/inject-anomaly", tags=["Simulation"])
async def inject_anomaly(background_tasks: BackgroundTasks):
    anomaly_data = {
        "temperature": 45.5,
        "humidity": 40.0,
        "co2": 200,
        "facility_id": settings.SMARTFARM_FACILITY_ID,
        "source": "fault_injection_demo",
    }

    try:
        with SessionLocal() as db:
            db.add(
                SensorLog(
                    temperature=anomaly_data["temperature"],
                    humidity=anomaly_data["humidity"],
                    co2=anomaly_data["co2"],
                    raw_response=anomaly_data,
                    is_fallback=False,
                )
            )
            db.commit()
    except Exception as exc:
        print(f"[Simulation] anomaly injection failed: {exc}")
        raise HTTPException(status_code=500, detail="폭염 데이터 주입 실패")

    alert = AutonomousControlService.detect_critical_alert(anomaly_data)
    control_summary = "환풍기(CC18) ON, 천창(CC01) OPEN, 측창(CC02) OPEN"
    if alert is not None:
        control_summary = ", ".join(
            f"{cmd.description}({cmd.device.value} {cmd.action.value})"
            for cmd in alert.control_sequence
        )
        background_tasks.add_task(
            AutonomousControlService.handle_critical_alert_safe,
            alert,
            anomaly_data,
        )

    try:
        agent_message = await asyncio.to_thread(
            _generate_anomaly_briefing,
            anomaly_data,
            control_summary,
        )
    except Exception as exc:
        print(f"[Simulation] anomaly briefing generation failed: {exc}")
        agent_message = ""

    return {
        "status": "success",
        "message": "폭염 데이터 주입 완료",
        "agent_message": agent_message,
    }


@app.get("/api/v1/report/generate", tags=["Report"])
async def generate_report():
    """최근 7일간 로그를 집계하여 농업인용 및 설비업체용 마크다운 리포트를 생성합니다."""
    service = ReportService()

    try:
        reports = service.generate_markdown_reports()
        service.dispatch_report_via_mcp("농업인용 생육 리포트", reports["farm_report"])
        service.dispatch_report_via_mcp("설비업체용 장비 점검 리포트", reports["equipment_report"])
    except Exception as exc:
        print(f"[main] 리포트 생성 중 오류 발생: {exc}")
        raise HTTPException(status_code=500, detail="리포트 생성 중 내부 오류가 발생했습니다.")

    return {
        "farm_report": reports["farm_report"],
        "equipment_report": reports["equipment_report"],
    }
