import json
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from langchain_mcp_adapters.client import MultiServerMCPClient

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"
MCP_SERVER_FILE = BASE_DIR / "weather_mcp_server.py"

app = FastAPI(title="Weather MCP Host App")

client = MultiServerMCPClient(
    {
        "weather": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(MCP_SERVER_FILE)],
        }
    }
)


async def get_weather_tool():
    cached = getattr(app.state, "weather_tool", None)
    if cached is not None:
        return cached

    tools = await client.get_tools()
    weather_tool = next((t for t in tools if getattr(t, "name", "") == "get_weather"), None)
    if weather_tool is None:
        raise RuntimeError("get_weather tool 을 찾을 수 없습니다.")

    app.state.weather_tool = weather_tool
    return weather_tool


def normalize_tool_result(location: str, result: Any) -> dict:
    # 1) 이미 dict 면 그대로 사용
    if isinstance(result, dict):
        return result

    # 2) 문자열이면 JSON 파싱 시도
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        return {"location": location, "weather": result, "temp": None}

    # 3) MCP content block 리스트 형태 처리
    if isinstance(result, list) and result:
        first = result[0]

        if isinstance(first, dict):
            text = first.get("text")
            if isinstance(text, str):
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    return {"location": location, "weather": text, "temp": None}

        text_attr = getattr(first, "text", None)
        if isinstance(text_attr, str):
            try:
                parsed = json.loads(text_attr)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return {"location": location, "weather": text_attr, "temp": None}

    # 4) LangChain/adapter 객체에서 content/data 추출 시도
    data_attr = getattr(result, "data", None)
    if isinstance(data_attr, dict):
        return data_attr

    content_attr = getattr(result, "content", None)
    if isinstance(content_attr, list) and content_attr:
        first = content_attr[0]
        if isinstance(first, dict):
            text = first.get("text")
            if isinstance(text, str):
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    return {"location": location, "weather": text, "temp": None}
        text_attr = getattr(first, "text", None)
        if isinstance(text_attr, str):
            try:
                parsed = json.loads(text_attr)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return {"location": location, "weather": text_attr, "temp": None}

    return {"location": location, "weather": str(result), "temp": None}


@app.get("/")
async def root():
    return FileResponse(INDEX_FILE)


@app.get("/index.html")
async def index():
    return FileResponse(INDEX_FILE)


@app.get("/weather")
async def weather(location: str):
    location = (location or "").strip()
    if not location:
        raise HTTPException(status_code=400, detail="location 파라미터가 필요합니다.")

    try:
        weather_tool = await get_weather_tool()
        raw_result = await weather_tool.ainvoke({"location": location})
        result = normalize_tool_result(location, raw_result)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCP tool 호출 실패: {e}")