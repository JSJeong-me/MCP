지금 가지고 계신 구조를 그대로 살리면, 흐름은 한 줄로 이렇게 됩니다:

> **Google Drive 15분 리포트 → (Ingestion + Parsing) 서비스 → MarketContext MCP Server → Trader/다른 Agent가 MCP Tool 호출해서 컨텍스트 사용**

아래에서 이걸 실제로 구현 가능한 수준으로 단계별로 쪼개 보겠습니다.

---

## 0. 현재 리포트 구조 이해(예시 기준)

첨부해주신 md를 보면, 한 번의 스냅샷에 대해 대략 이런 정보들이 들어 있습니다.

* 전체 시장 Regime/Volatility

  * 예: `sideways`, confidence=0.6, volatility=Caution, news_impact=0.15
* Top Recommendations (심볼 + 점수 + 이유)
* Focus Symbols (각 심볼별 기사 수, 평균 sentiment, 메모)
* Key News Drivers (시장·섹터·위험 요인 등 텍스트)

이걸 MCP를 통해 다른 에이전트에게 넘기려면:

1. **파일 포맷 그대로(text/markdown) 제공** +
2. **Trader Agent가 바로 쓸 수 있는 구조화 JSON (regime, symbol별 sentiment 등)**

두 가지를 MCP Server에서 도구(tool)/리소스(resource)로 노출하면 깔끔합니다.

---

## 1. 전체 아키텍처 개요

텍스트로 아키텍처 그리면:

1. **Source**:

   * Google Drive 폴더
   * 15분마다 `YYYYMMDD_HHMM_report.md` 같은 리포트가 생성

2. **Ingestion & Normalizer (백엔드 서비스 1개)**

   * 일정 주기로 Drive 폴더를 스캔
   * 새로 생긴 md 파일을 다운로드
   * 파싱해서 **MarketSnapshot JSON**으로 변환
   * DB/캐시(redis, postgres 등)에 저장

3. **MarketContext MCP Server**

   * MCP 스펙에 맞는 서버 프로세스
   * Tools / Resources:

     * `get_latest_snapshot`
     * `get_snapshot_by_time`
     * `get_symbol_context`
     * `list_focus_symbols`
   * 내부적으로 2번 서비스의 DB/캐시를 조회

4. **Trader / Risk / Universe Scanner Agent**

   * MCP 클라이언트 역할
   * 의사결정 전에 MCP tool을 호출하여

     * 현재 Regime / Vol / Focus Symbols / Sentiment를 받아서
   * 프롬프트 컨텍스트에 자동으로 붙여 사용

---

## 2. Step 1 – Google Drive → Ingestion 서비스

### 2-1. Drive 접근 방식

* **인증**:

  * 서비스 계정 또는 OAuth2 (서버에서 돌릴 거면 서비스 계정 추천)
* **폴더 ID 추출**:

  * 링크: `https://drive.google.com/drive/folders/1dgGdIjdqcj8VJKJgOqbg5g_uHXpYA9Ma?...`
  * 여기서 `1dgGdIjdqcj8VJKJgOqbg5g_uHXpYA9Ma`가 폴더 ID

### 2-2. 새 파일만 가져오기 로직

서비스에서 유지해야 할 상태:

* `last_processed_time` (마지막으로 처리한 파일의 수정시간 or 생성시간)
* 또는 `last_processed_file_id`

주기(예: 5분, 10분)마다:

1. `list_files_in_folder(folder_id, modifiedTime > last_processed_time)`
2. 새로 생긴 md/텍스트 파일만 필터
3. 파일 내용을 다운로드 (`files.get(media=True)` 식)
4. 한 파일씩 **파싱 후 JSON으로 변환**
5. DB/캐시 저장
6. `last_processed_time` 업데이트

### 2-3. 저장 스키마 (예시 – DB 테이블/JSON 구조)

`market_snapshots` 테이블/컬렉션:

```json
{
  "snapshot_id": "2025-12-05T23:45:00+09:00",
  "created_at": "2025-12-05T23:45:30+09:00",
  "source_file_id": "drive_file_id",
  "regime": {
    "name": "sideways",
    "confidence": 0.60,
    "volatility_level": "caution",
    "news_impact": 0.15
  },
  "top_recommendations": [
    {
      "symbol": "005380",
      "score": 0.68,
      "reason": "Positive news and high average sentiment (1.00)."
    },
    ...
  ],
  "focus_symbols": [
    {
      "symbol": "005380",
      "articles": 16,
      "sentiment": 1.0,
      "notes": "High activity and recommended."
    },
    ...
  ],
  "news_drivers": [
    {
      "id": 1,
      "category": "macro",
      "title": "…",
      "summary": "…",
      "sentiment": "mixed"
    }
  ],
  "raw_markdown": "파일 전체 텍스트"
}
```

이 JSON 구조가 **MCP Server의 반환 타입**이 됩니다.

---

## 3. Step 2 – Markdown → 구조화 파서 설계

리포트 포맷이 비교적 일정하니, 단순 파서로 충분합니다.

### 3-1. Regime/Volatility 파싱

예시 헤더:

```md
## Executive Summary
The market is currently in a **sideways regime** with a confidence level of **60%**. Volatility is at a **CAUTION** level due to elevated news impact, indicating potential risks in trading.
```

* 정규식/간단한 문자열 파싱으로

  * regime: `sideways`
  * confidence: `0.60`
  * volatility_level: `CAUTION`
  * 추가로 `news impact (0.15)` 같은 숫자도 파싱

### 3-2. Top Recommendations 파싱

```md
## Top Recommendations
1. **005380** (Active)
   - **Score**: 0.68
   - **Reason**: Positive news and high average sentiment (1.00).
```

* `## Top Recommendations` 이후의 번호 매긴 리스트를 블록 단위로 잘라
* 각 블록에서

  * 심볼: `**005380**`
  * 상태: `(Active)` 등
  * Score: `0.68`
  * Reason: 한 줄 전체를 문자열로 저장

### 3-3. Focus Symbols, News Drivers도 동일 패턴

* `## Focus Symbols` 아래의 bullet list

  * Articles, Sentiment, Notes 파싱
* `## Key News Drivers`

  * `1. ...` 패턴을 제목/내용으로 쪼개서 sentiment를 간단 rule로 붙이거나 그대로 텍스트만 저장

파서 레벨에서는 **완벽한 자연어 해석이 아니라 숫자·구조만** 잡아주고, 나머지는 LLM이 MCP에서 받아서 처리하도록 설계하면 단순하면서도 안정적입니다.

---

## 4. Step 3 – MarketContext MCP Server 설계

이제 DB에 쌓인 `market_snapshots`를 MCP Server에서 어떻게 노출할지입니다.

### 4-1. MCP Server 역할

* MCP 스펙 상 **Server**:

  * 클라이언트(에이전트 런타임)로부터 JSON-RPC 요청을 받음
  * 등록된 **tool**/리소스를 수행
  * 응답을 JSON으로 반환

여기서는 서버 이름을 예를 들어:

> `mcp-market-context`

라고 하겠습니다.

### 4-2. 제공할 Tool / Resource 설계

**(1) Tool: `get_latest_snapshot`**

* 입력:

  * `lookback_minutes` (optional, 기본 30분)
* 동작:

  * 현재 시각 기준 가장 최근 snapshot 1개를 DB에서 조회
* 출력(JSON):

```json
{
  "snapshot_id": "2025-12-05T23:45:00+09:00",
  "regime": { ... },
  "top_recommendations": [ ... ],
  "focus_symbols": [ ... ],
  "news_drivers": [ ... ]
}
```

---

**(2) Tool: `get_snapshot_by_time`**

* 입력:

  * `timestamp` (ISO8601)
  * or `nearest` 플래그 (가장 가까운 15분 캔들)
* 동작:

  * 해당 시각과 가장 가까운 snapshot 반환

---

**(3) Tool: `get_symbol_context`**

* 입력:

  * `symbol` (예: `"005930"`)
  * `window` (예: 최근 1~3개의 snapshot)
* 동작:

  * 해당 symbol이 포함된 최근 n개의 snapshot에서

    * sentiment history
    * 점수 history
    * 관련 news_drivers
  * 등을 모아서 반환

예시 응답:

```json
{
  "symbol": "005930",
  "history": [
    {
      "snapshot_id": "2025-12-05T23:45",
      "score": 0.56,
      "sentiment": 0.562,
      "articles": 8,
      "notes": "Active with moderate sentiment."
    },
    ...
  ],
  "aggregate": {
    "mean_score": 0.60,
    "mean_sentiment": 0.40
  }
}
```

---

**(4) Resource: `market-snapshot/latest`**

* 타입: `text/markdown`
* 내용: 가장 최근 snapshot의 `raw_markdown`
* Trader Agent가 **“원문을 직접 읽고 해석”**하고 싶을 때 사용

---

**(5) Resource: `market-snapshot/latest.json`**

* 타입: `application/json`
* 내용: `get_latest_snapshot` 응답과 동일

> 도구(tool)는 “질문/쿼리 + 계산/필터/집계” 역할,
> 리소스(resource)는 “그대로 읽어오는 컨텍스트 덩어리”라고 생각하면 됩니다.

---

## 5. Step 4 – Trader / 다른 Agent에서 MCP 사용 패턴

### 5-1. Trader Agent 프롬프트 구조

Trader Agent의 시스템/도움말 프롬프트 일부를 다음처럼 정의:

> * 매 15분 거래 사이클 시작 시, **반드시**
>   `get_latest_snapshot` MCP tool을 호출해서
>   현재 시장 Regime/Volatility/Focus Symbols 정보를 받아라.
> * 특정 종목을 의사결정하기 전에는
>   `get_symbol_context(symbol=…)`를 호출해서
>   최근 sentiment/score history를 확인하고,
>   “뉴스·심리·수급이 가격에 얼마나 반영되었는지”를 평가하라.

이렇게 해두면, LLM이 자동으로 MCP tool을 호출해서 **Structured JSON**을 받아 프롬프트에 붙이고, 그걸 기반으로 의사결정을 내립니다.

### 5-2. Universe Scanner / Risk Manager와의 연동

* **Universe Scanner Agent**:

  * 시장 Regime이 `sideways` + `volatility=Caution`일 때

    * 모멘텀 전략 비중 ↓, mean-reversion 전략 비중 ↑
    * 사용할 전략 후보를 바꾸는 로직에 `regime.name`/`volatility_level` 활용

* **Risk Manager Agent**:

  * news_impact가 일정 threshold 이상일 때

    * 새 포지션 개시 제한
    * 레버리지 축소, 손절 폭 축소 등 정책 변경

이때 모두 MCP tool에서 가져오는 JSON을 그대로 사용하면 되므로,
Agent별로 다시 파싱하지 않고 **동일한 데이터 모델**을 공유하게 됩니다.

---

## 6. Step 5 – 운영 측면 체크 포인트

### 6-1. 15분 주기와 동기화

* 리포트 자체가 15분 주기로 만들어지므로

  * Ingestion 서비스는 2~5분 간격으로 Drive를 폴링
  * MCP Server는 **항상 가장 최근 snapshot**만 읽으면 됨
* Trader Agent 사이클 시작 시점과

  * snapshot 생성 시점 사이의 지연(latency)을 기록/모니터링

### 6-2. 장애/예외 처리

* Drive 연결 실패 시:

  * Ingestion 서비스에서 로그 + 알림 (Slack, 이메일 등)
  * MCP tool은

    * 최근 N분 안에 snapshot이 없으면

      * `"status": "stale"` 플래그를 달아서 응답
      * Trader Agent는 “데이터가 오래되었다”라고 인지하고
        보수적으로 행동하게 프롬프트 설계

### 6-3. 권한/보안

* MCP Server는 내부 네트워크(또는 인증된 클라이언트)에서만 접근 가능하게
* Google Drive 서비스 계정 키는

  * `.env` or Secret Manager에 저장
* 로그에는 **민감한 계정 정보**가 노출되지 않도록 주의

---

## 7. 요약 – 구현 순서 정리

1. **Google Drive Ingestion 서비스**

   * 폴더 ID 고정
   * 새 md 파일 감지 → 다운로드
   * Markdown → MarketSnapshot JSON 파서 작성
   * DB/캐시에 저장

2. **MarketSnapshot 데이터 모델 확정**

   * `regime`, `volatility`, `top_recommendations`, `focus_symbols`, `news_drivers`, `raw_markdown`
   * 이 구조를 Trader/Risk/Universe Agent가 공유하는 공통 스키마로 사용

3. **MCP Server 구현**

   * `get_latest_snapshot`, `get_snapshot_by_time`, `get_symbol_context` tool
   * `market-snapshot/latest`, `market-snapshot/latest.json` resource
   * 내부에서 DB 조회 후 JSON 반환

4. **Agent 쪽 통합**

   * MCP Server를 클라이언트(Agent 런타임)에 등록
   * Trader/Risk/Universe Agent 프롬프트에

     * “의사결정 전에 해당 MCP tool을 호출하라”는 규칙 삽입

5. **운영/모니터링**

   * 15분 주기 동기화 체크
   * snapshot 신선도(staleness) 모니터링
   * Drive/API 오류 알림

---

원하시면 다음 단계로:

* `MarketSnapshot` / `SymbolContext` 정확한 필드 정의(JSON Schema 수준)
* MCP tool response 예시 (실제 JSON 샘플)
* Ingestion 파서 설계 문서를 “코딩 에이전트가 이해하기 쉬운 영어 설명”으로

까지 이어서 만들어 드릴게요.
