"""Agent 数据库查询工具测试。

使用临时 SQLite 数据库进行隔离测试，不污染正式数据库（literary_atlas.db）。

运行方式（在 backend/ 目录下）：
    .venv\\Scripts\\python.exe test_agent_tools.py
"""

import tempfile
from pathlib import Path

# 必须在导入 tools 之前重写 DB_PATH，让 tools 与 init_db 都指向临时库
import database
from database import get_db_connection, init_db

from agent.tools import get_book_detail, list_books, search_books, search_places

# ---------- 隔离：使用临时数据库 ----------

_tmpdir = tempfile.mkdtemp()
database.DB_PATH = Path(_tmpdir) / "test.db"
init_db()

# ---------- 测试统计 ----------

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


# ---------- 准备测试数据 ----------

BOOK_ID = None


def setup_data():
    global BOOK_ID
    conn = get_db_connection()
    try:
        # 1 本书
        cur = conn.execute(
            """
            INSERT INTO books
                (title, original_title, language, publication_year, description, source)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("百年孤独", "Cien años de soledad", "西班牙语", 1967,
             "魔幻现实主义代表作", "示例来源"),
        )
        BOOK_ID = cur.lastrowid

        # 1 位作者
        cur = conn.execute(
            """
            INSERT INTO authors (name, birth_year, death_year, nationality, bio)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("加西亚·马尔克斯", 1927, 2014, "哥伦比亚", "哥伦比亚作家"),
        )
        author_id = cur.lastrowid

        # 作品 ↔ 作者
        conn.execute(
            "INSERT INTO book_authors (book_id, author_id, role) VALUES (?, ?, ?)",
            (BOOK_ID, author_id, "author"),
        )

        # 虚构地点：马孔多
        cur = conn.execute(
            """
            INSERT INTO places (name, place_type, is_fictional, description)
            VALUES (?, ?, ?, ?)
            """,
            ("马孔多", "fictional", 1, "虚构小镇"),
        )
        macondo_id = cur.lastrowid

        # 现实地点：阿拉卡塔卡（城市，哥伦比亚）
        cur = conn.execute(
            """
            INSERT INTO places (name, place_type, is_fictional, country, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("阿拉卡塔卡", "city", 0, "哥伦比亚", "作者出生地"),
        )
        aracataca_id = cur.lastrowid

        # 作品 ↔ 地点（故事发生地）
        conn.execute(
            "INSERT INTO book_places (book_id, place_id, relation_type) VALUES (?, ?, ?)",
            (BOOK_ID, macondo_id, "setting"),
        )

        # 作者 ↔ 地点（出生地）
        conn.execute(
            "INSERT INTO author_places (author_id, place_id, relation_type) VALUES (?, ?, ?)",
            (author_id, aracataca_id, "birthplace"),
        )

        # 流派
        cur = conn.execute(
            "INSERT INTO genres (name, description) VALUES (?, ?)",
            ("魔幻现实主义", "文学流派"),
        )
        genre_id = cur.lastrowid

        # 作品 ↔ 流派
        conn.execute(
            "INSERT INTO book_genres (book_id, genre_id) VALUES (?, ?)",
            (BOOK_ID, genre_id),
        )

        conn.commit()
    finally:
        conn.close()


def table_counts() -> dict:
    """返回关键表的行数，用于校验工具是否为只读。"""
    tables = ["books", "authors", "places", "genres",
              "book_authors", "book_places", "book_genres", "author_places"]
    conn = get_db_connection()
    try:
        counts = {}
        for t in tables:
            counts[t] = conn.execute(f"SELECT COUNT(*) AS c FROM {t}").fetchone()["c"]
    finally:
        conn.close()
    return counts


setup_data()

# ---------- 测试开始 ----------

print("=== Agent 查询工具测试 ===\n")

# 1. 搜索存在的作品
res = search_books("百年")
check("搜索存在的作品：返回《百年孤独》",
      res["total"] >= 1 and res["items"][0]["title"] == "百年孤独")

# 2. 搜索不存在的作品
res = search_books("不存在的书")
check("搜索不存在的作品：total 为 0", res["total"] == 0 and res["items"] == [])

# 3. 关键词模糊搜索（部分关键词）
res = search_books("孤独")
check("模糊搜索：'孤独' 能匹配《百年孤独》",
      res["total"] >= 1 and any(it["title"] == "百年孤独" for it in res["items"]))

# 3b. 列出全部作品
res = list_books()
check("列出全部作品：total 为 1", res["total"] == 1)
check("列出全部作品：items[0].title 为《百年孤独》",
      len(res["items"]) == 1 and res["items"][0]["title"] == "百年孤独")

# 4. 搜索地点（虚构地点）
res = search_places("马孔多")
check("搜索地点：返回马孔多且 is_fictional=1",
      res["total"] >= 1
      and res["items"][0]["name"] == "马孔多"
      and res["items"][0]["is_fictional"] == 1
      and res["items"][0]["place_type"] == "fictional")

# 5. 根据作品 ID 查询详情
detail = get_book_detail(BOOK_ID)
authors = detail.get("authors", [])
genres = detail.get("genres", [])
places = detail.get("places", [])
check("详情：作品标题正确", detail.get("title") == "百年孤独")
check("详情：作者为加西亚·马尔克斯且角色为 author",
      len(authors) >= 1 and authors[0]["name"] == "加西亚·马尔克斯"
      and authors[0]["role"] == "author")
check("详情：作者国籍为哥伦比亚（保留在作者对象，不混入作品地点）",
      authors[0]["nationality"] == "哥伦比亚")
check("详情：作者地点关系包含出生地（阿拉卡塔卡）",
      any(p["relation_type"] == "birthplace" and p["name"] == "阿拉卡塔卡"
          for p in authors[0].get("places", [])))
check("详情：作品地点关系包含故事发生地（马孔多）",
      any(p["relation_type"] == "setting" and p["name"] == "马孔多"
          and p["is_fictional"] == 1 for p in places))
check("详情：流派包含魔幻现实主义",
      any(g["name"] == "魔幻现实主义" for g in genres))

# 6. 不存在的作品 ID
res = get_book_detail(99999)
check("不存在的作品 ID：返回 error 提示", res.get("error") == "作品不存在")

# 7. 空关键词
res = search_books("")
check("空关键词搜索作品：total 为 0", res["total"] == 0 and res["items"] == [])
res = search_places("   ")
check("纯空白关键词搜索地点：total 为 0", res["total"] == 0 and res["items"] == [])

# 8. 工具执行不修改数据库数据
before = table_counts()
search_books("百年")
search_places("马孔多")
get_book_detail(BOOK_ID)
after = table_counts()
check("工具执行后各表行数保持不变", before == after)

# ---------- 汇总 ----------

print(f"\n=== 测试汇总 ===\n总数: {PASS + FAIL}  通过: {PASS}  失败: {FAIL}")
if FAIL:
    raise SystemExit(1)
