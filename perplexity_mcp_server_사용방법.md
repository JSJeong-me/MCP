# `perplexity_mcp_server.py` 사용 가이드

## 1. 개요

`perplexity_mcp_server.py`는 Perplexity Search REST API를 FastMCP Tool로 제공하는 로컬 MCP Server입니다.

MCP Client는 `stdio` 방식으로 이 서버를 실행하고, 서버가 제공하는 `perplexity_search` Tool을 호출합니다.

```text
사용자
  │
  │ 검색어 입력
  ▼
FastMCP Client
  │
  │ MCP / stdio
  ▼
perplexity_mcp_server.py
  │
  │ HTTPS POST
  ▼
https://api.perplexity.ai/search
  │
  ▼
Perplexity 검색 결과
  │
  ▼
MCP Tool 결과
```

이 서버가 제공하는 기능은 다음과 같습니다.

| 종류 | 이름 | 설명 |
|---|---|---|
| Tool | `perplexity_search` | Perplexity Search API를 이용해 웹을 검색합니다. |
| Resource | `perplexity://server-info` | 서버 이름, API 주소, API 키 설정 여부 등을 제공합니다. |
| Log | `perplexity_mcp_server.log` | Tool 호출, 완료, 오류와 예외 정보를 기록합니다. |

---

## 2. 준비 사항

### 2.1 권장 환경

- Windows 10 또는 Windows 11
- WSL2 Ubuntu
- Python 3.10 이상
- Perplexity API Key
- 인터넷 연결

### 2.2 프로젝트 폴더 예시

```text
perplexity-mcp/
├── perplexity_mcp_server.py
├── perplexity_mcp_client.py
├── requirements.txt
└── perplexity_mcp_server.log
```

`perplexity_mcp_server.log`는 서버를 실행하면 자동으로 생성됩니다.

---

## 3. WSL 프로젝트 폴더 구성

WSL Ubuntu 터미널에서 실행합니다.

```bash
mkdir -p ~/perplexity-mcp
cd ~/perplexity-mcp
```

다운로드한 `perplexity_mcp_server.py` 파일을 이 폴더에 복사합니다.

Windows 다운로드 폴더에 파일이 있다고 가정하면 다음과 같이 복사할 수 있습니다.

```bash
cp /mnt/c/Users/<Windows사용자명>/Downloads/perplexity_mcp_server.py \
   ~/perplexity-mcp/
```

예:

```bash
cp /mnt/c/Users/kosa/Downloads/perplexity_mcp_server.py \
   ~/perplexity-mcp/
```

파일을 확인합니다.

```bash
cd ~/perplexity-mcp
ls -l
```

예상 결과:

```text
-rw-r--r-- 1 kosa kosa 7727 Jul 24 12:00 perplexity_mcp_server.py
```

---

## 4. Python 가상환경 구성

### 4.1 필요한 시스템 패키지 설치

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

Python 버전을 확인합니다.

```bash
python3 --version
```

### 4.2 가상환경 생성

```bash
cd ~/perplexity-mcp
python3 -m venv .venv
```

### 4.3 가상환경 활성화

```bash
source .venv/bin/activate
```

활성화되면 터미널 앞에 `(.venv)`가 표시됩니다.

```text
(.venv) kosa@DESKTOP-FAPUL74:~/perplexity-mcp$
```

### 4.4 패키지 설치

```bash
python -m pip install --upgrade pip
python -m pip install fastmcp httpx
```

설치 여부를 확인합니다.

```bash
python -m pip show fastmcp
python -m pip show httpx
```

### 4.5 `requirements.txt` 사용

다음 내용으로 `requirements.txt`를 만들 수 있습니다.

```text
fastmcp
httpx
```

설치:

```bash
python -m pip install -r requirements.txt
```

---

## 5. Perplexity API Key 설정

## 5.1 보안 원칙

API Key를 다음 위치에 직접 작성하지 않습니다.

- `perplexity_mcp_server.py`
- `perplexity_mcp_client.py`
- GitHub 저장소
- Markdown 문서
- 화면 공유 자료
- 채팅 메시지

잘못된 예:

```python
PERPLEXITY_API_KEY = "pplx-실제키"
```

권장 방식은 환경변수를 사용하는 것입니다.

## 5.2 현재 WSL 터미널에 API Key 설정

키 입력 내용이 화면에 표시되지 않도록 다음 명령을 사용합니다.

```bash
read -s PERPLEXITY_API_KEY
export PERPLEXITY_API_KEY
echo
```

명령을 실행한 후 Perplexity API Key를 입력하고 Enter를 누릅니다.

## 5.3 설정 여부 확인

키 전체를 출력하지 않고 설정 여부만 확인합니다.

```bash
python -c "
import os
key = os.getenv('PERPLEXITY_API_KEY')
print('API 키 설정됨' if key else 'API 키 없음')
"
```

예상 결과:

```text
API 키 설정됨
```

또는:

```bash
test -n "$PERPLEXITY_API_KEY" \
  && echo "API 키 설정됨" \
  || echo "API 키 없음"
```

> 외부에 노출된 API Key는 기존 키를 폐기한 뒤 새 키를 발급해 사용합니다.

---

## 6. 서버 코드의 주요 동작

## 6.1 FastMCP Server 생성

```python
mcp = FastMCP("Perplexity Search MCP Server")
```

이 객체가 MCP Tool과 Resource를 등록하고 `stdio` 연결을 처리합니다.

## 6.2 API Key 읽기

```python
def get_api_key() -> str:
    api_key = os.getenv("PERPLEXITY_API_KEY", "").strip()

    if not api_key:
        raise ToolError(
            "Perplexity API 키가 MCP Server에 전달되지 않았습니다."
        )

    return api_key
```

Server 프로세스에서 `PERPLEXITY_API_KEY`를 찾을 수 없으면 `ToolError`를 발생시킵니다.

## 6.3 검색 Tool

```python
@mcp.tool
async def perplexity_search(
    query: str,
    max_results: int = 3,
    max_tokens_per_page: int = 256,
) -> dict:
    ...
```

입력값:

| 인자 | 형식 | 기본값 | 유효 범위 |
|---|---|---:|---|
| `query` | 문자열 | 없음 | 빈 문자열 불가 |
| `max_results` | 정수 | `3` | 1~20 |
| `max_tokens_per_page` | 정수 | `256` | 1~1,000,000 |

반환 예:

```json
{
  "query": "FastMCP architecture",
  "result_count": 3,
  "results": [
    {
      "title": "검색 결과 제목",
      "url": "https://example.com",
      "snippet": "검색 결과 설명",
      "date": "2026-07-24",
      "last_updated": null
    }
  ],
  "request_id": "요청 ID",
  "server_time": "서버 처리 시각"
}
```

## 6.4 Server 정보 Resource

```python
@mcp.resource(
    "perplexity://server-info",
    mime_type="application/json",
)
def server_information() -> str:
    ...
```

이 Resource는 다음 정보를 제공합니다.

```json
{
  "server_name": "Perplexity Search MCP Server",
  "api_endpoint": "https://api.perplexity.ai/search",
  "api_key_configured": true,
  "available_tools": [
    "perplexity_search"
  ],
  "log_file": "/home/kosa/perplexity-mcp/perplexity_mcp_server.log"
}
```

## 6.5 서버 로그

로그 파일은 `perplexity_mcp_server.py`와 같은 폴더에 생성됩니다.

```text
perplexity_mcp_server.log
```

로그 형식:

```text
날짜 | 로그 수준 | logger 이름 | 메시지
```

예:

```text
2026-07-24 12:30:10,125 | INFO | perplexity_mcp_server |
Perplexity Search MCP Server started | transport=stdio

2026-07-24 12:30:11,029 | INFO | perplexity_mcp_server |
perplexity_search started | query=FastMCP | max_results=3 |
max_tokens_per_page=256

2026-07-24 12:30:12,482 | INFO | perplexity_mcp_server |
perplexity_search completed | result_count=3
```

---

## 7. 서버 단독 실행

다음 명령으로 서버를 직접 실행할 수 있습니다.

```bash
cd ~/perplexity-mcp
source .venv/bin/activate
python perplexity_mcp_server.py
```

예상 출력:

```text
Starting MCP server 'Perplexity Search MCP Server' with transport 'stdio'
```

이후 화면이 멈춘 것처럼 보일 수 있습니다. 이는 오류가 아니라 MCP 요청을 `stdin`으로 기다리는 정상 상태입니다.

```text
Server 실행
    │
    ▼
stdin에서 MCP JSON-RPC 요청 대기
```

종료:

```text
Ctrl+C
```

> 서버 단독 실행은 시작 여부 확인용입니다. 실제 Tool 호출 실습에서는 FastMCP Client가 Server를 자식 프로세스로 자동 실행하도록 구성하는 것이 편리합니다.

---

## 8. 권장 사용 방법: FastMCP Client에서 실행

다음 Client는 Server를 `stdio` 자식 프로세스로 실행하고 `perplexity_search` Tool을 호출합니다.

파일 이름:

```text
perplexity_mcp_client.py
```

```python
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


BASE_DIR = Path(__file__).resolve().parent
SERVER_FILE = BASE_DIR / "perplexity_mcp_server.py"


def print_result(result: Any) -> None:
    """FastMCP Tool 결과를 읽기 쉽게 출력합니다."""

    data = getattr(result, "data", None)

    if data is not None:
        print(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return

    content = getattr(result, "content", None)

    if content:
        for item in content:
            text = getattr(item, "text", None)

            if text is not None:
                print(text)
            else:
                print(item)

        return

    print(result)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Perplexity Search MCP Client"
    )

    parser.add_argument(
        "query",
        nargs="?",
        default="Perplexity API Platform",
        help="검색할 질문 또는 키워드",
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=3,
        help="검색 결과 개수: 1~20",
    )

    parser.add_argument(
        "--max-tokens-per-page",
        type=int,
        default=256,
        help="각 페이지에서 추출할 최대 토큰 수",
    )

    args = parser.parse_args()

    api_key = os.getenv("PERPLEXITY_API_KEY", "").strip()

    if not api_key:
        print(
            "PERPLEXITY_API_KEY가 설정되지 않았습니다.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    server_env = {
        "PERPLEXITY_API_KEY": api_key,
        "FASTMCP_LOG_LEVEL": "DEBUG",
    }

    # 프록시 또는 인증서 환경변수가 있다면 Server에도 전달합니다.
    optional_variables = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
    ]

    for variable_name in optional_variables:
        value = os.getenv(variable_name)

        if value:
            server_env[variable_name] = value

    transport = StdioTransport(
        command=sys.executable,
        args=[str(SERVER_FILE)],
        cwd=str(BASE_DIR),
        env=server_env,
    )

    client = Client(transport)

    try:
        async with client:
            await client.ping()
            print("MCP Server 연결 성공")

            print("\n[Tool 목록]")
            tools = await client.list_tools()

            for tool in tools:
                print(f"- {tool.name}")

            print("\n[Server Resource 확인]")
            resource_contents = await client.read_resource(
                "perplexity://server-info"
            )

            for content in resource_contents:
                text = getattr(content, "text", None)

                if text:
                    print(text)

            print("\n[Perplexity 검색 실행]")
            result = await client.call_tool(
                "perplexity_search",
                {
                    "query": args.query,
                    "max_results": args.max_results,
                    "max_tokens_per_page": (
                        args.max_tokens_per_page
                    ),
                },
            )

            print_result(result)

    except Exception as error:
        print(
            f"MCP Client 실행 오류: {error}",
            file=sys.stderr,
        )
        print(
            f"오류 종류: {type(error).__name__}",
            file=sys.stderr,
        )
        raise SystemExit(1) from error


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 9. Client 코드에서 가장 중요한 설정

### 9.1 현재 가상환경의 Python 사용

```python
command=sys.executable
```

이 설정은 Client와 Server가 같은 Python 가상환경과 같은 패키지를 사용하도록 합니다.

### 9.2 서버 파일 지정

```python
args=[str(SERVER_FILE)]
```

실행할 MCP Server 파일을 지정합니다.

### 9.3 작업 디렉터리 지정

```python
cwd=str(BASE_DIR)
```

로그 파일과 상대 경로가 프로젝트 폴더를 기준으로 처리되도록 합니다.

### 9.4 API Key 전달

```python
env={
    "PERPLEXITY_API_KEY": api_key,
}
```

이 설정이 매우 중요합니다.

Client의 환경에 API Key가 있더라도, `stdio` Server 자식 프로세스에서 환경변수를 찾지 못할 수 있으므로 `env`를 통해 명시적으로 전달합니다.

```text
WSL 터미널
  │ PERPLEXITY_API_KEY
  ▼
FastMCP Client
  │ env로 명시적 전달
  ▼
FastMCP Server
  │ Bearer 인증
  ▼
Perplexity Search API
```

---

## 10. Client 실행

프로젝트 폴더에서 실행합니다.

```bash
cd ~/perplexity-mcp
source .venv/bin/activate
```

기본 검색:

```bash
python perplexity_mcp_client.py
```

검색어 지정:

```bash
python perplexity_mcp_client.py \
  "Perplexity API Platform"
```

검색 결과 수 지정:

```bash
python perplexity_mcp_client.py \
  "FastMCP Client Server architecture" \
  --max-results 5
```

페이지당 토큰 수까지 지정:

```bash
python perplexity_mcp_client.py \
  "MCP와 REST API의 차이" \
  --max-results 5 \
  --max-tokens-per-page 400
```

---

## 11. 예상 실행 흐름

```text
MCP Server 연결 성공

[Tool 목록]
- perplexity_search

[Server Resource 확인]
{
  "server_name": "Perplexity Search MCP Server",
  "api_endpoint": "https://api.perplexity.ai/search",
  "api_key_configured": true,
  "available_tools": [
    "perplexity_search"
  ],
  "log_file": "..."
}

[Perplexity 검색 실행]
{
  "query": "Perplexity API Platform",
  "result_count": 3,
  "results": [
    {
      "title": "...",
      "url": "...",
      "snippet": "...",
      "date": "...",
      "last_updated": "..."
    }
  ],
  "request_id": "...",
  "server_time": "..."
}
```

실행이 끝나면 Client의 `async with` 블록이 종료되면서 Server 자식 프로세스도 함께 종료됩니다.

---

## 12. Perplexity REST API 직접 확인

MCP 문제와 Perplexity API 문제를 분리하려면 먼저 REST API를 직접 테스트합니다.

```bash
curl -sS \
  -X POST "https://api.perplexity.ai/search" \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Perplexity API Platform",
    "max_results": 3,
    "max_tokens_per_page": 256
  }'
```

`jq`가 설치되어 있다면 결과를 보기 좋게 출력할 수 있습니다.

```bash
sudo apt install -y jq
```

```bash
curl -sS \
  -X POST "https://api.perplexity.ai/search" \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Perplexity API Platform",
    "max_results": 3,
    "max_tokens_per_page": 256
  }' \
  | jq
```

HTTP 상태도 확인하려면:

```bash
curl -sS \
  -X POST "https://api.perplexity.ai/search" \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Perplexity API Platform",
    "max_results": 3,
    "max_tokens_per_page": 256
  }' \
  -w "\nHTTP_STATUS:%{http_code}\n"
```

### 판단 순서

```text
REST API 직접 호출 성공
        │
        ▼
API Key와 네트워크는 정상
        │
        ▼
MCP Client의 env 전달과 Server 코드 확인

REST API 직접 호출 실패
        │
        ▼
API Key, 계정 권한, 크레딧, 파라미터,
프록시 또는 네트워크 확인
```

---

## 13. 로그 확인

최근 로그 100줄 확인:

```bash
tail -n 100 perplexity_mcp_server.log
```

실시간 로그 확인:

```bash
tail -f perplexity_mcp_server.log
```

종료:

```text
Ctrl+C
```

전체 로그 확인:

```bash
cat perplexity_mcp_server.log
```

로그 파일 초기화:

```bash
: > perplexity_mcp_server.log
```

로그 파일 삭제:

```bash
rm -f perplexity_mcp_server.log
```

다음 실행 시 로그 파일이 다시 생성됩니다.

---

## 14. 대표 오류와 해결 방법

## 14.1 `Internal Server Error`

### 원인 후보

- Server 프로세스에 API Key가 전달되지 않음
- Tool 내부 Python 예외
- Perplexity API 인증 실패
- 네트워크 또는 프록시 문제

### 우선 확인

```bash
tail -n 100 perplexity_mcp_server.log
```

Client의 `StdioTransport`에 다음 설정이 있는지 확인합니다.

```python
env={
    "PERPLEXITY_API_KEY": os.environ["PERPLEXITY_API_KEY"],
}
```

---

## 14.2 API Key가 Server에 전달되지 않음

오류:

```text
Perplexity API 키가 MCP Server에 전달되지 않았습니다.
```

해결:

```python
api_key = os.environ["PERPLEXITY_API_KEY"]

transport = StdioTransport(
    command=sys.executable,
    args=[str(SERVER_FILE)],
    cwd=str(BASE_DIR),
    env={
        "PERPLEXITY_API_KEY": api_key,
    },
)
```

---

## 14.3 HTTP 401

의미:

- API Key가 잘못됨
- API Key가 폐기됨
- 인증 또는 계정 상태 문제

확인:

```bash
python -c "
import os
print('키 있음' if os.getenv('PERPLEXITY_API_KEY') else '키 없음')
"
```

기존 키가 외부에 노출되었다면 폐기하고 새 키를 발급합니다.

---

## 14.4 HTTP 403

의미:

- API 사용 권한이 없음
- 계정 또는 프로젝트 권한 문제

Perplexity 계정과 API 권한을 확인합니다.

---

## 14.5 HTTP 422

의미:

- 요청 파라미터가 유효하지 않음

확인 항목:

```text
1 <= max_results <= 20

1 <= max_tokens_per_page <= 1,000,000

query는 빈 문자열이 아님
```

---

## 14.6 HTTP 429

의미:

- API 호출량 또는 사용 한도 초과

일정 시간 뒤 다시 호출하거나 Perplexity 사용량과 요금 상태를 확인합니다.

---

## 14.7 Timeout

오류:

```text
Perplexity API 요청 시간이 초과되었습니다.
```

확인:

```bash
curl -I https://api.perplexity.ai
```

회사 또는 기관 네트워크라면 프록시 환경변수를 Server에 전달합니다.

```python
for name in [
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
]:
    value = os.getenv(name)

    if value:
        server_env[name] = value
```

---

## 14.8 인증서 오류

기업 네트워크에서 사설 인증서를 사용하는 경우 다음 환경변수를 Server에 전달해야 할 수 있습니다.

```text
SSL_CERT_FILE
REQUESTS_CA_BUNDLE
```

Client 예:

```python
for name in [
    "SSL_CERT_FILE",
    "REQUESTS_CA_BUNDLE",
]:
    value = os.getenv(name)

    if value:
        server_env[name] = value
```

---

## 14.9 `ModuleNotFoundError`

예:

```text
ModuleNotFoundError: No module named 'fastmcp'
```

가상환경을 활성화하고 패키지를 설치합니다.

```bash
cd ~/perplexity-mcp
source .venv/bin/activate
python -m pip install fastmcp httpx
```

Client에서 현재 가상환경의 Python을 사용해야 합니다.

```python
command=sys.executable
```

---

## 15. stdio 환경에서 `print()` 사용 주의

`stdio` MCP Server에서는 `stdout`이 MCP JSON-RPC 통신에 사용됩니다.

따라서 서버 코드에 다음과 같은 디버그 출력을 추가하지 않는 것이 좋습니다.

```python
print("Perplexity Tool 시작")
```

대신 파일 로깅을 사용합니다.

```python
logger.info("Perplexity Tool 시작")
```

구분:

```text
stdout
└── MCP 프로토콜 통신

perplexity_mcp_server.log
└── 개발자 확인용 로그
```

---

## 16. 문법 검사

Server 파일의 Python 문법을 검사합니다.

```bash
python -m py_compile perplexity_mcp_server.py
```

정상이면 별도의 출력 없이 종료됩니다.

Client 파일도 검사합니다.

```bash
python -m py_compile perplexity_mcp_client.py
```

---

## 17. 한 번에 실행하는 셸 스크립트

파일 이름:

```text
run_perplexity_mcp.sh
```

```bash
#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")"

if [[ -f ".venv/bin/activate" ]]; then
    source .venv/bin/activate
else
    echo ".venv 가상환경이 없습니다."
    exit 1
fi

if [[ -z "${PERPLEXITY_API_KEY:-}" ]]; then
    echo "PERPLEXITY_API_KEY가 설정되지 않았습니다."
    echo "다음 명령으로 키를 설정하세요."
    echo "read -s PERPLEXITY_API_KEY"
    echo "export PERPLEXITY_API_KEY"
    exit 1
fi

python perplexity_mcp_client.py \
    "${1:-Perplexity API Platform}" \
    --max-results "${2:-3}" \
    --max-tokens-per-page "${3:-256}"
```

실행 권한 부여:

```bash
chmod +x run_perplexity_mcp.sh
```

실행:

```bash
./run_perplexity_mcp.sh
```

검색어 지정:

```bash
./run_perplexity_mcp.sh \
  "FastMCP Client Server architecture"
```

검색어와 옵션 지정:

```bash
./run_perplexity_mcp.sh \
  "MCP와 REST API의 차이" \
  5 \
  400
```

---

## 18. 운영 시 보안 권장사항

- API Key를 소스 코드에 넣지 않습니다.
- API Key를 GitHub에 올리지 않습니다.
- 로그에 API Key 전체 값을 기록하지 않습니다.
- 검색어에 민감한 개인정보를 넣지 않습니다.
- 외부에 노출된 키는 즉시 폐기합니다.
- 운영 환경에서는 오류 세부정보 노출을 제한합니다.
- 저장소에 다음 `.gitignore`를 추가합니다.

```gitignore
.venv/
__pycache__/
*.pyc
*.log
.env
```

`.env` 파일을 사용할 경우에도 Git에 포함하지 않습니다.

---

## 19. 전체 실행 순서 요약

```bash
# 1. 프로젝트 폴더 이동
cd ~/perplexity-mcp

# 2. 가상환경 활성화
source .venv/bin/activate

# 3. 패키지 설치
python -m pip install fastmcp httpx

# 4. API Key 설정
read -s PERPLEXITY_API_KEY
export PERPLEXITY_API_KEY
echo

# 5. Server 문법 검사
python -m py_compile perplexity_mcp_server.py

# 6. REST API 직접 확인
curl -sS \
  -X POST "https://api.perplexity.ai/search" \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Perplexity API Platform",
    "max_results": 3,
    "max_tokens_per_page": 256
  }'

# 7. MCP Client 실행
python perplexity_mcp_client.py \
  "Perplexity API Platform"

# 8. Server 로그 확인
tail -n 100 perplexity_mcp_server.log
```

---

## 20. 완료 체크리스트

```text
□ WSL 프로젝트 폴더에 perplexity_mcp_server.py가 있다.
□ Python 가상환경이 활성화되어 있다.
□ fastmcp와 httpx가 설치되어 있다.
□ PERPLEXITY_API_KEY가 환경변수로 설정되어 있다.
□ REST API 직접 호출이 정상 동작한다.
□ Client가 StdioTransport env로 API Key를 전달한다.
□ client.ping()이 성공한다.
□ list_tools()에서 perplexity_search가 표시된다.
□ perplexity://server-info Resource를 읽을 수 있다.
□ perplexity_search Tool이 검색 결과를 반환한다.
□ perplexity_mcp_server.log에 실행 기록이 남는다.
□ Server 코드에서 print() 대신 logger를 사용한다.
```

---

## 21. 핵심 정리

`perplexity_mcp_server.py`는 직접 사용자가 검색어를 입력하는 프로그램이 아니라, MCP Client가 호출할 수 있는 검색 기능을 제공하는 Server입니다.

```text
perplexity_mcp_server.py
= Perplexity REST API를 감싼 MCP Server

perplexity_mcp_client.py
= MCP Server를 실행하고 Tool을 호출하는 Client
```

가장 중요한 Client 설정은 API Key를 Server 프로세스에 전달하는 것입니다.

```python
transport = StdioTransport(
    command=sys.executable,
    args=[str(SERVER_FILE)],
    cwd=str(BASE_DIR),
    env={
        "PERPLEXITY_API_KEY":
            os.environ["PERPLEXITY_API_KEY"],
    },
)
```

정상 동작 여부는 다음 세 단계로 분리해 점검합니다.

```text
1. Perplexity REST API 직접 호출
2. FastMCP Client와 Server 연결
3. perplexity_search Tool 호출
```

이 방식으로 검사하면 API 인증 문제, 네트워크 문제, MCP 환경변수 전달 문제를 각각 구분할 수 있습니다.
