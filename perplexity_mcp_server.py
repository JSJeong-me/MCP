"""
Perplexity Search MCP Server

Perplexity REST Search API를 FastMCP Tool로 제공합니다.

필수 환경변수:
    PERPLEXITY_API_KEY

실행:
    python perplexity_mcp_server.py

주의:
    stdio 방식에서는 stdout이 MCP 프로토콜 통신에 사용됩니다.
    디버그 메시지는 print() 대신 logger를 사용하세요.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError


BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "perplexity_mcp_server.log"

PERPLEXITY_SEARCH_URL = "https://api.perplexity.ai/search"


logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    encoding="utf-8",
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("perplexity_mcp_server")

mcp = FastMCP("Perplexity Search MCP Server")


def get_api_key() -> str:
    """환경변수에서 Perplexity API 키를 가져옵니다."""

    api_key = os.getenv("PERPLEXITY_API_KEY", "").strip()

    if not api_key:
        logger.error(
            "PERPLEXITY_API_KEY is not available in the MCP server process"
        )
        raise ToolError(
            "Perplexity API 키가 MCP Server에 전달되지 않았습니다. "
            "Client의 StdioTransport env 설정을 확인하세요."
        )

    return api_key


def normalize_results(results: Any) -> list[dict[str, Any]]:
    """Perplexity API의 검색 결과를 일관된 형태로 정리합니다."""

    if not isinstance(results, list):
        logger.warning(
            "Unexpected results type received: %s",
            type(results).__name__,
        )
        return []

    normalized: list[dict[str, Any]] = []

    for item in results:
        if not isinstance(item, dict):
            logger.warning(
                "Skipping unexpected result item type: %s",
                type(item).__name__,
            )
            continue

        normalized.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": item.get("snippet"),
                "date": item.get("date"),
                "last_updated": item.get("last_updated"),
            }
        )

    return normalized


def raise_http_tool_error(error: httpx.HTTPStatusError) -> None:
    """HTTP 상태 코드에 맞는 MCP Tool 오류를 발생시킵니다."""

    status_code = error.response.status_code
    response_body = error.response.text[:1000]

    logger.exception(
        "Perplexity HTTP error | status=%d | response=%s",
        status_code,
        response_body,
    )

    messages = {
        400: "Perplexity 요청 형식이 잘못되었습니다.",
        401: (
            "Perplexity 인증에 실패했습니다. "
            "API 키의 유효성 및 계정 상태를 확인하세요."
        ),
        403: "Perplexity API 사용 권한이 없습니다.",
        404: "Perplexity Search API 엔드포인트를 찾을 수 없습니다.",
        422: (
            "Perplexity 검색 파라미터가 유효하지 않습니다. "
            f"응답: {response_body}"
        ),
        429: "Perplexity API 호출 한도를 초과했습니다.",
    }

    message = messages.get(
        status_code,
        f"Perplexity API 요청에 실패했습니다. HTTP 상태: {status_code}",
    )

    raise ToolError(message) from error


@mcp.tool
async def perplexity_search(
    query: str,
    max_results: int = 3,
    max_tokens_per_page: int = 256,
) -> dict[str, Any]:
    """
    Perplexity Search API를 이용해 웹을 검색합니다.

    Args:
        query:
            검색할 질문이나 키워드입니다.

        max_results:
            반환할 검색 결과 개수입니다. 1~20 범위입니다.

        max_tokens_per_page:
            각 웹페이지에서 추출할 최대 토큰 수입니다.
            1~1,000,000 범위입니다.

    Returns:
        검색어, 검색 결과 수, 결과 목록과 요청 메타데이터를 반환합니다.
    """

    clean_query = query.strip()

    if not clean_query:
        raise ToolError("query는 비어 있을 수 없습니다.")

    if not 1 <= max_results <= 20:
        raise ToolError(
            "max_results는 1 이상 20 이하여야 합니다."
        )

    if not 1 <= max_tokens_per_page <= 1_000_000:
        raise ToolError(
            "max_tokens_per_page는 1 이상 1,000,000 이하여야 합니다."
        )

    api_key = get_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "query": clean_query,
        "max_results": max_results,
        "max_tokens_per_page": max_tokens_per_page,
    }

    logger.info(
        "perplexity_search started | query=%s | max_results=%d "
        "| max_tokens_per_page=%d",
        clean_query,
        max_results,
        max_tokens_per_page,
    )

    timeout = httpx.Timeout(
        connect=10.0,
        read=60.0,
        write=10.0,
        pool=10.0,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout) as http_client:
            response = await http_client.post(
                PERPLEXITY_SEARCH_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

    except httpx.HTTPStatusError as error:
        raise_http_tool_error(error)

    except httpx.TimeoutException as error:
        logger.exception("Perplexity request timeout")
        raise ToolError(
            "Perplexity API 요청 시간이 초과되었습니다."
        ) from error

    except httpx.RequestError as error:
        logger.exception(
            "Perplexity network error: %s",
            error,
        )
        raise ToolError(
            f"Perplexity 네트워크 연결 오류: {error}"
        ) from error

    try:
        data = response.json()
    except ValueError as error:
        logger.exception(
            "Invalid JSON response from Perplexity"
        )
        raise ToolError(
            "Perplexity API가 올바른 JSON을 반환하지 않았습니다."
        ) from error

    if not isinstance(data, dict):
        logger.error(
            "Unexpected Perplexity response type: %s",
            type(data).__name__,
        )
        raise ToolError(
            "Perplexity API가 예상하지 못한 응답 형식을 반환했습니다."
        )

    normalized_results = normalize_results(data.get("results", []))

    logger.info(
        "perplexity_search completed | result_count=%d",
        len(normalized_results),
    )

    return {
        "query": clean_query,
        "result_count": len(normalized_results),
        "results": normalized_results,
        "request_id": data.get("id"),
        "server_time": data.get("server_time"),
    }


@mcp.resource(
    "perplexity://server-info",
    mime_type="application/json",
)
def server_information() -> str:
    """Perplexity MCP Server의 공개 설정 정보를 제공합니다."""

    information = {
        "server_name": "Perplexity Search MCP Server",
        "api_endpoint": PERPLEXITY_SEARCH_URL,
        "api_key_configured": bool(
            os.getenv("PERPLEXITY_API_KEY")
        ),
        "available_tools": ["perplexity_search"],
        "log_file": str(LOG_FILE),
    }

    return json.dumps(
        information,
        ensure_ascii=False,
        indent=2,
    )


if __name__ == "__main__":
    logger.info(
        "Perplexity Search MCP Server started | transport=stdio"
    )
    mcp.run()
