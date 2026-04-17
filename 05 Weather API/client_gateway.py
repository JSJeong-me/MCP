# client_gateway.py
import asyncio
import json
import openai
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

app = FastAPI()


OPENAI_API_KEY ="sk-proj-"
openai.api_key = OPENAI_API_KEY

server_params = StdioServerParameters(
    command="python",
    args=["weather_server.py"],
    env=None
)

async def process_with_mcp(user_message: str):
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                mcp_tools = await session.list_tools()
                openai_tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema
                        }
                    } for tool in mcp_tools.tools
                ]

                # OpenAI 호출 및 예외 처리
                try:
                    response = openai.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "당신은 MCP 도구를 사용하는 날씨 비서입니다."},
                            {"role": "user", "content": user_message}
                        ],
                        tools=openai_tools
                    )
                except openai.AuthenticationError:
                    return {"role": "error", "content": "OpenAI API 키가 올바르지 않습니다. client_gateway.py의 키를 확인해주세요."}
                except Exception as e:
                    return {"role": "error", "content": f"OpenAI 호출 중 오류 발생: {str(e)}"}

                message = response.choices[0].message

                if message.tool_calls:
                    tool_call = message.tool_calls[0]
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    result = await session.call_tool(tool_name, tool_args)
                    
                    return {
                        "role": "assistant",
                        "content": f"MCP 도구({tool_name}) 호출 결과입니다.",
                        "tool_call": tool_name,
                        "result": json.loads(result.content[0].text)
                    }
                
                return {"role": "assistant", "content": message.content}
    except Exception as e:
        return {"role": "error", "content": f"MCP 서버 연결 오류: {str(e)}"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            req = json.loads(data)
            user_msg = req.get("message", "")
            
            response = await process_with_mcp(user_msg)
            await websocket.send_text(json.dumps(response, ensure_ascii=False))
    except WebSocketDisconnect:
        print("연결 종료")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)