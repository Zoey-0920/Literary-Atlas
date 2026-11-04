"""Agent 阅读工具（get_reading_records / get_reading_statistics）测试。

使用临时 SQLite 数据库隔离，验证只读工具能正确读取演示用户的阅读记录，
并遵守用户隔离（不返回其他用户的记录）。

运行方式（在 backend/ 目录下）：
    .venv\\Scripts\\python.exe test_reading_tools.py
"""

import tempfile
from pathlib import Path

import database
from database import get_db_connection, init_db

_tmpdir = tempfile.mkdtemp()
database.DB_PATH = Path(_tmpdir) / "test.db"
init_db()

from config import DEMO_USER_ID
from seed import seed_data
from agent.tools import get_reading_records, get_reading_statistics

# 准备数据：导入种子 + 写入演示用户与另一用户的阅读记录
conn = get_db_connection()
try:
    seed_data(conn)
    book1 = conn.execute("SELECT id FROM books WHERE title = '百年孤独'").fetchone()["id"]
    book2 = conn.execute("SELECT id FROM books WHERE title = '老人与海'").fetchone()["id"]
    book3 = conn.execute("SELECT id FROM books WHERE title = '1984'").fetchone()["id"]

    conn.execute(
        "INSERT INTO reading_records (user_id, book_id, status, rating, progress) "
        "VALUES (?, ?, 'reading', 5, 40)",
        (DEMO_USER_ID, book1),
    )
    conn.execute(
        "INSERT INTO reading_records (user_id, book_id, status) VALUES (?, ?, 'want_to_read')",
        (DEMO_USER_ID, book2),
    )
    conn.execute(
        "INSERT INTO reading_records (user_id, book_id, status) VALUES (?, ?, 'finished')",
        ("other_user", book3),
    )
    conn.commit()
finally:
    conn.close()

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


print("=== Agent 阅读工具测试 ===\n")

# 1. 读取演示用户全部记录（不包含其他用户）
res = get_reading_records()
check("get_reading_records 返回 2 条", res["total"] == 2)
check("记录含书名", all("book_title" in it for it in res["items"]))

# 2. 按状态筛选
res = get_reading_records(status="reading")
check("按 reading 筛选返回 1 条", res["total"] == 1)
check("筛选结果书名正确", res["items"][0]["book_title"] == "百年孤独")
check("筛选结果含评分与进度", res["items"][0]["rating"] == 5 and res["items"][0]["progress"] == 40)

res = get_reading_records(status="finished")
check("演示用户 finished 为 0", res["total"] == 0)

# 3. 统计
stats = get_reading_statistics()
check("统计总数正确", stats["total"] == 2)
check("统计 reading 正确", stats["reading"] == 1)
check("统计 want_to_read 正确", stats["want_to_read"] == 1)
check("统计 finished 正确（不含其他用户）", stats["finished"] == 0)

# 4. 只读性：调用前后行数不变
conn = get_db_connection()
try:
    before = conn.execute("SELECT COUNT(*) AS c FROM reading_records").fetchone()["c"]
finally:
    conn.close()
get_reading_records()
get_reading_statistics()
conn = get_db_connection()
try:
    after = conn.execute("SELECT COUNT(*) AS c FROM reading_records").fetchone()["c"]
finally:
    conn.close()
check("阅读工具为只读（行数不变）", before == after == 3)

print(f"\n=== 测试汇总 ===\n总数: {PASS + FAIL}  通过: {PASS}  失败: {FAIL}")
if FAIL:
    raise SystemExit(1)
