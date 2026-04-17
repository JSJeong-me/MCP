# weather_server.py
import requests
import json
import sys
from mcp.server.fastmcp import FastMCP

# FastMCP 인스턴스 생성
mcp = FastMCP("WeatherService")

# 발급받은 WeatherAPI 키를 입력하세요
WEATHER_API_KEY = "6c6516a272db4836a30131652251007" 

@mcp.tool()
def fetch_weather(location: str) -> str:
    """특정 지역의 현재 날씨 정보를 가져오는 도구입니다."""
    url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={location}&aqi=no&lang=ko"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        
        result = {
            "location": location,
            "condition": data['current']['condition']['text'],
            "temp_c": data['current']['temp_c'],
            "humidity": data['current']['humidity']
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

if __name__ == "__main__":
    # stdio 모드로 실행
    mcp.run()