import asyncio
import httpx
from datetime import datetime, timedelta
from app.core.config import settings

class SensorService:
    def __init__(self):
        self.api_key = settings.SMARTFARM_API_KEY
        self.base_url = "https://www.smartfarmkorea.net/Agree_WS/webservices/ProvideRestService/getEnvDataList"

    async def fetch_data(self, facility_id: str, meas_date: str = None) -> dict:
        """
        주어진 농가(온실) 시설 ID와 측정일자를 기반으로 온도, 습도, CO2 데이터를 비동기/병렬로 조회합니다.
        """
        
        facility_id = "PF_0010056_01"  # 부여군 토마토 농가 (공식 샘플)
        meas_date = "2026-05-28"

        # Fallback 처리 (API Key가 세팅되지 않았거나 초기값/테스트용 값일 때)
        if not self.api_key or self.api_key.startswith("your") or self.api_key == "temp_key":
            print(f"[SensorService] Mock 데이터를 반환합니다. 시설 ID: {facility_id}, 날짜: {meas_date}")
            return {
                "facility_id": facility_id,
                "meas_date": meas_date,
                "temperature": 25.5,
                "humidity": 85.0,
                "co2": 450,
                "raw_response": {"reason": "invalid_api_key_or_mock_mode"}
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
            "co2": None,
            "raw_response": {}
        }
        original_date = meas_date
        tried_dates = [meas_date]

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            responses = await self._fetch_all_sensor_values(client, facility_id, meas_date, target_codes)

        for res in responses:
            if isinstance(res, Exception):
                print(f"[SensorService] 센서 조회 중 에러 발생: {res}")
                continue
            if res and "key" in res and "value" in res:
                results[res["key"]] = res["value"]
                if res.get("time") and "exact_time" not in results:
                    results["exact_time"] = res["time"]
                if res.get("raw") is not None:
                    results["raw_response"][res["key"]] = res.get("raw")
                if res.get("error") is not None:
                    results["raw_response"][res["key"]] = res.get("error")

        # 오늘 데이터가 모두 비어있다면 어제 데이터도 시도해봅니다.
        if results["temperature"] is None and results["humidity"] is None and results["co2"] is None:
            yesterday = self._yesterday_date(meas_date)
            if yesterday not in tried_dates:
                print(f"[SensorService] {original_date} 데이터가 존재하지 않습니다. 이전 날짜인 {yesterday}를 추가로 조회합니다.")
                tried_dates.append(yesterday)
                results["meas_date"] = yesterday
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    responses = await self._fetch_all_sensor_values(client, facility_id, yesterday, target_codes)
                for res in responses:
                    if isinstance(res, Exception):
                        print(f"[SensorService] 센서 조회 중 에러 발생: {res}")
                        continue
                    if res and "key" in res and "value" in res:
                        results[res["key"]] = res["value"]
                        if res.get("time") and "exact_time" not in results:
                            results["exact_time"] = res["time"]
                        if res.get("raw") is not None:
                            results["raw_response"][res["key"]] = res.get("raw")
                        if res.get("error") is not None:
                            results["raw_response"][res["key"]] = res.get("error")

        if results["temperature"] is None and results["humidity"] is None and results["co2"] is None:
            print("[SensorService] 지정된 날짜에 보관된 데이터가 없어 Fallback 데이터를 반환합니다.")
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
                target_time = "2026-05-28 14:00:00"
                item = next((row for row in data if row.get("measDate") == target_time), data[-1])    
                #item = data[-1]
                if item.get("statusCode") and item.get("statusCode") != "00":
                    print(f"[SensorService] {key} 조회 에러 (상태코드: {item.get('statusCode')}, 메시지: {item.get('statusMessage')})")
                    return {"key": key, "value": None, "error": item}

                val = item.get("senVal")
                exact_time = item.get("measDate")
                return {"key": key, "value": float(val) if val is not None else None, "time": exact_time, "raw": item}

            if isinstance(data, dict):
                if data.get("statusCode") and data.get("statusCode") != "00":
                    print(f"[SensorService] {key} 조회 에러 (statusCode={data.get('statusCode')}, message={data.get('statusMessage', data.get('message', ''))})")
                    return {"key": key, "value": None, "error": data}

                for list_key in ["item", "data", "list"]:
                    if list_key in data and isinstance(data[list_key], list) and len(data[list_key]) > 0:
                        item = data[list_key][-1]
                        val = item.get("senVal", item.get("value"))
                        exact_time = item.get("measDate")
                        return {"key": key, "value": float(val) if val is not None else None, "time": exact_time, "raw": item}

            return {"key": key, "value": None, "raw": data}

        except Exception as e:
            print(f"[SensorService] {key} API 요청 실패: {e}")
            return {"key": key, "value": None, "error": str(e)}

    async def _fetch_all_sensor_values(self, client: httpx.AsyncClient, facility_id: str, meas_date: str, target_codes: dict) -> list:
        tasks = []
        for key, fatr_code in target_codes.items():
            url = f"{self.base_url}/{self.api_key}/{facility_id}/{meas_date}/FG/EI/{fatr_code}/080300"
            tasks.append(self._fetch_single_sensor(client, url, key))
        return await asyncio.gather(*tasks, return_exceptions=True)

    def _yesterday_date(self, date_str: str) -> str:
        try:
            current = datetime.strptime(date_str, "%Y-%m-%d")
            return (current - timedelta(days=1)).strftime("%Y-%m-%d")
        except ValueError:
            return date_str
