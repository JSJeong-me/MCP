from fastapi import FastAPI, WebSocket
import openai
import json
import requests

openai.api_key = "sk-proj-"  # 본인 키로 교체
OPENWEATHER_API_KEY = "6c65XXXXXXXXXXXXX"  # 발급받은 키로 교체

app = FastAPI()

# def get_weather(location: str):
#     # 예시 응답
#     return {"location": location, "weather": "sunny", "temp": 28}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        req = json.loads(data)
        user_message = req.get("message", "")
        # 여기서 call_openai_with_functions는 일반 함수로 호출
        response = call_openai_with_functions(user_message)
        await websocket.send_text(json.dumps(response, ensure_ascii=False))

def call_openai_with_functions(message):
    functions = [
        {
            "name": "get_weather",
            "description": "특정 지역의 현재 날씨를 가져옵니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "도시명"}
                },
                "required": ["location"]
            }
        }
    ]
    completion = openai.chat.completions.create(
        model="gpt-4o",  # 또는 사용가능한 모델
        messages=[
            {"role": "system", "content": "당신은 날씨 비서입니다."},
            {"role": "user", "content": message}
        ],
        functions=functions,
        function_call="auto"
    )

    choice = completion.choices[0]
    if hasattr(choice.message, "function_call") and choice.finish_reason == "function_call":
        func_name = choice.message.function_call.name
        args = json.loads(choice.message.function_call.arguments)
        if func_name == "get_weather":
            result = get_weather(args["location"])
            return {"function": func_name, "result": result}
    else:
        return {"response": choice.message.content}


import requests

def get_weather(location: str):
    API_KEY = "6c6516a272db4836a30131652251007"  # 본인의 API Key
    url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={location}&aqi=no&lang=ko"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        weather = data['current']['condition']['text']  # 한글로 날씨 설명
        temp = data['current']['temp_c']                # 섭씨 온도
        return {
            "location": location,
            "weather": weather,
            "temp": temp
        }
    except Exception as e:
        return {
            "location": location,
            "weather": "정보를 가져올 수 없음",
            "temp": None,
            "error": str(e)
        }