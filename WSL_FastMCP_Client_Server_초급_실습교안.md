# FastMCP Client & Server 초급 실습 교안

**Windows PC · WSL 환경**

stdio 기반 Tool · Resource · Prompt 연결 실습

![FastMCP Client-Server stdio architecture](assets/architecture.png)

> 예제 기준: FastMCP 3.4.4 · Python 3.10 이상  
> 작성일  2026년 7월 24일

---

## 강의 개요

| 구분 | 내용 |
| --- | --- |
| 교육 대상 | Python 기초 문법과 터미널 명령을 처음 접했거나, MCP의 Server/Client 구조를 처음 학습하는 수강생 |
| 권장 시간 | 약 150분(개념 20분, 환경 구성 25분, Server 35분, Client 35분, 실행·검증 20분, 오류 해결·과제 15분) |
| 실습 환경 | Windows 10/11, WSL2 Ubuntu, Python 3.10 이상, FastMCP 3.4.4 |
| 완성 결과 | client.py가 server.py를 자동 실행하고 Tool, Resource, Prompt를 조회·호출하는 로컬 MCP 예제 |

### 학습 목표

- MCP Host, Client, Server가 각각 어떤 역할을 하는지 설명할 수 있다.
- FastMCP의 @mcp.tool, @mcp.resource, @mcp.prompt 데코레이터를 구분할 수 있다.
- WSL에서 Python 가상환경을 만들고 FastMCP를 설치할 수 있다.
- StdioTransport를 사용해 Client가 Server를 자식 프로세스로 실행하도록 구성할 수 있다.
- Tool 호출, Resource 읽기, Prompt 요청 결과를 확인하고 기본 오류를 해결할 수 있다.

### 전체 실습 흐름

1. Windows에서 WSL2 Ubuntu를 준비한다.
2. WSL 홈 디렉터리로 프로젝트를 복사한다.
3. Python 가상환경을 만들고 FastMCP를 설치한다.
4. server.py에서 Tools, Resource, Prompt를 등록한다.
5. client.py에서 StdioTransport와 Client를 생성한다.
6. client.py를 실행해 Server 자동 실행과 MCP 기능 호출을 확인한다.
7. notes.json 저장 결과와 오류 상황을 점검한다.

### 권장 진행 시간표

| 단계 | 시간 | 핵심 활동 |
| --- | --- | --- |
| 1. 개념 이해 | 20분 | MCP 구성요소와 stdio 데이터 흐름 이해 |
| 2. 환경 준비 | 25분 | WSL2, Python, 가상환경, 패키지 설치 |
| 3. Server 분석 | 35분 | Tool, Resource, Prompt 등록 코드 이해 |
| 4. Client 분석 | 35분 | StdioTransport, 비동기 연결, 호출 API 이해 |
| 5. 실행과 검증 | 20분 | client.py 실행, notes.json 확인 |
| 6. 오류 해결·과제 | 15분 | 대표 오류 해결, 기능 확장 실습 |

## 1. MCP와 FastMCP 기초 이해

### 1.1 MCP란 무엇인가

MCP(Model Context Protocol)는 AI 애플리케이션이 외부 기능과 데이터를 표준 방식으로 사용할 수 있도록 연결하는 프로토콜입니다. 이번 실습에서는 LLM을 연결하기 전에 **Client와 Server의 통신 자체**를 먼저 확인합니다.

> **핵심 구분**
>
> MCP는 “무엇을 판단할지”를 대신 결정하는 LLM이 아닙니다. MCP Client는 요청을 전달하고, MCP Server는 등록된 기능을 실제로 실행합니다.

### 1.2 Host · Client · Server 역할

| 구성요소 | 초급자 관점의 역할 | 이번 예제 |
| --- | --- | --- |
| Host | 사용자 입력과 전체 동작 흐름을 관리하는 상위 애플리케이션 | client.py가 간단한 Host 역할도 함께 수행 |
| Client | 특정 Server와 연결하고 목록 조회·호출 메시지를 전달 | FastMCP Client + StdioTransport |
| Server | Tool, Resource, Prompt를 등록하고 실제 기능을 제공 | server.py |

### 1.3 Tools · Resources · Prompts

| MCP 기능 | 질문으로 기억하기 | 예제 |
| --- | --- | --- |
| Tool | “어떤 작업을 실행할 것인가?” | add, greet, add_note, search_notes |
| Resource | “어떤 데이터를 읽을 것인가?” | notes://all |
| Prompt | “LLM에게 어떤 형식의 요청문을 줄 것인가?” | study_review |

> **쉬운 비유**
>
> Tool은 계산기 버튼, Resource는 읽을 수 있는 문서, Prompt는 반복해서 사용할 질문 양식으로 이해하면 쉽습니다.

### 1.4 stdio 연결 방식

![FastMCP Client-Server stdio architecture](assets/architecture.png)

- 사용자는 python client.py만 실행한다.
- Client가 현재 가상환경의 Python으로 server.py를 자식 프로세스로 실행한다.
- Client와 Server는 stdin/stdout 파이프를 통해 JSON-RPC 메시지를 교환한다.
- async with client 블록이 끝나면 연결과 Server 프로세스가 함께 정리된다.

> **매우 중요한 주의**
>
> stdio Server의 stdout은 MCP 메시지 전용입니다. server.py에 일반 print() 로그를 추가하면 프로토콜 메시지가 섞여 연결 오류가 발생할 수 있습니다.

## 2. Windows PC와 WSL 실습 환경 준비

### 2.1 사전 준비 체크리스트

| 항목 | 확인 명령 | 완료 기준 |
| --- | --- | --- |
| WSL2 | wsl --list --verbose | Ubuntu의 VERSION이 2 |
| Python | python3 --version | 3.10 이상 |
| 가상환경 | python3 -m venv .venv | 오류 없이 .venv 생성 |
| FastMCP | fastmcp version | 설치된 버전 출력 |
| 프로젝트 | ls -la | server.py와 client.py 확인 |

### 2.2 WSL 설치 및 확인

Windows PowerShell을 관리자 권한으로 실행합니다.

**PowerShell - WSL 설치**

```powershell
wsl --install
```

**PowerShell - 배포판과 WSL 버전 확인**

```powershell
wsl --list --verbose
```

> **확인 결과**
>
> Ubuntu 항목의 VERSION이 2로 표시되어야 합니다. 설치 직후에는 Windows 재부팅이 필요할 수 있습니다.

### 2.3 Ubuntu 패키지 설치

**WSL Ubuntu 터미널**

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip unzip
python3 --version
```

### 2.4 프로젝트를 WSL 홈으로 복사

Windows 다운로드 폴더의 ZIP 파일을 WSL 홈으로 복사한 뒤 압축을 풉니다. /mnt/c/...에서 직접 실행할 수도 있지만, 학습 프로젝트와 Python 가상환경은 ~/... 아래에 두는 편이 안정적입니다.

**프로젝트 복사와 압축 해제**

```bash
cd ~
cp /mnt/c/Users/<Windows사용자명>/Downloads/fastmcp_wsl_beginner.zip .
unzip fastmcp_wsl_beginner.zip
cd fastmcp_wsl_beginner
```

### 2.5 가상환경과 FastMCP 설치

**가상환경 생성과 패키지 설치**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
fastmcp version
```

> **프롬프트 확인**
>
> 가상환경이 활성화되면 터미널 앞에 (.venv)가 표시됩니다. 새 터미널을 열었다면 다시 source .venv/bin/activate를 실행해야 합니다.

## 3. 프로젝트 구조와 실행 시나리오

### 3.1 프로젝트 파일

**프로젝트 디렉터리**

```text
fastmcp_wsl_beginner/
├── server.py          # Tool, Resource, Prompt 제공
├── client.py          # Server 자동 실행 및 기능 호출
├── requirements.txt   # FastMCP 버전 고정
├── pyproject.toml
├── run_demo.sh        # 실행 편의 스크립트
└── data/
    └── notes.json     # 메모 저장 파일
```

| 파일 | 역할 |
| --- | --- |
| server.py | MCP Server를 만들고 Tool, Resource, Prompt를 등록 |
| client.py | StdioTransport로 Server를 자동 실행하고 기능을 순차 호출 |
| data/notes.json | add_note Tool이 저장하고 Resource가 읽는 JSON 데이터 |
| requirements.txt | 실습에서 사용할 FastMCP 버전을 fastmcp==3.4.4로 고정 |
| run_demo.sh | 가상환경 활성화 여부를 확인하고 client.py를 실행 |

### 3.2 실행 시나리오

1. Client가 server.py를 현재 Python 인터프리터로 실행한다.
2. ping으로 연결 상태를 확인한다.
3. Tools, Resources, Prompts 목록을 조회한다.
4. add와 greet Tool을 호출한다.
5. add_note로 메모를 저장하고 search_notes로 검색한다.
6. notes://all Resource를 읽는다.
7. study_review Prompt를 요청한다.
8. Client 연결을 닫고 Server 프로세스를 종료한다.

### 3.3 실습 전 데이터 초기화

**notes.json을 빈 배열로 초기화**

```bash
printf '[]\n' > data/notes.json
```

> **반복 실행 시 참고**
>
> client.py를 실행할 때마다 add_note가 새 메모를 하나 추가합니다. 동일한 결과로 다시 실습하려면 notes.json을 초기화합니다.

## 4. FastMCP Server 단계별 이해

### 4.1 Server 객체 생성

**server.py - FastMCP Server 객체**

```python
from fastmcp import FastMCP

mcp = FastMCP("WSL Beginner MCP Server")
```

- FastMCP 객체는 Server의 이름과 등록된 MCP 구성요소를 관리합니다.
- 이후 @mcp.tool, @mcp.resource, @mcp.prompt로 일반 Python 함수를 MCP 기능으로 노출합니다.

### 4.2 메모 데이터 파일 경로

**server.py - 현재 파일 기준 경로**

```python
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "notes.json
```

> **왜 절대 경로를 만드는가**
>
> 터미널의 현재 위치가 달라도 server.py가 있는 폴더를 기준으로 data/notes.json을 찾기 위해서입니다.

### 4.3 JSON 읽기·쓰기 함수

**핵심 로직 축약**

```python
def load_notes() -> list[dict[str, Any]]:
    ensure_data_file()
    raw_text = DATA_FILE.read_text(encoding="utf-8")
    notes = json.loads(raw_text)
    return notes

def save_notes(notes: list[dict[str, Any]]) -> None:
    DATA_FILE.write_text(
        json.dumps(notes, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
```

- ensure_ascii=False를 사용하면 한글이 유니코드 코드로 변환되지 않고 그대로 저장됩니다.
- indent=2는 JSON 파일을 사람이 읽기 쉬운 들여쓰기 형식으로 저장합니다.
- JSON 형식이 손상되었을 때는 ValueError로 의미 있는 오류 메시지를 반환하도록 구성되어 있습니다.

### 4.4 Tool 1 - add

**가장 단순한 Tool**

```python
@mcp.tool
def add(a: int, b: int) -> int:
    """두 정수를 더한 값을 반환합니다."""
    return a + b
```

> **자동 스키마 생성**
>
> FastMCP는 a: int, b: int와 반환 타입을 읽어 Tool의 입력 스키마를 자동 생성합니다. docstring은 Tool 설명으로 사용됩니다.

### 4.5 Tool 2 - greet

**입력 검증을 포함한 Tool**

```python
@mcp.tool
def greet(name: str) -> str:
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("name은 빈 문자열일 수 없습니다.")
    return f"안녕하세요, {clean_name}님!
```

- strip()으로 앞뒤 공백을 제거합니다.
- 빈 입력은 ValueError로 거부합니다.
- 정상 입력이면 문자열 결과를 반환합니다.

### 4.6 Tool 3 - add_note

**파일을 변경하는 Tool**

```python
@mcp.tool
def add_note(title: str, content: str) -> dict[str, Any]:
    notes = load_notes()

    note = {
        "id": len(notes) + 1,
        "title": title.strip(),
        "content": content.strip(),
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }

    notes.append(note)
    save_notes(notes)
    return note
```

| 처리 단계 | 설명 |
| --- | --- |
| 1. 입력 정리 | title과 content의 앞뒤 공백 제거 및 빈 문자열 검사 |
| 2. 기존 데이터 읽기 | load_notes()로 notes.json의 배열을 읽음 |
| 3. 메모 생성 | ID, 제목, 내용, 생성 시각으로 dict 생성 |
| 4. 저장 | 배열에 추가하고 save_notes() 호출 |
| 5. 결과 반환 | 저장된 메모 dict를 Client에 반환 |

### 4.7 Tool 4 - search_notes

**키워드 검색 Tool**

```python
@mcp.tool
def search_notes(keyword: str) -> list[dict[str, Any]]:
    clean_keyword = keyword.strip().lower()
    notes = load_notes()
    return [
        note for note in notes
        if clean_keyword in str(note.get("title", "")).lower()
        or clean_keyword in str(note.get("content", "")).lower()
    ]
```

> **검색 특징**
>
> 제목 또는 내용에 키워드가 포함되면 결과에 포함합니다. lower()를 사용하므로 영문 대소문자를 구분하지 않습니다.

### 4.8 Resource - notes://all

**전체 메모 Resource**

```python
@mcp.resource("notes://all", mime_type="application/json")
def get_all_notes() -> str:
    return json.dumps(load_notes(), ensure_ascii=False, indent=2)
```

Resource는 notes://all이라는 URI로 식별됩니다. Client는 Tool처럼 함수 이름을 호출하는 것이 아니라 이 URI를 읽습니다.

### 4.9 Prompt - study_review

**재사용 가능한 Prompt 템플릿**

```python
@mcp.prompt
def study_review(topic: str) -> str:
    return (
        f"'{topic}' 주제를 초급자 수준으로 복습해 주세요.\n"
        "1. 핵심 개념 3개\n"
        "2. 쉬운 비유\n"
        "3. 짧은 실습 예제\n"
        "4. 확인 문제 3개"
    )
```

### 4.10 Server 실행

**stdio Server 시작**

```python
if __name__ == "__main__":
    mcp.run()
```

> **Server 직접 실행 시**
>
> python server.py를 직접 실행하면 화면이 멈춘 것처럼 보입니다. stdio 요청을 기다리는 정상 상태이며, 초급 실습에서는 Ctrl+C로 종료하고 python client.py를 실행합니다.

## 5. FastMCP Client 단계별 이해

### 5.1 필요한 모듈과 파일 경로

**client.py - 준비 코드**

```python
import asyncio
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

BASE_DIR = Path(__file__).resolve().parent
SERVER_FILE = BASE_DIR / "server.py
```

### 5.2 StdioTransport 생성

**Server 실행 명령 구성**

```text
transport = StdioTransport(
    command=sys.executable,
    args=[str(SERVER_FILE)],
    cwd=str(BASE_DIR),
)
```

| 설정 | 의미 |
| --- | --- |
| command=sys.executable | 현재 client.py를 실행한 Python을 사용 |
| args=[server.py] | 해당 Python으로 실행할 Server 파일 지정 |
| cwd=BASE_DIR | Server 프로세스의 작업 폴더를 프로젝트 루트로 설정 |

> **가상환경이 중요한 이유**
>
> 현재 가상환경의 Python을 Server에도 그대로 사용하므로 Client와 Server가 같은 FastMCP 패키지를 사용합니다.

### 5.3 Client 생성과 비동기 연결

**연결 시작과 ping**

```python
client = Client(transport)

async with client:
    await client.ping()
    print("서버가 정상적으로 응답했습니다.")
```

- async with client에 진입할 때 Server 프로세스와 MCP 연결이 시작됩니다.
- ping은 Server가 응답할 수 있는지 확인하는 가장 단순한 검증입니다.
- 블록을 벗어나면 연결과 Server 프로세스가 자동으로 정리됩니다.

### 5.4 구성요소 목록 조회

**Server 기능 탐색**

```python
tools = await client.list_tools()
resources = await client.list_resources()
prompts = await client.list_prompts()
```

> **목록 조회의 의미**
>
> Client는 Server 코드를 미리 알지 못해도 목록 API를 통해 사용 가능한 Tool, Resource, Prompt와 설명을 탐색할 수 있습니다.

### 5.5 Tool 호출

**add Tool 호출**

```python
add_result = await client.call_tool(
    "add",
    {"a": 7, "b": 5},
)
print(add_result.data)
```

| 인자 | 설명 |
| --- | --- |
| "add" | Server에 등록된 Tool 이름 |
| {"a": 7, "b": 5} | Tool 입력 스키마에 맞는 dict |
| add_result.data | FastMCP가 구조화한 실제 Tool 반환 데이터 |

### 5.6 메모 Tool 호출

**add_note Tool 호출**

```python
note_result = await client.call_tool(
    "add_note",
    {
        "title": "FastMCP 첫 실습",
        "content": "WSL에서 stdio 방식으로 client와 server를 연결했다.",
    },
)
```

**search_notes Tool 호출**

```python
search_result = await client.call_tool(
    "search_notes",
    {"keyword": "stdio"},
)
```

### 5.7 Resource 읽기

**notes://all Resource 읽기**

```python
resource_contents = await client.read_resource("notes://all")

for item in resource_contents:
    if hasattr(item, "text"):
        print(item.text)
```

> **왜 반복문을 사용하는가**
>
> read_resource() 결과는 한 개 이상의 Resource Content를 담을 수 있는 목록이므로 각 항목을 순회합니다. 이번 예제는 텍스트 JSON을 반환합니다.

### 5.8 Prompt 요청

**study_review Prompt 요청**

```python
prompt_result = await client.get_prompt(
    "study_review",
    {"topic": "MCP Server와 Client"},
)

for message in prompt_result.messages:
    print(message.role)
    print(message.content)
```

### 5.9 asyncio.run(main())

**비동기 main 함수 실행**

```python
if __name__ == "__main__":
    asyncio.run(main())
```

> **초급자 핵심**
>
> FastMCP Client API는 비동기로 동작합니다. await가 있는 main()을 일반 함수처럼 직접 호출하지 않고 asyncio.run()으로 실행합니다.

## 6. 전체 실습 실행과 결과 확인

### 6.1 실행 전 확인

**실행 환경 확인**

```bash
cd ~/fastmcp_wsl_beginner
source .venv/bin/activate
python -c "import fastmcp; print('FastMCP import OK')"
```

### 6.2 Client 실행

**기본 실행 명령**

```text
python client.py
```

또는 실행 권한이 있는 경우 ./run_demo.sh를 사용할 수 있습니다.

**셸 스크립트 실행**

```bash
chmod +x run_demo.sh
./run_demo.sh
```

### 6.3 예상 출력 흐름

**출력 예시(일부 축약)**

```text
======================================================================
1. 서버 연결 확인
======================================================================
서버가 정상적으로 응답했습니다.

[Tools]
- add
- greet
- add_note
- search_notes

7 + 5 = 12
안녕하세요, MCP 학습자님!

저장된 메모: {...}
검색 결과: [...]
Resource: notes://all
Prompt: study_review

MCP 연결이 종료되었고 서버 프로세스도 정리되었습니다.
```

### 6.4 저장 결과 확인

**메모 데이터 확인**

```bash
cat data/notes.json
```

**저장 결과 예시**

```json
[
  {
    "id": 1,
    "title": "FastMCP 첫 실습",
    "content": "WSL에서 stdio 방식으로 client와 server를 연결했다.",
    "created_at": "2026-07-24T05:30:00+09:00"
  }
]
```

### 6.5 성공 판정 체크리스트

| 체크 | 완료 조건 |
| --- | --- |
| □ | ping 이후 “서버가 정상적으로 응답했습니다.”가 출력됨 |
| □ | Tool 4개, Resource 1개, Prompt 1개가 목록에 표시됨 |
| □ | add 결과가 12로 출력됨 |
| □ | add_note 결과가 data/notes.json에 저장됨 |
| □ | search_notes가 stdio를 포함한 메모를 반환함 |
| □ | notes://all Resource가 JSON 텍스트를 반환함 |
| □ | 연결 종료 후 server.py 프로세스가 남지 않음 |

## 7. 자주 발생하는 오류와 해결 방법

| 증상 | 원인 | 해결 |
| --- | --- | --- |
| ModuleNotFoundError: fastmcp | 가상환경 미활성화 또는 설치 누락 | source .venv/bin/activate 후 pip install -r requirements.txt |
| python3 -m venv 실패 | python3-venv 패키지 누락 | sudo apt install -y python3-venv |
| server.py 실행 후 화면 정지 | stdio 요청 대기 중인 정상 상태 | Ctrl+C 후 python client.py 실행 |
| Client 연결이 즉시 종료 | server.py 경로 또는 Python command 오류 | SERVER_FILE과 sys.executable 출력 확인 |
| JSONDecodeError | notes.json 형식 손상 | printf '[]\\n' > data/notes.json |
| stdout 관련 프로토콜 오류 | server.py에서 일반 print() 사용 | stderr 또는 파일 로깅으로 변경 |
| Permission denied: run_demo.sh | 실행 권한 없음 | chmod +x run_demo.sh |

### 7.1 단계별 진단 순서

1. pwd와 ls로 현재 프로젝트 폴더인지 확인한다.
2. which python과 python --version으로 가상환경 Python인지 확인한다.
3. python -c "import fastmcp"로 패키지 import를 확인한다.
4. python -m py_compile server.py client.py로 문법 오류를 확인한다.
5. notes.json을 빈 배열로 초기화한다.
6. python client.py를 다시 실행한다.

**기본 진단 명령**

```bash
which python
python --version
python -m py_compile server.py client.py
cat data/notes.json
```

### 7.2 Server 로그를 남기고 싶을 때

**stdout 대신 파일 로깅**

```python
import logging

logging.basicConfig(
    filename="server.log",
    level=logging.INFO,
    encoding="utf-8",
)

logging.info("add_note Tool called")
```

> **로그 원칙**
>
> stdio Server에서는 print() 대신 logging을 파일이나 stderr로 보내야 합니다. Client의 print()는 사용자 출력이므로 사용해도 됩니다.

## 8. 단계별 실습 과제

### 8.1 기초 과제 - multiply Tool 추가

server.py에 두 수를 곱하는 multiply(a: int, b: int) Tool을 추가하고 client.py에서 6 × 7 결과를 호출합니다.

**힌트**

```python
@mcp.tool
def multiply(a: int, b: int) -> int:
    """두 정수를 곱한 값을 반환합니다."""
    return a * b
```

### 8.2 중급 과제 - 메모 개수 Resource

새 Resource URI notes://count를 만들고 전체 메모 개수를 문자열 또는 JSON으로 반환합니다.

**힌트**

```python
@mcp.resource("notes://count")
def get_note_count() -> str:
    return str(len(load_notes()))
```

### 8.3 확장 과제 - delete_note Tool

- 입력: note_id: int, confirmed: bool
- confirmed가 False이면 삭제하지 않고 안내 결과 반환
- 해당 ID가 없으면 ValueError 발생
- 삭제 후 notes.json에 다시 저장

> **안전 설계**
>
> 데이터 변경 Tool에는 confirmed 같은 명시적 확인 인자를 두는 습관이 좋습니다.

### 8.4 관찰 과제 - 오류 발생시키기

| 실험 | 예상 결과 |
| --- | --- |
| greet에 공백 문자열 전달 | ValueError가 Tool 오류로 반환 |
| search_notes에 빈 keyword 전달 | 입력 검증 오류 |
| notes.json에 잘못된 문자 입력 | JSON 형식 오류 |
| server.py에 print("start") 추가 | stdio 프로토콜 연결 오류 가능 |

### 8.5 확인 문제

1. Tool과 Resource의 가장 큰 차이는 무엇입니까?
2. Client가 Server를 자동 실행하게 만드는 클래스는 무엇입니까?
3. 왜 command에 python3 문자열 대신 sys.executable을 사용합니까?
4. stdio Server에서 일반 print()를 피해야 하는 이유는 무엇입니까?
5. async with client 블록을 벗어나면 어떤 정리 작업이 일어납니까?

### 8.6 정답 및 해설

| 번호 | 정답 요약 |
| --- | --- |
| 1 | Tool은 작업을 실행하고, Resource는 URI로 식별되는 데이터를 읽습니다. |
| 2 | StdioTransport입니다. |
| 3 | 현재 가상환경과 동일한 Python 및 FastMCP 패키지를 Server에서도 사용하기 위해서입니다. |
| 4 | stdout이 MCP JSON-RPC 메시지 전용이기 때문입니다. |
| 5 | MCP 연결을 닫고 자식 Server 프로세스를 종료합니다. |

## 9. 강사용 진행 가이드

### 9.1 설명 순서 권장안

1. 처음에는 LLM을 언급하기보다 Client가 Server 기능을 발견하고 호출하는 구조에 집중합니다.
2. add Tool로 가장 단순한 호출을 확인한 뒤, add_note로 파일 변경을 보여 줍니다.
3. Tool과 Resource를 나란히 비교해 “실행”과 “읽기”의 차이를 강조합니다.
4. server.py를 직접 실행해 stdio 대기 상태를 보여 주고, client.py가 자동 실행한다는 점을 다시 확인합니다.
5. 마지막에 Prompt는 실제 LLM 호출이 아니라 메시지 템플릿을 반환하는 기능임을 설명합니다.

### 9.2 수강생 점검 질문

- 현재 Server는 어떤 Tool을 제공합니까?
- Client가 Server 경로를 어떻게 찾습니까?
- add_note를 호출하면 어느 파일이 변경됩니까?
- read_resource와 call_tool은 입력 형식이 어떻게 다릅니까?
- 프로세스가 종료되는 시점은 어디입니까?

### 9.3 실습 완료 산출물

| 산출물 | 확인 방법 |
| --- | --- |
| 실행 가능한 server.py | @mcp.tool/resource/prompt 등록 확인 |
| 실행 가능한 client.py | python client.py 정상 종료 |
| 저장 데이터 | data/notes.json에 메모 1개 이상 |
| 학습 확장 결과 | multiply 또는 notes://count 중 하나 구현 |

### 9.4 다음 학습 단계

- MCP Inspector를 이용한 Tool Schema와 호출 결과 시각적 확인
- Streamable HTTP 방식으로 Server를 실행하고 네트워크 Client 연결
- OpenAI API 또는 로컬 LLM이 Tool 선택을 결정하는 Host 구현
- SQLite 또는 Vector DB를 Resource와 Tool 뒤에 연결
- 변경 Tool에 인증, 확인, 감사 로그를 추가하는 안전 설계

## 부록 A. server.py 전체 코드

```python
"""초급자용 FastMCP 서버 예제.

이 서버는 다음 MCP 구성요소를 제공합니다.
1. Tools: add, greet, add_note, search_notes
2. Resource: notes://all
3. Prompt: study_review

실행 방식은 stdio입니다. 일반적으로 client.py가 이 파일을 자식 프로세스로
자동 실행하므로 서버 터미널을 별도로 열 필요가 없습니다.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# -----------------------------------------------------------------------------
# 1. FastMCP 서버 객체 생성
# -----------------------------------------------------------------------------
# 이 이름은 클라이언트가 서버 정보를 확인할 때 사용됩니다.
mcp = FastMCP("WSL Beginner MCP Server")

# -----------------------------------------------------------------------------
# 2. 메모 데이터 파일 준비
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "notes.json"

def ensure_data_file() -> None:
    """data/notes.json 파일이 없으면 빈 배열로 생성합니다."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]\n", encoding="utf-8")

def load_notes() -> list[dict[str, Any]]:
    """JSON 파일에서 메모 목록을 읽습니다."""
    ensure_data_file()

    try:
        raw_text = DATA_FILE.read_text(encoding="utf-8")
        notes = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError("notes.json 파일의 JSON 형식이 올바르지 않습니다.") from exc

    if not isinstance(notes, list):
        raise ValueError("notes.json의 최상위 데이터는 배열이어야 합니다.")

    return notes

def save_notes(notes: list[dict[str, Any]]) -> None:
    """메모 목록을 UTF-8 JSON 파일로 저장합니다."""
    ensure_data_file()
    DATA_FILE.write_text(
        json.dumps(notes, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

# -----------------------------------------------------------------------------
# 3. Tool 등록
# -----------------------------------------------------------------------------
# Tool은 클라이언트가 '실행'할 수 있는 함수입니다.

@mcp.tool
def add(a: int, b: int) -> int:
    """두 정수를 더한 값을 반환합니다."""
    return a + b

@mcp.tool
def greet(name: str) -> str:
    """입력한 이름으로 환영 인사를 만듭니다."""
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("name은 빈 문자열일 수 없습니다.")
    return f"안녕하세요, {clean_name}님! FastMCP 실습에 오신 것을 환영합니다."

@mcp.tool
def add_note(title: str, content: str) -> dict[str, Any]:
    """새 학습 메모를 notes.json에 저장합니다."""
    clean_title = title.strip()
    clean_content = content.strip()

    if not clean_title:
        raise ValueError("title은 비어 있을 수 없습니다.")
    if not clean_content:
        raise ValueError("content는 비어 있을 수 없습니다.")

    notes = load_notes()

    # 삭제 기능이 없는 초급 예제이므로 현재 개수 + 1로 ID를 생성합니다.
    note = {
        "id": len(notes) + 1,
        "title": clean_title,
        "content": clean_content,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }

    notes.append(note)
    save_notes(notes)
    return note

@mcp.tool
def search_notes(keyword: str) -> list[dict[str, Any]]:
    """제목 또는 내용에 키워드가 포함된 메모를 검색합니다."""
    clean_keyword = keyword.strip().lower()
    if not clean_keyword:
        raise ValueError("keyword는 비어 있을 수 없습니다.")

    notes = load_notes()
    return [
        note
        for note in notes
        if clean_keyword in str(note.get("title", "")).lower()
        or clean_keyword in str(note.get("content", "")).lower()
    ]

# -----------------------------------------------------------------------------
# 4. Resource 등록
# -----------------------------------------------------------------------------
# Resource는 클라이언트가 '읽는' 데이터입니다.

@mcp.resource("notes://all", mime_type="application/json")
def get_all_notes() -> str:
    """저장된 전체 메모를 JSON 문자열로 제공합니다."""
    return json.dumps(load_notes(), ensure_ascii=False, indent=2)

# -----------------------------------------------------------------------------
# 5. Prompt 등록
# -----------------------------------------------------------------------------
# Prompt는 LLM에게 전달할 재사용 가능한 메시지 템플릿입니다.

@mcp.prompt
def study_review(topic: str) -> str:
    """특정 주제를 복습하기 위한 질문 템플릿을 생성합니다."""
    clean_topic = topic.strip()
    if not clean_topic:
        raise ValueError("topic은 비어 있을 수 없습니다.")

    return (
        f"'{clean_topic}' 주제를 초급자 수준으로 복습해 주세요.\n"
        "다음 순서로 답변해 주세요.\n"
        "1. 핵심 개념 3개\n"
        "2. 쉬운 비유\n"
        "3. 짧은 실습 예제\n"
        "4. 확인 문제 3개"
    )

# -----------------------------------------------------------------------------
# 6. 서버 실행
# -----------------------------------------------------------------------------
# 인자를 지정하지 않으면 기본 transport는 stdio입니다.
# stdio 서버는 stdout을 MCP 메시지용으로 사용하므로 일반 print() 로그를
# 함부로 출력하지 않는 것이 중요합니다.
if __name__ == "__main__":
    mcp.run()
```

## 부록 B. client.py 전체 코드

```python
"""초급자용 FastMCP 클라이언트 예제.

실행하면 다음 순서로 동작합니다.
1. server.py를 자식 프로세스로 자동 실행
2. MCP 서버 연결 확인
3. Tool / Resource / Prompt 목록 조회
4. Tool 호출
5. Resource 읽기
6. Prompt 가져오기
7. 연결 종료와 함께 서버 프로세스 종료
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

BASE_DIR = Path(__file__).resolve().parent
SERVER_FILE = BASE_DIR / "server.py"

def print_title(text: str) -> None:
    """출력 구역을 보기 쉽게 구분합니다."""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)

def pretty(value: Any) -> str:
    """dict/list를 읽기 쉬운 JSON 형태로 출력합니다."""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2, default=str)
    return str(value)

async def main() -> None:
    # 현재 client.py를 실행한 Python을 그대로 사용해 server.py를 실행합니다.
    # 따라서 가상환경 안에서 `python client.py`를 실행하면 서버도 같은
    # 가상환경의 FastMCP 패키지를 사용합니다.
    transport = StdioTransport(
        command=sys.executable,
        args=[str(SERVER_FILE)],
        cwd=str(BASE_DIR),
    )

    client = Client(transport)

    print_title("0. FastMCP 클라이언트 시작")
    print(f"클라이언트 Python: {sys.executable}")
    print(f"실행할 서버 파일: {SERVER_FILE}")

    try:
        # async with 블록에 들어가면 서버 프로세스가 시작되고 MCP 연결이 열립니다.
        async with client:
            print_title("1. 서버 연결 확인")
            await client.ping()
            print("서버가 정상적으로 응답했습니다.")

            print_title("2. 서버가 제공하는 구성요소 목록")

            tools = await client.list_tools()
            print("[Tools]")
            for tool in tools:
                print(f"- {tool.name}: {tool.description or '설명 없음'}")

            resources = await client.list_resources()
            print("\n[Resources]")
            for resource in resources:
                print(f"- {resource.uri}: {resource.description or resource.name}")

            prompts = await client.list_prompts()
            print("\n[Prompts]")
            for prompt in prompts:
                print(f"- {prompt.name}: {prompt.description or '설명 없음'}")

            print_title("3. Tool 호출: add")
            add_result = await client.call_tool("add", {"a": 7, "b": 5})
            print(f"7 + 5 = {pretty(add_result.data)}")

            print_title("4. Tool 호출: greet")
            greet_result = await client.call_tool("greet", {"name": "MCP 학습자"})
            print(pretty(greet_result.data))

            print_title("5. Tool 호출: add_note")
            note_result = await client.call_tool(
                "add_note",
                {
                    "title": "FastMCP 첫 실습",
                    "content": "WSL에서 stdio 방식으로 client와 server를 연결했다.",
                },
            )
            print("저장된 메모:")
            print(pretty(note_result.data))

            print_title("6. Tool 호출: search_notes")
            search_result = await client.call_tool(
                "search_notes",
                {"keyword": "stdio"},
            )
            print("검색 결과:")
            print(pretty(search_result.data))

            print_title("7. Resource 읽기: notes://all")
            resource_contents = await client.read_resource("notes://all")
            for item in resource_contents:
                if hasattr(item, "text"):
                    print(item.text)
                elif hasattr(item, "blob"):
                    print(f"바이너리 데이터 {len(item.blob)} bytes")

            print_title("8. Prompt 가져오기: study_review")
            prompt_result = await client.get_prompt(
                "study_review",
                {"topic": "MCP Server와 Client"},
            )
            for index, message in enumerate(prompt_result.messages, start=1):
                content = (
                    message.content.text
                    if hasattr(message.content, "text")
                    else message.content
                )
                print(f"메시지 {index} / role={message.role}")
                print(content)

        # async with 블록을 벗어나면 연결과 서버 프로세스가 정리됩니다.
        print_title("9. 실습 완료")
        print("MCP 연결이 종료되었고 서버 프로세스도 정리되었습니다.")

    except FileNotFoundError:
        print("오류: server.py 또는 Python 실행 파일을 찾지 못했습니다.")
        raise SystemExit(1)
    except Exception as exc:
        print_title("실행 중 오류 발생")
        print(f"오류 종류: {type(exc).__name__}")
        print(f"오류 내용: {exc}")
        print("가상환경 활성화와 FastMCP 설치 여부를 확인하세요.")
        raise SystemExit(1) from exc

if __name__ == "__main__":
    asyncio.run(main())
```

## 부록 C. 설치 및 실행 파일

### C.1 requirements.txt

```text
fastmcp==3.4.4
```

### C.2 run_demo.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

# 이 스크립트는 반드시 프로젝트의 가상환경을 활성화한 뒤 실행하세요.
python client.py
```

### C.3 전체 명령 요약

**WSL 명령 한 장 요약**

```bash
# 1. 프로젝트로 이동
cd ~/fastmcp_wsl_beginner

# 2. 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 3. 설치
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4. 실행
python client.py

# 5. 결과 확인
cat data/notes.json

# 6. 데이터 초기화
printf '[]\n' > data/notes.json
```

---

## 문서 사용 안내

- 이 Markdown 문서는 Word 강의교안의 제목, 표, 코드, 실습 순서를 Markdown 형식으로 변환한 버전입니다.
- `assets/architecture.png`는 본문에서 사용하는 MCP Client-Server 구조도입니다.
- 실습 전 `requirements.txt`에 고정된 FastMCP 버전과 현재 환경의 Python 버전을 확인하세요.
