"""种子数据导入程序测试。

使用临时 SQLite 数据库进行隔离测试，不触碰正式数据库（literary_atlas.db）。

运行方式（在 backend/ 目录下）：
    .venv\\Scripts\\python.exe test_seed.py
"""

import copy
import sqlite3
import tempfile
from pathlib import Path

# 必须在导入 seed 之前重写 DB_PATH，让 seed 与 init_db 都指向临时库
import database
from database import get_db_connection, init_db

import seed

# ---------- 隔离：使用临时数据库 ----------

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


def fresh_db() -> None:
    """切换到全新的临时数据库并建表。"""
    d = tempfile.mkdtemp()
    database.DB_PATH = Path(d) / "test.db"
    init_db()


def table_counts() -> dict:
    """返回各业务表（不含 reading_records 与内部表）的行数。"""
    tables = ["books", "authors", "genres", "places",
              "book_authors", "book_genres", "book_places", "author_places"]
    conn = get_db_connection()
    try:
        counts = {}
        for t in tables:
            counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    finally:
        conn.close()
    return counts


def _get_id(conn, table: str, col: str, val) -> int | None:
    row = conn.execute(
        f"SELECT id FROM {table} WHERE {col} = ?", (val,)
    ).fetchone()
    return row[0] if row is not None else None


# 首次导入前，建立临时库
fresh_db()

# 期望行数 = SEED_DATA 中各列表长度（数据补齐后自动随之更新）
EXPECTED = {
    "books": len(seed.SEED_DATA["books"]),
    "authors": len(seed.SEED_DATA["authors"]),
    "genres": len(seed.SEED_DATA["genres"]),
    "places": len(seed.SEED_DATA["places"]),
    "book_authors": len(seed.SEED_DATA["book_authors"]),
    "book_genres": len(seed.SEED_DATA["book_genres"]),
    "book_places": len(seed.SEED_DATA["book_places"]),
    "author_places": len(seed.SEED_DATA["author_places"]),
}

# ---------- 测试开始 ----------

print("=== 种子数据导入测试 ===\n")

# 1. 首次导入，各表数量正确
conn = get_db_connection()
try:
    seed.seed_data(conn)
finally:
    conn.close()

counts1 = table_counts()
for t, expected in EXPECTED.items():
    check(f"首次导入：{t} 数量为 {expected}", counts1[t] == expected)

# 2. 再次导入，不产生重复数据
conn = get_db_connection()
try:
    seed.seed_data(conn)
finally:
    conn.close()

counts2 = table_counts()
check("再次导入：各表行数不变（幂等）", counts2 == counts1)

# 3. 关联关系指向正确的作品 / 作者 / 地点
conn = get_db_connection()
try:
    book_id = _get_id(conn, "books", "title", "百年孤独")
    macondo_id = _get_id(conn, "places", "name", "马孔多")
    bp_row = conn.execute(
        "SELECT relation_type FROM book_places "
        "WHERE book_id = ? AND place_id = ?",
        (book_id, macondo_id),
    ).fetchone()
    check("关联正确：《百年孤独》-> 马孔多 为 setting",
          bp_row is not None and bp_row[0] == "setting")

    # 战争与和平 关联 3 个地点
    wp_id = _get_id(conn, "books", "title", "战争与和平")
    wp_places = conn.execute(
        "SELECT COUNT(*) FROM book_places WHERE book_id = ?", (wp_id,)
    ).fetchone()[0]
    check("关联正确：《战争与和平》关联 3 个地点", wp_places == 3)

    # book_authors：百年孤独 -> 加夫列尔·加西亚·马尔克斯，角色 author
    marquez_id = _get_id(conn, "authors", "name", "加夫列尔·加西亚·马尔克斯")
    ba_row = conn.execute(
        "SELECT role FROM book_authors WHERE book_id = ? AND author_id = ?",
        (book_id, marquez_id),
    ).fetchone()
    check("关联正确：book_authors 角色为 author",
          ba_row is not None and ba_row[0] == "author")
finally:
    conn.close()

# 4. 所有地点关联记录的核验状态均为 unverified
conn = get_db_connection()
try:
    n_book_places = conn.execute("SELECT COUNT(*) FROM book_places").fetchone()[0]
    n_author_places = conn.execute("SELECT COUNT(*) FROM author_places").fetchone()[0]
    bad_book = conn.execute(
        "SELECT COUNT(*) FROM book_places WHERE verification_status <> 'unverified'"
    ).fetchone()[0]
    bad_author = conn.execute(
        "SELECT COUNT(*) FROM author_places WHERE verification_status <> 'unverified'"
    ).fetchone()[0]
    check("核验状态：book_places 全部为 unverified", bad_book == 0)
    check("核验状态：author_places 全部为 unverified", bad_author == 0)
    print(f"      （当前 book_places={n_book_places}，author_places={n_author_places}）")
finally:
    conn.close()

# 5. 外键检查通过（PRAGMA foreign_key_check 无结果）
conn = get_db_connection()
try:
    fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    check("外键检查：无违规记录", len(fk_violations) == 0)
finally:
    conn.close()

# 6. 不修改 reading_records（保持空，且导入逻辑从不写该表）
conn = get_db_connection()
try:
    rr = conn.execute("SELECT COUNT(*) FROM reading_records").fetchone()[0]
    check("保护个人数据：reading_records 未被写入", rr == 0)
finally:
    conn.close()

# 7. 人为触发异常时事务回滚（使用全新临时库 + 非法 parent_place_id 触发外键失败）
fresh_db()
bad_data = copy.deepcopy(seed.SEED_DATA)
bad_data["places"].append({
    "name": "非法地点", "place_type": "city", "is_fictional": 0,
    "latitude": None, "longitude": None, "country": None, "region": None,
    "parent_place_id": 99999, "description": "用于触发外键失败",
})

raised = False
conn = get_db_connection()
try:
    try:
        seed.seed_data(conn, bad_data)
    except sqlite3.IntegrityError:
        raised = True
finally:
    conn.close()
check("人为触发异常：抛出 IntegrityError", raised)

conn = get_db_connection()
try:
    n_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    n_authors = conn.execute("SELECT COUNT(*) FROM authors").fetchone()[0]
    n_places = conn.execute("SELECT COUNT(*) FROM places").fetchone()[0]
finally:
    conn.close()
check("事务回滚：异常后 books 表为空", n_books == 0)
check("事务回滚：异常后 authors 表为空", n_authors == 0)
check("事务回滚：异常后 places 表为空", n_places == 0)

# ---------- 汇总 ----------

print(f"\n=== 测试汇总 ===\n总数: {PASS + FAIL}  通过: {PASS}  失败: {FAIL}")
if FAIL:
    raise SystemExit(1)
