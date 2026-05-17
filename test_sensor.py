import asyncio
from dotenv import load_dotenv

# 환경변수(.env) 수동 로드
load_dotenv()

from app.services.sensor_service import SensorService
from app.core.config import settings

async def main():
    print("========================================")
    print("스마트팜 오픈 API 센서 데이터 호출 테스트")
    print("========================================")
    
    print(f"사용 API KEY: {settings.SMARTFARM_API_KEY[:8]}********")
    
    service = SensorService()
    
    # 시설 ID 지정 (테스트를 위해 기본값 대신 검색된 유효한 ID 사용)
    facility_id = "PF_0010056_01"
    meas_date = "2026-05-14"
    print(f"대상 시설 ID: {facility_id}")
    print(f"조회 날짜: {meas_date}")
    print("데이터를 조회 중입니다. 잠시만 기다려주세요...\n")
    
    result = await service.fetch_data(facility_id=facility_id, meas_date=meas_date)
    
    print("[수집 완료된 센서 데이터]")
    print(f"  - 시설 ID: {result.get('facility_id')}")
    print(f"  - 측정 일자: {result.get('meas_date')}")
    print(f"  - 정확한 측정 시간: {result.get('exact_time')}")
    print(f"  - 내부 온도 (TI): {result.get('temperature')} ℃")
    print(f"  - 내부 습도 (HI): {result.get('humidity')} %")
    print(f"  - 내부 CO2 (CI): {result.get('co2')} ppm")
    print("========================================")

if __name__ == "__main__":
    asyncio.run(main())
