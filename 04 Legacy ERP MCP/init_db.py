import sqlite3

con = sqlite3.connect("erp.db")
cur = con.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    item_code TEXT PRIMARY KEY,
    item_name TEXT NOT NULL,
    qty INTEGER NOT NULL,
    warehouse TEXT NOT NULL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor TEXT NOT NULL,
    item_code TEXT NOT NULL,
    qty INTEGER NOT NULL,
    status TEXT NOT NULL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("DELETE FROM inventory")
cur.execute("DELETE FROM purchase_orders")
cur.execute("DELETE FROM audit_logs")

cur.executemany(
    "INSERT INTO inventory(item_code, item_name, qty, warehouse) VALUES (?, ?, ?, ?)",
    [
        ("ITEM-001", "모터", 120, "WH-A"),
        ("ITEM-002", "센서", 8, "WH-A"),
        ("ITEM-003", "제어보드", 35, "WH-B"),
    ]
)

cur.executemany(
    "INSERT INTO purchase_orders(vendor, item_code, qty, status) VALUES (?, ?, ?, ?)",
    [
        ("Alpha Parts", "ITEM-001", 50, "APPROVED"),
        ("Beta Tech", "ITEM-002", 100, "PENDING"),
        ("Gamma Systems", "ITEM-003", 25, "APPROVED"),
    ]
)

con.commit()
con.close()

print("erp.db 초기화 완료")
