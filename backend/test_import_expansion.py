"""扩充数据导入程序测试。

使用临时 SQLite 数据库进行隔离测试，不触碰正式数据库（literary_atlas.db）。

测试在「现有 6 部种子数据」之上执行扩充导入，覆盖：
- 最终作品数量恰好 50；
- 作者 / 流派 / 地点 / 各关联表无意外重复；
- 外键关系有效；
- 50 部作品都正确关联作者（且每部作品都有流派与地点）；
- 虚构地点无经纬度、未核实坐标未被擅自填入；
- reading_records 不被修改；
- 连续运行两次不重复导入（幂等）；
- 人为制造导入错误时能够回滚。

运行方式（在 backend/ 目录下）：
    .venv\\Scripts\\python.exe test_import_expansion.py
"""

import copy
import sqlite3
import tempfile
from pathlib import Path

# 必须在导入其它模块前重写 DB_PATH，让 database / seed 指向临时库
import database
from database import get_db_connection, init_db

import seed
import import_expansion
import expansion_data

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


def _get_id(conn, table: str, col: str, val):
    row = conn.execute(
        f"SELECT id FROM {table} WHERE {col} = ?", (val,)
    ).fetchone()
    return row[0] if row is not None else None


# ---------- 数据文件自检（防止数据漂移） ----------

D = expansion_data.EXPANSION_DATA
print("=== 数据文件自检 ===\n")
check("数据文件：books 数量为 50", len(D["books"]) == 50)
check("数据文件：authors 数量为 46", len(D["authors"]) == 46)
check("数据文件：genres 数量为 12", len(D["genres"]) == 12)
check("数据文件：places 数量为 71（14 虚构 + 57 真实）", len(D["places"]) == 71)
check("数据文件：book_authors 数量为 50", len(D["book_authors"]) == 50)
check("数据文件：book_genres 数量为 56", len(D["book_genres"]) == 56)
check("数据文件：book_places 数量为 81", len(D["book_places"]) == 81)
fictional = sum(1 for p in D["places"] if p["is_fictional"] == 1)
real = sum(1 for p in D["places"] if p["is_fictional"] == 0)
check(f"数据文件：虚构 {fictional} + 真实 {real} 构成 71", fictional == 14 and real == 57)

# ---------- 首次导入前，建立临时库并导入种子数据 ----------

fresh_db()
conn = get_db_connection()
try:
    seed.seed_data(conn)
finally:
    conn.close()

# 期望最终行数（在 6 部种子之上扩充后）
EXPECTED_FINAL = {
    "books": 50,
    "authors": 46,
    "genres": 12,
    "places": 77,          # 16 种子 + 61 新增（71 扩充 - 10 复用）
    "book_authors": 50,    # 6 种子 + 50 扩充 - 6 复用
    "book_genres": 56,     # 6 种子 + 56 扩充 - 6 复用
    "book_places": 81,     # 10 种子 - 1 删除(1984→伦敦) + 81 扩充 - 9 复用
    "author_places": 8,    # 本轮不扩展
}

print("\n=== 扩充数据导入测试 ===\n")

# 1. 首次导入，各表数量正确
conn = get_db_connection()
try:
    report1 = import_expansion.import_expansion(conn)
finally:
    conn.close()

counts1 = table_counts()
for t, expected in EXPECTED_FINAL.items():
    check(f"首次导入：{t} 数量为 {expected}", counts1[t] == expected)

# 2. 再次导入，不产生重复数据（幂等）
conn = get_db_connection()
try:
    report2 = import_expansion.import_expansion(conn)
finally:
    conn.close()

counts2 = table_counts()
check("再次导入：各表行数不变（幂等）", counts2 == counts1)
check("再次导入：无新增实体与关联",
      all(report2[k]["created"] == 0 and report2[k]["reused"] > 0
          for k in ("books", "authors", "genres", "places"))
      and all(report2[k]["inserted"] == 0 for k in
              ("book_authors", "book_genres", "book_places")))

# 3. 50 部作品都正确关联作者、流派、地点
conn = get_db_connection()
try:
    no_author = conn.execute(
        "SELECT COUNT(*) FROM books b WHERE NOT EXISTS "
        "(SELECT 1 FROM book_authors ba WHERE ba.book_id = b.id)"
    ).fetchone()[0]
    no_genre = conn.execute(
        "SELECT COUNT(*) FROM books b WHERE NOT EXISTS "
        "(SELECT 1 FROM book_genres bg WHERE bg.book_id = b.id)"
    ).fetchone()[0]
    no_place = conn.execute(
        "SELECT COUNT(*) FROM books b WHERE NOT EXISTS "
        "(SELECT 1 FROM book_places bp WHERE bp.book_id = b.id)"
    ).fetchone()[0]
    check("50 部作品均关联 ≥1 位作者", no_author == 0)
    check("50 部作品均关联 ≥1 个流派", no_genre == 0)
    check("50 部作品均关联 ≥1 个地点", no_place == 0)
finally:
    conn.close()

# 4. 数据修正：1984 → 一九八四，且无残留「1984」标题
conn = get_db_connection()
try:
    n_1984 = conn.execute(
        "SELECT COUNT(*) FROM books WHERE title = '1984'"
    ).fetchone()[0]
    n_1984_zh = conn.execute(
        "SELECT COUNT(*) FROM books WHERE title = '一九八四'"
    ).fetchone()[0]
    check("数据修正：《1984》已不存在", n_1984 == 0)
    check("数据修正：《一九八四》存在且唯一", n_1984_zh == 1)

    # 一九八四 只关联 大洋国 + 大洋国伦敦，不再关联真实伦敦
    book_id = _get_id(conn, "books", "title", "一九八四")
    london_id = _get_id(conn, "places", "name", "伦敦")
    oceania_london = conn.execute(
        "SELECT COUNT(*) FROM book_places WHERE book_id = ? "
        "AND place_id = ?", (book_id, london_id)
    ).fetchone()[0]
    check("数据修正：一九八四不再关联真实伦敦", oceania_london == 0)
    bp_names = {r["name"] for r in conn.execute(
        "SELECT p.name FROM book_places bp JOIN places p ON p.id = bp.place_id "
        "WHERE bp.book_id = ?", (book_id,)
    ).fetchall()}
    check("数据修正：一九八四地点为 {大洋国, 大洋国伦敦}",
          bp_names == {"大洋国", "大洋国伦敦"})
finally:
    conn.close()

# 5. 曹雪芹生卒年置 NULL
conn = get_db_connection()
try:
    row = conn.execute(
        "SELECT birth_year, death_year FROM authors WHERE name = '曹雪芹'"
    ).fetchone()
    check("数据修正：曹雪芹生卒年为 NULL",
          row is not None and row["birth_year"] is None and row["death_year"] is None)
finally:
    conn.close()

# 6. 虚构地点无经纬度；未核实坐标未被擅自填入
conn = get_db_connection()
try:
    fictional_with_coord = conn.execute(
        "SELECT COUNT(*) FROM places WHERE is_fictional = 1 "
        "AND (latitude IS NOT NULL OR longitude IS NOT NULL)"
    ).fetchone()[0]
    real_with_coord = conn.execute(
        "SELECT COUNT(*) FROM places WHERE is_fictional = 0 "
        "AND latitude IS NOT NULL AND longitude IS NOT NULL"
    ).fetchone()[0]
    real_without_coord = conn.execute(
        "SELECT COUNT(*) FROM places WHERE is_fictional = 0 "
        "AND (latitude IS NULL OR longitude IS NULL)"
    ).fetchone()[0]
    check("虚构地点：全部无经纬度", fictional_with_coord == 0)
    check(
        "坐标规则：55 个已核实真实地点有坐标，8 个待确认项无坐标",
        real_with_coord == 55 and real_without_coord == 8,
    )
finally:
    conn.close()

# 7. 核验状态全部 unverified
conn = get_db_connection()
try:
    bad_bp = conn.execute(
        "SELECT COUNT(*) FROM book_places WHERE verification_status <> 'unverified'"
    ).fetchone()[0]
    bad_ap = conn.execute(
        "SELECT COUNT(*) FROM author_places WHERE verification_status <> 'unverified'"
    ).fetchone()[0]
    check("核验状态：book_places 全部 unverified", bad_bp == 0)
    check("核验状态：author_places 全部 unverified", bad_ap == 0)
finally:
    conn.close()

# 8. 外键检查通过
conn = get_db_connection()
try:
    fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    check("外键检查：无违规记录", len(fk_violations) == 0)
finally:
    conn.close()

# 9. 不修改 reading_records
conn = get_db_connection()
try:
    rr = conn.execute("SELECT COUNT(*) FROM reading_records").fetchone()[0]
    check("保护个人数据：reading_records 未被写入", rr == 0)
finally:
    conn.close()

# 10. 人为触发异常时事务回滚（全新临时库 + 非法 parent_place_id 触发外键失败）
fresh_db()
conn = get_db_connection()
try:
    seed.seed_data(conn)
finally:
    conn.close()

bad_data = copy.deepcopy(expansion_data.EXPANSION_DATA)
bad_data["places"].append({
    "name": "非法地点", "place_type": "city", "is_fictional": 0,
    "latitude": None, "longitude": None, "country": None, "region": None,
    "parent_place_id": 99999, "description": "用于触发外键失败",
})

raised = False
conn = get_db_connection()
try:
    try:
        import_expansion.import_expansion(conn, bad_data)
    except sqlite3.IntegrityError:
        raised = True
finally:
    conn.close()
check("人为触发异常：抛出 IntegrityError", raised)

conn = get_db_connection()
try:
    n_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    title_1984 = conn.execute(
        "SELECT COUNT(*) FROM books WHERE title = '1984'"
    ).fetchone()[0]
    cao = conn.execute(
        "SELECT birth_year, death_year FROM authors WHERE name = '曹雪芹'"
    ).fetchone()
finally:
    conn.close()
check("事务回滚：异常后 books 回到 6（种子数据）", n_books == 6)
check("事务回滚：改名未生效（仍为 1984）", title_1984 == 1)
check("事务回滚：曹雪芹生卒年未被改动",
      cao is not None and cao["birth_year"] == 1715 and cao["death_year"] == 1763)

# ---------- 汇总 ----------

print(f"\n=== 测试汇总 ===\n总数: {PASS + FAIL}  通过: {PASS}  失败: {FAIL}")
if FAIL:
    raise SystemExit(1)
