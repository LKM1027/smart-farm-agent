import asyncio
import httpx
from datetime import datetime
from app.core.config import settings

class SensorService:
    def __init__(self):
        self.api_key = settings.SMARTFARM_API_KEY
        self.base_url = "https://www.smartfarmkorea.net/Agree_WS/webservices/ProvideRestService/getEnvDataList"

    async def fetch_data(self, facility_id: str, meas_date: str = None) -> dict:
        """
        주어진 농가(온실) 시설 ID와 측정일자를 기반으로 온도, 습도, CO2 데이터를 비동기/병렬로 조회합니다.
        """
        if not meas_date:
            meas_date = datetime.now().strftime("%Y-%m-%d")

        # Fallback 처리 (API Key가 세팅되지 않았거나 테스트 용도일 때)
        if not self.api_key or self.api_key.startswith("your") or self.api_key == "temp_key":
            print(f"[SensorService] Mock 데이터를 반환합니다. 시설 ID: {facility_id}, 날짜: {meas_date}")
            return {
                "facility_id": facility_id,
                "meas_date": meas_date,
                "temperature": 25.5,
                "humidity": 85.0,
                "co2": 450
            }

        # 타겟 센서 코드 (TI: 온도, HI: 습도, CI: CO2)
        target_codes = {
            "temperature": "TI",
            "humidity": "HI",
            "co2": "CI"
        }
        
        results = {
            "facility_id": facility_id,
            "meas_date": meas_date,
            "temperature": None,
            "humidity": None,
            "co2": None
        }

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            tasks = []
            for key, fatr_code in target_codes.items():
                url = f"{self.base_url}/{self.api_key}/{facility_id}/{meas_date}/FG/EI/{fatr_code}/080300"
                tasks.append(self._fetch_single_sensor(client, url, key))
            
            # 병렬 호출 실행
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for res in responses:
                if isinstance(res, Exception):
                    print(f"[SensorService] 센서 조회 중 에러 발생: {res}")
                    continue
                if res and "key" in res and "value" in res:
                    results[res["key"]] = res["value"]
                    if res.get("time") and "exact_time" not in results:
                        results["exact_time"] = res["time"]

        # 모든 값이 None인 경우, 완전 실패로 간주하고 Fallback 제공
        if results["temperature"] is None and results["humidity"] is None and results["co2"] is None:
            print("[SensorService] 정상적인 응답을 받지 못해 Fallback 데이터를 제공합니다.")
            results["temperature"] = 25.5
            results["humidity"] = 85.0
            results["co2"] = 450

        return results

    async def _fetch_single_sensor(self, client: httpx.AsyncClient, url: str, key: str) -> dict:
        try:
            response = await client.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                item = data[-1]  # 가장 최신 시간의 데이터 (리스트 마지막 요소)
                if item.get("statusCode") and item.get("statusCode") != "00":
                    print(f"[SensorService] {key} 조회 에러 (상태코드: {item.get('statusCode')}, 메시지: {item.get('statusMessage')})")
                    return {"key": key, "value": None}
                
                val = item.get("senVal")
                exact_time = item.get("measDate") # 예: '2026-05-14 17:00:00'
                return {"key": key, "value": float(val) if val is not None else None, "time": exact_time}
            elif isinstance(data, dict):
                if data.get("statusCode") and data.get("statusCode") != "00":
                    print(f"[SensorService] {key} 조회 에러 (상태코드: {data.get('statusCode')})")
                    return {"key": key, "value": None}
                
                for list_key in ["item", "data", "list"]:
                    if list_key in data and isinstance(data[list_key], list) and len(data[list_key]) > 0:
                        item = data[list_key][-1]
                        val = item.get("senVal", item.get("value", 0))
                        exact_time = item.get("measDate")
                        return {"key": key, "value": float(val) if val is not None else 0.0, "time": exact_time}
            
            return {"key": key, "value": None}
            
        except Exception as e:
            print(f"[SensorService] {key} API 요청 실패: {e}")
            return {"key": key, "value": None}
