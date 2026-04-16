from fastmcp import FastMCP
import sqlite3
import json
import os

DB_PATH = os.getenv("ERP_DB_PATH", "erp.db")
READ_ONLY = os.getenv("READ_ONLY", "false").lower() == "true"

mcp = FastMCP("legacy-erp-bridge")


def get_conn():
    return sqlite3.connect(DB_PATH)


def log_action(action: str, detail: dict):
    con = get_conn()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO audit_logs(action, detail) VALUES(?, ?)",
        (action, json.dumps(detail, ensure_ascii=False))
    )
    con.commit()
    con.close()


@mcp.resource("erp://schema/inventory")
def inventory_schema() -> dict:
    """재고 테이블 스키마를 제공합니다."""
    return {
        "table": "inventory",
        "columns": [
            {"name": "item_code", "type": "TEXT", "pk": True},
            {"name": "item_name", "type": "TEXT"},
            {"name": "qty", "type": "INTEGER"},
            {"name": "warehouse", "type": "TEXT"},
        ]
    }


@mcp.resource("erp://schema/purchase_orders")
def po_schema() -> dict:
    """발주 테이블 스키마를 제공합니다."""
    return {
        "table": "purchase_orders",
        "columns": [
            {"name": "po_id", "type": "INTEGER", "pk": True},
            {"name": "vendor", "type": "TEXT"},
            {"name": "item_code", "type": "TEXT"},
            {"name": "qty", "type": "INTEGER"},
            {"name": "status", "type": "TEXT"},
        ]
    }


@mcp.tool()
def find_inventory(item_code: str) -> dict:
    """품목코드 기준으로 현재 재고와 창고 정보를 조회합니다."""
    con = get_conn()
    cur = con.cursor()
    cur.execute(
        """
        SELECT item_code, item_name, qty, warehouse
        FROM inventory
        WHERE item_code = ?
        """,
        (item_code,)
    )
    row = cur.fetchone()
    con.close()

    if not row:
        return {"found": False, "item_code": item_code}

    return {
        "found": True,
        "item_code": row[0],
        "item_name": row[1],
        "qty": row[2],
        "warehouse": row[3]
    }


@mcp.tool()
def list_low_stock(threshold: int = 10) -> list[dict]:
    """재고 수량이 threshold 이하인 품목 목록을 조회합니다."""
    con = get_conn()
    cur = con.cursor()
    cur.execute(
        """
        SELECT item_code, item_name, qty, warehouse
        FROM inventory
        WHERE qty <= ?
        ORDER BY qty ASC
        """,
        (threshold,)
    )
    rows = cur.fetchall()
    con.close()

    return [
        {
            "item_code": r[0],
            "item_name": r[1],
            "qty": r[2],
            "warehouse": r[3]
        }
        for r in rows
    ]


@mcp.tool()
def find_purchase_orders(status: str = "APPROVED") -> list[dict]:
    """상태 기준으로 발주 목록을 조회합니다."""
    con = get_conn()
    cur = con.cursor()
    cur.execute(
        """
        SELECT po_id, vendor, item_code, qty, status
        FROM purchase_orders
        WHERE status = ?
        ORDER BY po_id
        """,
        (status,)
    )
    rows = cur.fetchall()
    con.close()

    return [
        {
            "po_id": r[0],
            "vendor": r[1],
            "item_code": r[2],
            "qty": r[3],
            "status": r[4]
        }
        for r in rows
    ]


@mcp.tool()
def adjust_inventory(item_code: str, delta: int, reason: str) -> dict:
    """재고를 증감 조정합니다. READ_ONLY=true 이면 차단됩니다."""
    if READ_ONLY:
        return {
            "ok": False,
            "error": "READ_ONLY 모드에서는 재고 조정이 불가능합니다."
        }

    con = get_conn()
    cur = con.cursor()

    cur.execute(
        "SELECT qty FROM inventory WHERE item_code = ?",
        (item_code,)
    )
    row = cur.fetchone()

    if not row:
        con.close()
        return {"ok": False, "error": f"{item_code} 품목을 찾을 수 없습니다."}

    old_qty = row[0]
    new_qty = old_qty + delta

    cur.execute(
        "UPDATE inventory SET qty = ? WHERE item_code = ?",
        (new_qty, item_code)
    )
    con.commit()
    con.close()

    log_action(
        "adjust_inventory",
        {
            "item_code": item_code,
            "delta": delta,
            "reason": reason,
            "old_qty": old_qty,
            "new_qty": new_qty
        }
    )

    return {
        "ok": True,
        "item_code": item_code,
        "old_qty": old_qty,
        "new_qty": new_qty,
        "reason": reason
    }


if __name__ == "__main__":
    mcp.run()
