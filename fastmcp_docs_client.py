"""
FastMCP 공식 문서 MCP 서버 연결 예제

문서 웹페이지:
https://gofastmcp.com/getting-started/welcome

실제 MCP 서버:
https://gofastmcp.com/mcp
"""

import asyncio
import json
from typing import Any

from fastmcp import Client


MCP_SERVER_URL = "https://gofastmcp.com/mcp"


def print_separator(title: str) -> None:
    """터미널 출력 영역을 구분합니다."""
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def get_attribute(
    obj: Any,
    *attribute_names: str,
    default: Any = None,
) -> Any:
    """
    여러 후보 속성 이름 중 존재하는 값을 반환합니다.

    FastMCP 버전에 따라 다음처럼 속성 이름이 달라질 수 있습니다.

    serverInfo
    server_info

    protocolVersion
    protocol_version
    """

    if obj is None:
        return default

    for attribute_name in attribute_names:
        if hasattr(obj, attribute_name):
            value = getattr(obj, attribute_name)

            if value is not None:
                return value

    return default


def print_server_information(client: Client) -> None:
    """
    FastMCP 버전에 맞춰 서버 정보를 출력합니다.

    최신 API:
        client.server_info

    이전 API:
        client.initialize_result.serverInfo
    """

    # FastMCP 최신 버전에서 사용하는 속성
    server_info = getattr(client, "server_info", None)

    if server_info is not None:
        server_name = get_attribute(
            server_info,
            "name",
            default="이름 없음",
        )
        server_version = get_attribute(
            server_info,
            "version",
            default="버전 정보 없음",
        )
        protocol_version = getattr(
            client,
            "protocol_version",
            None,
        )
        instructions = getattr(
            client,
            "instructions",
            None,
        )

        print(f"서버 이름: {server_name}")
        print(f"서버 버전: {server_version}")

        if protocol_version is not None:
            print(f"프로토콜 버전: {protocol_version}")

        if instructions:
            print(f"서버 안내: {instructions}")

        return

    # FastMCP 2.x 및 일부 3.x 버전에서 사용하는 속성
    initialize_result = getattr(
        client,
        "initialize_result",
        None,
    )

    if initialize_result is not None:
        server_info = get_attribute(
            initialize_result,
            "serverInfo",
            "server_info",
        )

        protocol_version = get_attribute(
            initialize_result,
            "protocolVersion",
            "protocol_version",
        )

        instructions = get_attribute(
            initialize_result,
            "instructions",
        )

        if server_info is not None:
            server_name = get_attribute(
                server_info,
                "name",
                default="이름 없음",
            )

            server_version = get_attribute(
                server_info,
                "version",
                default="버전 정보 없음",
            )

            print(f"서버 이름: {server_name}")
            print(f"서버 버전: {server_version}")
        else:
            print("서버 이름과 버전 정보가 제공되지 않았습니다.")

        if protocol_version is not None:
            print(f"프로토콜 버전: {protocol_version}")

        if instructions:
            print(f"서버 안내: {instructions}")

        return

    # 서버 정보가 없더라도 연결과 Tool 사용은 가능합니다.
    print("서버 메타데이터를 읽을 수 없습니다.")
    print("연결 상태는 Tool 목록 조회를 통해 확인합니다.")


def convert_to_serializable(value: Any) -> Any:
    """Pydantic 객체 등을 JSON으로 출력 가능한 형태로 변환합니다."""

    if hasattr(value, "model_dump"):
        return value.model_dump()

    if hasattr(value, "dict"):
        return value.dict()

    return value


def print_result(result: Any) -> None:
    """Tool 호출 결과를 초급자가 읽기 쉽게 출력합니다."""

    data = getattr(result, "data", None)

    if data is not None:
        data = convert_to_serializable(data)

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

    contents = getattr(result, "content", None)

    if contents:
        for item in contents:
            text = getattr(item, "text", None)

            if text is not None:
                print(text)
            else:
                print(item)

        return

    print(result)


async def main() -> None:
    """FastMCP 문서 서버에 연결하고 문서를 검색합니다."""

    print(f"MCP 서버 연결 시도: {MCP_SERVER_URL}")

    try:
        async with Client(MCP_SERVER_URL) as client:
            print_separator("1. MCP 서버 연결 성공")

            # 버전별 차이를 처리하는 함수
            print_server_information(client)

            print_separator("2. 서버가 제공하는 Tool 목록")

            tools = await client.list_tools()

            if not tools:
                print("서버가 제공하는 Tool이 없습니다.")
                return

            for index, tool in enumerate(tools, start=1):
                print(f"{index}. {tool.name}")

                if tool.description:
                    print(f"   설명: {tool.description}")

                input_schema = get_attribute(
                    tool,
                    "inputSchema",
                    "input_schema",
                )

                if input_schema:
                    print(
                        "   입력 스키마:",
                        json.dumps(
                            input_schema,
                            ensure_ascii=False,
                            default=str,
                        ),
                    )

            tool_names = {
                tool.name
                for tool in tools
            }

            if "search_fast_mcp" not in tool_names:
                print()
                print(
                    "search_fast_mcp Tool을 "
                    "찾을 수 없습니다."
                )
                print(
                    "출력된 Tool 목록에서 "
                    "검색 Tool 이름을 확인하세요."
                )
                return

            print_separator("3. FastMCP 기본 개념 검색")

            result = await client.call_tool(
                name="search_fast_mcp",
                arguments={
                    "query": (
                        "Explain FastMCP servers, clients, "
                        "tools, resources, and prompts "
                        "for a beginner."
                    )
                },
            )

            print_result(result)

            print_separator("4. FastMCP Client 연결 방법 검색")

            second_result = await client.call_tool(
                name="search_fast_mcp",
                arguments={
                    "query": (
                        "How do I create a FastMCP Client "
                        "and connect to a remote HTTP "
                        "MCP server?"
                    )
                },
            )

            print_result(second_result)

            print_separator("5. 실행 완료")

            print("MCP 서버 검색을 정상적으로 완료했습니다.")

    except TimeoutError:
        print("MCP 서버 연결 시간이 초과되었습니다.")
        print("WSL 인터넷 연결 상태를 확인하세요.")

    except ConnectionError as error:
        print(f"MCP 서버 연결에 실패했습니다: {error}")

    except Exception as error:
        print(
            "MCP Client 실행 중 오류가 발생했습니다:",
            error,
        )
        print(f"오류 종류: {type(error).__name__}")


if __name__ == "__main__":
    asyncio.run(main())