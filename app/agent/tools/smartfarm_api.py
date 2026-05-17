import requests
from langchain_core.tools import tool
from app.core.config import settings

@tool
def get_smartfarm_sensor_data(facility_id: str) -> dict:
    """
    주어진 농가(온실) 시설 ID를 기반으로 현재 온도, 습도, CO2 농도 등의 환경 센서 데이터를 조회합니다.
    """
    api_key = settings.SMARTFARM_API_KEY
    
    # API 키가 없거나 초기 설정값(your-smartfarm-api-key)인 경우 통신을 모사하여 Mock 데이터를 반환
    if not api_key or api_key.startswith("your"):
        print(f"[Tool: get_smartfarm_sensor_data] Mock 데이터를 반환합니다. 시설 ID: {facility_id}")
        return {
            "facility_id": facility_id,
            "temperature": 25.5,
            "humidity": 85.0,
            "co2": 450
        }
        
    # 실제 API 호출 로직 (스마트팜코리아 OpenAPI 스펙 예시)
    url = f"http://www.smartfarmkorea.net/api/SensorData.do"
    params = {
        "key": api_key,
        "facilityId": facility_id
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        # 반환받은 데이터 규격에 맞게 파싱해야 하나, 여기서는 편의상 json()으로 받습니다.
        data = response.json()
        return data
        
    except Exception as e:
        print(f"[Tool: get_smartfarm_sensor_data] API 호출 실패: {e}. 임시 Mock 데이터를 반환합니다.")
        return {
            "facility_id": facility_id,
            "temperature": 25.5,
            "humidity": 85.0,
            "co2": 450
        }
