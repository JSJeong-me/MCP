
# =========================================================
# Colab 실습: Agent Tool 이해를 위한 최소 예제
# 주제: 간단한 CBO(Condition-Based Operation) 스타일 제어
# - Agent는 외부 시스템(BMS, Weather, Audit)을 직접 다루지 않고
# - Tool Registry를 통해 표준 방식으로 호출한다.
# =========================================================

from dataclasses import dataclass
from typing import Any, Callable, Dict, List
from pprint import pprint
import time


# =========================================================
# 1) Tool 정의를 위한 기본 클래스
# =========================================================

@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: Dict[str, Any]
    func: Callable[[Dict[str, Any]], Dict[str, Any]]


class ToolValidationError(Exception):
    pass


def validate_args(schema: Dict[str, Any], args: Dict[str, Any]) -> None:
    """
    매우 단순한 JSON-Schema 스타일 검사기.
    교육용이므로 type, required 정도만 검사합니다.
    """
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    missing = [key for key in required if key not in args]
    if missing:
        raise ToolValidationError(f"Missing required fields: {missing}")

    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
    }

    for key, value in args.items():
        if key not in properties:
            raise ToolValidationError(f"Unknown field: {key}")

        expected_type = properties[key].get("type")
        if expected_type:
            py_type = type_map.get(expected_type)
            if py_type and not isinstance(value, py_type):
                raise ToolValidationError(
                    f"Field '{key}' expects {expected_type}, got {type(value).__name__}"
                )


class ToolRegistry:
    def __init__(self) -> None:
        self.tools: Dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self.tools:
            raise ValueError(f"Tool already exists: {spec.name}")
        self.tools[spec.name] = spec

    def describe(self) -> None:
        print("=" * 70)
        print("REGISTERED TOOLS")
        print("=" * 70)
        for spec in self.tools.values():
            print(f"[{spec.name}]")
            print(f"  description : {spec.description}")
            print(f"  input_schema: {spec.input_schema}")
            print("-" * 70)

    def call(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name not in self.tools:
            return {
                "ok": False,
                "tool": tool_name,
                "error": f"Unknown tool: {tool_name}",
            }

        spec = self.tools[tool_name]

        try:
            validate_args(spec.input_schema, args)
            result = spec.func(args)
            return {
                "ok": True,
                "tool": tool_name,
                "content": result,
            }
        except Exception as e:
            return {
                "ok": False,
                "tool": tool_name,
                "error": str(e),
            }


# =========================================================
# 2) 외부 시스템(Mock)
# 실제 환경에서는 DB, BMS, Weather API, Logger 등이 여기에 해당
# =========================================================

EXTERNAL_SYSTEMS = {
    "bms": {
        "zone_a": {
            "temp_c": 28.2,
            "humidity_pct": 65.0,
            "co2_ppm": 1120,
            "fan_speed": "LOW",
            "damper_open_pct": 15,
        },
        "zone_b": {
            "temp_c": 24.0,
            "humidity_pct": 48.0,
            "co2_ppm": 690,
            "fan_speed": "LOW",
            "damper_open_pct": 10,
        },
    },
    "weather": {
        "Seoul": {
            "outdoor_temp_c": 19.0,
            "outdoor_humidity_pct": 50.0,
            "pm25": 21,
        },
        "Busan": {
            "outdoor_temp_c": 21.5,
            "outdoor_humidity_pct": 58.0,
            "pm25": 34,
        },
    },
    "audit_logs": [],
}


# =========================================================
# 3) Tool 구현
# =========================================================

def get_zone_state(args: Dict[str, Any]) -> Dict[str, Any]:
    zone_id = args["zone_id"]
    if zone_id not in EXTERNAL_SYSTEMS["bms"]:
        raise ValueError(f"Unknown zone_id: {zone_id}")

    state = EXTERNAL_SYSTEMS["bms"][zone_id].copy()
    state["zone_id"] = zone_id
    return state


def get_outdoor_weather(args: Dict[str, Any]) -> Dict[str, Any]:
    location = args["location"]
    if location not in EXTERNAL_SYSTEMS["weather"]:
        raise ValueError(f"Unknown location: {location}")

    result = EXTERNAL_SYSTEMS["weather"][location].copy()
    result["location"] = location
    return result


def set_fan_speed(args: Dict[str, Any]) -> Dict[str, Any]:
    zone_id = args["zone_id"]
    speed = args["speed"]

    if zone_id not in EXTERNAL_SYSTEMS["bms"]:
        raise ValueError(f"Unknown zone_id: {zone_id}")

    allowed = {"LOW", "MEDIUM", "HIGH"}
    if speed not in allowed:
        raise ValueError(f"speed must be one of {sorted(allowed)}")

    EXTERNAL_SYSTEMS["bms"][zone_id]["fan_speed"] = speed
    return {
        "message": f"Fan speed updated",
        "zone_id": zone_id,
        "fan_speed": speed,
    }


def set_damper_open_pct(args: Dict[str, Any]) -> Dict[str, Any]:
    zone_id = args["zone_id"]
    open_pct = args["open_pct"]

    if zone_id not in EXTERNAL_SYSTEMS["bms"]:
        raise ValueError(f"Unknown zone_id: {zone_id}")

    if not (0 <= open_pct <= 100):
        raise ValueError("open_pct must be between 0 and 100")

    EXTERNAL_SYSTEMS["bms"][zone_id]["damper_open_pct"] = open_pct
    return {
        "message": f"Damper updated",
        "zone_id": zone_id,
        "damper_open_pct": open_pct,
    }


def write_audit_log(args: Dict[str, Any]) -> Dict[str, Any]:
    message = args["message"]
    item = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "message": message,
    }
    EXTERNAL_SYSTEMS["audit_logs"].append(item)
    return item


# =========================================================
# 4) Tool Registry 구성
# =========================================================

registry = ToolRegistry()

registry.register(
    ToolSpec(
        name="get_zone_state",
        description="실내 존(zone)의 현재 센서 상태를 조회한다.",
        input_schema={
            "type": "object",
            "properties": {
                "zone_id": {"type": "string"},
            },
            "required": ["zone_id"],
        },
        func=get_zone_state,
    )
)

registry.register(
    ToolSpec(
        name="get_outdoor_weather",
        description="외기 상태를 조회한다.",
        input_schema={
            "type": "object",
            "properties": {
                "location": {"type": "string"},
            },
            "required": ["location"],
        },
        func=get_outdoor_weather,
    )
)

registry.register(
    ToolSpec(
        name="set_fan_speed",
        description="존(zone)의 팬 속도를 LOW/MEDIUM/HIGH로 설정한다.",
        input_schema={
            "type": "object",
            "properties": {
                "zone_id": {"type": "string"},
                "speed": {"type": "string"},
            },
            "required": ["zone_id", "speed"],
        },
        func=set_fan_speed,
    )
)

registry.register(
    ToolSpec(
        name="set_damper_open_pct",
        description="댐퍼 개도율(0~100)을 설정한다.",
        input_schema={
            "type": "object",
            "properties": {
                "zone_id": {"type": "string"},
                "open_pct": {"type": "integer"},
            },
            "required": ["zone_id", "open_pct"],
        },
        func=set_damper_open_pct,
    )
)

registry.register(
    ToolSpec(
        name="write_audit_log",
        description="감사 로그를 기록한다.",
        input_schema={
            "type": "object",
            "properties": {
                "message": {"type": "string"},
            },
            "required": ["message"],
        },
        func=write_audit_log,
    )
)


# =========================================================
# 5) 간단한 Agent Planner
# 실제 제품에서는 이 부분이 LLM 또는 Planning Agent 역할
# 여기서는 Tool 개념 이해를 위해 rule-based 로직을 사용
# =========================================================

def detect_zone(user_request: str) -> str:
    text = user_request.lower()
    if "zone_b" in text:
        return "zone_b"
    return "zone_a"


def detect_location(user_request: str) -> str:
    text = user_request.lower()
    if "busan" in text:
        return "Busan"
    return "Seoul"


def plan_actions(observation: Dict[str, Any]) -> Dict[str, Any]:
    """
    입력:
      observation = {
        "zone_state": {...},
        "weather": {...}
      }

    출력:
      {
        "reasons": [...],
        "actions": [
          {"tool": "...", "args": {...}},
          ...
        ]
      }
    """
    zone_state = observation["zone_state"]
    weather = observation["weather"]

    temp = zone_state["temp_c"]
    humidity = zone_state["humidity_pct"]
    co2 = zone_state["co2_ppm"]
    pm25 = weather["pm25"]

    reasons: List[str] = []
    actions: List[Dict[str, Any]] = []

    # 팬 속도 결정
    if temp >= 27.0 or humidity >= 60.0 or co2 >= 1000:
        target_fan = "HIGH"
        reasons.append("실내 온도/습도/CO2가 높아 팬 속도를 HIGH로 상향")
    elif temp >= 25.0 or co2 >= 800:
        target_fan = "MEDIUM"
        reasons.append("실내 상태가 보통 수준으로 팬 속도를 MEDIUM으로 조정")
    else:
        target_fan = "LOW"
        reasons.append("실내 상태가 안정적이므로 팬 속도를 LOW 유지")

    # 댐퍼 개도율 결정
    if pm25 <= 30 and co2 >= 900:
        target_damper = 35
        reasons.append("외기질이 양호하고 CO2가 높아 댐퍼 개도율을 35%로 확대")
    elif pm25 > 30:
        target_damper = 10
        reasons.append("외기 미세먼지가 높아 댐퍼 개도율을 10%로 제한")
    else:
        target_damper = 20
        reasons.append("일반 상태로 댐퍼 개도율을 20%로 설정")

    zone_id = zone_state["zone_id"]

    actions.append({
        "tool": "set_fan_speed",
        "args": {
            "zone_id": zone_id,
            "speed": target_fan,
        }
    })

    actions.append({
        "tool": "set_damper_open_pct",
        "args": {
            "zone_id": zone_id,
            "open_pct": target_damper,
        }
    })

    log_message = (
        f"[AUTO-CBO] zone={zone_id}, "
        f"fan={target_fan}, damper={target_damper}, "
        f"temp={temp}, humidity={humidity}, co2={co2}, pm25={pm25}, "
        f"reasons={' | '.join(reasons)}"
    )

    actions.append({
        "tool": "write_audit_log",
        "args": {
            "message": log_message
        }
    })

    return {
        "reasons": reasons,
        "actions": actions,
    }


# =========================================================
# 6) Agent 실행 루프
# =========================================================

def run_agent(user_request: str) -> Dict[str, Any]:
    zone_id = detect_zone(user_request)
    location = detect_location(user_request)

    print("=" * 70)
    print("STEP 1) OBSERVE")
    print("=" * 70)

    zone_state_result = registry.call("get_zone_state", {"zone_id": zone_id})
    weather_result = registry.call("get_outdoor_weather", {"location": location})

    if not zone_state_result["ok"]:
        raise RuntimeError(zone_state_result["error"])
    if not weather_result["ok"]:
        raise RuntimeError(weather_result["error"])

    observation = {
        "zone_state": zone_state_result["content"],
        "weather": weather_result["content"],
    }

    pprint(observation)

    print("\n" + "=" * 70)
    print("STEP 2) PLAN")
    print("=" * 70)

    plan = plan_actions(observation)
    pprint(plan)

    print("\n" + "=" * 70)
    print("STEP 3) ACT")
    print("=" * 70)

    action_results = []
    for action in plan["actions"]:
        result = registry.call(action["tool"], action["args"])
        action_results.append(result)
        pprint(result)

    print("\n" + "=" * 70)
    print("STEP 4) VERIFY FINAL STATE")
    print("=" * 70)

    final_state = registry.call("get_zone_state", {"zone_id": zone_id})
    pprint(final_state)

    final_answer = (
        f"[최종 요약]\n"
        f"- 대상 존: {zone_id}\n"
        f"- 외기 위치: {location}\n"
        f"- 최종 팬 속도: {final_state['content']['fan_speed']}\n"
        f"- 최종 댐퍼 개도율: {final_state['content']['damper_open_pct']}%\n"
        f"- 판단 근거: " + "; ".join(plan["reasons"])
    )

    return {
        "user_request": user_request,
        "observation": observation,
        "plan": plan,
        "action_results": action_results,
        "final_state": final_state,
        "final_answer": final_answer,
    }


# =========================================================
# 7) 실행 예제
# =========================================================

if __name__ == "__main__":
    print("### 사용 가능한 Tool 목록")
    registry.describe()

    print("\n\n### Agent 실행 예제 1")
    result_1 = run_agent(
        "zone_a의 현재 상태를 보고 필요하면 팬 속도와 댐퍼 개도율을 조정해줘. 위치는 Seoul."
    )
    print("\n" + result_1["final_answer"])

    print("\n\n### Agent 실행 예제 2")
    result_2 = run_agent(
        "zone_b 상태를 점검하고 필요하면 제어값을 바꿔줘. 위치는 Busan."
    )
    print("\n" + result_2["final_answer"])

    print("\n\n### 최근 감사 로그 5건")
    pprint(EXTERNAL_SYSTEMS["audit_logs"][-5:])
