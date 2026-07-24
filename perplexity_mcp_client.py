"""
Perplexity Search FastMCP Client

로컬 perplexity_mcp_server.py를 stdio 방식으로 실행하고
perplexity_search Tool을 호출합니다.

필수 환경변수:
    PERPLEXITY_API_KEY

실행 예:
    python perplexity_mcp_client.py "Perplexity API Platform"

    python perplexity_mcp_client.py \
        "FastMCP Client Server architecture" \
        --max-results 5 \
        --max-tokens-per-page 400
"""

from __future__ import annotations

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


def print_separator(title: str) -> None:
    """터미널 출력 영역을 구분합니다."""

    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def to_serializable(value: Any) -> Any:
    """Pydantic 객체 등을 JSON 출력이 가능한 형태로 변환합니다."""

    if hasattr(value, "model_dump"):
        return value.model_dump()

    if hasattr(value, "dict"):
        return value.dict()

    return value


def print_tool_result(result: Any) -> None:
    """FastMCP Tool 호출 결과를 읽기 쉽게 출력합니다."""

    data = getattr(result, "data", None)

    if data is not None:
        data = to_serializable(data)

        if isinstance(data, (dict, list)):
            print(
                json.dumps(
                    data,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )
        else:
            print(data)

        return

    structured_content = getattr(
        result,
        "structured_content",
        None,
    )

    if structured_content is not None:
        print(
            json.dumps(
                structured_content,
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


def build_server_environment(api_key: str) -> dict[str, str]:
    """
    MCP Server 자식 프로세스에 전달할 환경변수를 구성합니다.

    API Key 외에 프록시와 인증서 관련 환경변수도 현재 WSL 환경에서
    설정되어 있다면 함께 전달합니다.
    """

    server_env = {
        "PERPLEXITY_API_KEY": api_key,
        "FASTMCP_LOG_LEVEL": "DEBUG",
    }

    optional_variables = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "no_proxy",
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
    ]

    for variable_name in optional_variables:
        value = os.getenv(variable_name)

        if value:
            server_env[variable_name] = value

    return server_env


async def print_server_resource(client: Client) -> None:
    """서버 정보 Resource를 읽어 출력합니다."""

    try:
        contents = await client.read_resource(
            "perplexity://server-info"
        )
    except Exception as error:
        print(
            f"서버 정보 Resource를 읽지 못했습니다: {error}"
        )
        return

    for item in contents:
        text = getattr(item, "text", None)

        if text is not None:
            print(text)
        else:
            print(item)


async def main() -> None:
    """MCP Server를 실행하고 Perplexity Search Tool을 호출합니다."""

    parser = argparse.ArgumentParser(
        description="Perplexity Search FastMCP Client"
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

    if not SERVER_FILE.exists():
        print(
            f"오류: MCP Server 파일을 찾을 수 없습니다: {SERVER_FILE}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    api_key = os.getenv(
        "PERPLEXITY_API_KEY",
        "",
    ).strip()

    if not api_key:
        print(
            "오류: PERPLEXITY_API_KEY 환경변수가 설정되지 않았습니다.",
            file=sys.stderr,
        )
        print(
            "WSL에서 다음 명령으로 설정하세요:\n"
            "  read -s PERPLEXITY_API_KEY\n"
            "  export PERPLEXITY_API_KEY",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if not 1 <= args.max_results <= 20:
        print(
            "오류: --max-results는 1~20 범위여야 합니다.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if not 1 <= args.max_tokens_per_page <= 1_000_000:
        print(
            "오류: --max-tokens-per-page는 "
            "1~1,000,000 범위여야 합니다.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    server_env = build_server_environment(api_key)

    transport = StdioTransport(
        command=sys.executable,
        args=[str(SERVER_FILE)],
        cwd=str(BASE_DIR),
        env=server_env,
    )

    client = Client(transport)

    try:
        async with client:
            print_separator("1. MCP Server 연결 확인")

            await client.ping()

            print("Perplexity Search MCP Server가 응답했습니다.")

            print_separator("2. 사용 가능한 MCP Tool")

            tools = await client.list_tools()

            if not tools:
                print("서버가 제공하는 Tool이 없습니다.")
                return

            for index, tool in enumerate(tools, start=1):
                print(f"{index}. {tool.name}")

                if tool.description:
                    first_line = (
                        tool.description
                        .strip()
                        .splitlines()[0]
                    )
                    print(f"   설명: {first_line}")

            tool_names = {tool.name for tool in tools}

            if "perplexity_search" not in tool_names:
                raise RuntimeError(
                    "perplexity_search Tool을 찾을 수 없습니다."
                )

            print_separator("3. MCP Server 정보")

            await print_server_resource(client)

            print_separator("4. Perplexity Search Tool 호출")

            print(f"검색어: {args.query}")
            print(f"검색 결과 개수: {args.max_results}")
            print(
                "페이지당 최대 토큰 수: "
                f"{args.max_tokens_per_page}"
            )

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

            print_separator("5. 검색 결과")

            print_tool_result(result)

            print_separator("6. 실행 완료")

            print(
                "Perplexity Search MCP Tool 호출을 "
                "정상적으로 완료했습니다."
            )

    except KeyboardInterrupt:
        print(
            "\n사용자가 실행을 중단했습니다.",
            file=sys.stderr,
        )
        raise SystemExit(130)

    except Exception as error:
        print(
            f"MCP Client 실행 오류: {error}",
            file=sys.stderr,
        )
        print(
            f"오류 종류: {type(error).__name__}",
            file=sys.stderr,
        )
        print(
            "서버 로그 확인:\n"
            "  tail -n 100 perplexity_mcp_server.log",
            file=sys.stderr,
        )
        raise SystemExit(1) from error


if __name__ == "__main__":
    asyncio.run(main())
