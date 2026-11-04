"""个人阅读记录（reading_records）HTTP 接口测试。

使用临时 SQLite 数据库隔离，不污染正式数据库。
测试覆盖：新增、列表、筛选、修改、删除、参数校验、重复添加、用户隔离。

运行方式（在 backend/ 目录下）：
    .venv\\Scripts\\python.exe test_reading.py
"""

import tempfile
from pathlib import Path

# 隔离：临时数据库（必须在导入 main 前重写 DB_PATH）
import database
from database import get_db_connection, init_db

_tmpdir = tempfile.mkdtemp()
database.DB_PATH = Path(_tmpdir) / "test.db"
init_db()

# 导入种子数据，让作品真实存在，供阅读记录引用
from seed import seed_data

_conn = get_db_connection()
try:
    seed_data(_conn)
finally:
    _conn.close()

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

PASS = 0
FAIL = 0


def check(name: str, cond: bool):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name}")


print("=== 个人阅读记录 HTTP 接口测试 ===\n")

# 取一本真实作品 ID
conn = get_db_connection()
try:
    BOOK_ID = conn.execute("SELECT id FROM books WHERE title = '百年孤独'").fetchone()["id"]
    BOOK_ID_2 = conn.execute("SELECT id FROM books WHERE title = '老人与海'").fetchone()["id"]
finally:
    conn.close()

# ---------- 1. 新增到书架 ----------
resp = client.post("/api/reading", json={"book_id": BOOK_ID, "status": "reading", "progress": 30})
check("新增书架记录返回 201", resp.status_code == 201)
data = resp.json()
check("新增记录包含书名", data.get("book_title") == "百年孤独")
check("新增记录状态正确", data.get("status") == "reading")
check("新增记录进度正确", data.get("progress") == 30)
RECORD_ID = data.get("id")

# ---------- 2. 重复添加同一本书 ----------
resp = client.post("/api/reading", json={"book_id": BOOK_ID, "status": "want_to_read"})
check("重复添加同一本书返回 409", resp.status_code == 409)

# ---------- 3. 添加不存在的作品 ----------
resp = client.post("/api/reading", json={"book_id": 99999, "status": "reading"})
check("添加不存在作品返回 404", resp.status_code == 404)

# ---------- 4. 参数校验 ----------
resp = client.post("/api/reading", json={"book_id": BOOK_ID_2, "status": "invalid_status"})
check("非法状态返回 422", resp.status_code == 422)
resp = client.post("/api/reading", json={"book_id": BOOK_ID_2, "status": "reading", "rating": 6})
check("评分越界返回 422", resp.status_code == 422)
resp = client.post("/api/reading", json={"book_id": BOOK_ID_2, "status": "reading", "progress": 101})
check("进度越界返回 422", resp.status_code == 422)

# ---------- 5. 列表与筛选 ----------
resp = client.get("/api/reading")
check("书架列表返回 200", resp.status_code == 200)
check("书架列表总数正确", resp.json().get("total") == 1)

resp = client.get("/api/reading", params={"status": "reading"})
check("按 reading 筛选返回 1 条", resp.json().get("total") == 1)
resp = client.get("/api/reading", params={"status": "finished"})
check("按 finished 筛选返回 0 条", resp.json().get("total") == 0)

# ---------- 6. 修改记录 ----------
resp = client.patch(f"/api/reading/{RECORD_ID}", json={"rating": 5, "progress": 80, "note": "很好看"})
check("修改记录返回 200", resp.status_code == 200)
check("评分已更新", resp.json().get("rating") == 5)
check("进度已更新", resp.json().get("progress") == 80)
check("笔记已更新", resp.json().get("note") == "很好看")
check("未提供的状态保持不变", resp.json().get("status") == "reading")

resp = client.patch(f"/api/reading/{RECORD_ID}", json={"status": "finished"})
check("修改状态为 finished", resp.status_code == 200 and resp.json().get("status") == "finished")

# ---------- 7. 修改不存在的记录 ----------
resp = client.patch("/api/reading/99999", json={"status": "reading"})
check("修改不存在记录返回 404", resp.status_code == 404)

# ---------- 8. 用户隔离 ----------
conn = get_db_connection()
try:
    cur = conn.execute(
        "INSERT INTO reading_records (user_id, book_id, status) VALUES (?, ?, ?)",
        ("other_user", BOOK_ID_2, "reading"),
    )
    OTHER_ID = cur.lastrowid
    conn.commit()
finally:
    conn.close()

resp = client.get("/api/reading")
check("列表不包含其他用户的记录", all(it["book_id"] != BOOK_ID_2 for it in resp.json()["items"]))
resp = client.patch(f"/api/reading/{OTHER_ID}", json={"status": "finished"})
check("不能修改其他用户的记录（404）", resp.status_code == 404)
resp = client.delete(f"/api/reading/{OTHER_ID}")
check("不能删除其他用户的记录（404）", resp.status_code == 404)

# ---------- 9. 删除记录 ----------
resp = client.delete(f"/api/reading/{RECORD_ID}")
check("删除记录返回 204", resp.status_code == 204)
resp = client.get("/api/reading")
check("删除后列表为空（不含其他用户）", resp.json().get("total") == 0)

resp = client.delete(f"/api/reading/{RECORD_ID}")
check("删除不存在的记录返回 404", resp.status_code == 404)

print(f"\n=== 测试汇总 ===\n总数: {PASS + FAIL}  通过: {PASS}  失败: {FAIL}")
if FAIL:
    raise SystemExit(1)
