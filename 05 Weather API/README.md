🚀 WSL에서 실행하는 법
패키지 설치: WSL 터미널에서 아래 명령어를 실행합니다.

Bash
> pip install mcp fastapi uvicorn openai requests
파일 작성: 위 코드들을 각각 weather_server.py, client_gateway.py, index.html로 저장합니다.

서버 실행:

Bash
> python client_gateway.py
UI 열기: 브라우저에서 index.html 파일을 열어 테스트합니다.

주의: client_gateway.py 내의 server_params에서 weather_server.py의 경로가 정확해야 합니다. 같은 폴더에 두시면 됩니다!
