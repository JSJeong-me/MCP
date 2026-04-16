from fastmcp import FastMCP
import requests

mcp = FastMCP("Weather MCP Server")


@mcp.tool()
def get_weather(location: str) -> dict:
    """특정 지역의 현재 날씨와 기온을 가져옵니다."""
    API_KEY = "6cxxxxxxxxxxxxxx"
    url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={location}&aqi=no&lang=ko"

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        return {
            "location": location,
            "weather": data["current"]["condition"]["text"],
            "temp": data["current"]["temp_c"]
        }
    except Exception as e:
        return {
            "location": location,
            "weather": "정보를 가져올 수 없음",
            "temp": None,
            "error": str(e)
        }


if __name__ == "__main__":
    # host_app.py 가 stdio subprocess 로 실행
    mcp.run()