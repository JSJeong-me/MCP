# Legacy ERP MCP Practice

## 파일 구성
- `init_db.py`: SQLite 기반 ERP 샘플 DB 생성
- `server.py`: FastMCP 기반 Legacy ERP Bridge 서버
- `test_client.py`: FastMCP Client로 서버 테스트

## WSL 실행 순서

```bash
mkdir -p ~/legacy-erp-mcp
cd ~/legacy-erp-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install fastmcp
```

파일 복사 후:

```bash
python init_db.py
python test_client.py
```

## READ_ONLY 모드 테스트

```bash
export READ_ONLY=true
python test_client.py
```

## SQLite 직접 확인

```bash
sqlite3 erp.db
SELECT * FROM inventory;
SELECT * FROM purchase_orders;
SELECT * FROM audit_logs;
.quit
```
