# client_gateway.py
import asyncio
import json
import openai
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse  # HTML 전송을 위해 추가
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

app = FastAPI()

OPENAI_API_KEY = "sk-" 
openai.api_key = OPENAI_API_KEY

# MCP 서버 설정
server_params = StdioServerParameters(
    command="python3",
    args=["weather_server.py"],
    env=None
)

# --- [추가] 브라우저 접속 시 index.html을 보여주는 설정 ---
@app.get("/")
async def get_index():
    # 같은 폴더에 있는 index.html 파일을 반환합니다.
    return FileResponse('index.html')
# --------------------------------------------------

async def process_with_mcp(user_message: str):
    # (기존 MCP 처리 로직과 동일)
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                mcp_tools = await session.list_tools()
                openai_tools = [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}} for t in mcp_tools.tools]

                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": "날씨 비서입니다."}, {"role": "user", "content": user_message}],
                    tools=openai_tools
                )
                message = response.choices[0].message
                if message.tool_calls:
                    tool_call = message.tool_calls[0]
                    result = await session.call_tool(tool_call.function.name, json.loads(tool_call.function.arguments))
                    return {"role": "assistant", "tool_call": tool_call.function.name, "result": json.loads(result.content[0].text)}
                return {"role": "assistant", "content": message.content}
    except Exception as e:
        return {"role": "error", "content": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            req = json.loads(data)
            response = await process_with_mcp(req.get("message", ""))
            await websocket.send_text(json.dumps(response, ensure_ascii=False))
    except WebSocketDisconnect:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)