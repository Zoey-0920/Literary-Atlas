"""Literary Atlas 第一版 50 部作品扩充数据导入程序。

将 `expansion_data.py` 中已审核通过的数据写入 SQLite 数据库，把第一版扩充为
恰好 50 部作品。数据来源：`DATA_EXPANSION_PLAN.md` 第 1—10 节（已定稿）。

设计要点：
- 幂等性：基础实体按自然键（书名 / 作者名 / 流派名 / 地点名）先查后插；
  关联表使用 INSERT OR IGNORE 依赖现有唯一约束，重复执行不会产生重复数据。
- 事务：整个导入（含数据修正）在单个事务中完成，任一异常回滚，避免半插入状态。
- 数据修正（先于实体导入，且在同一事务内）：
  1. 《1984》→《一九八四》：按 original_title='Nineteen Eighty-Four' 匹配后 UPDATE title；
  2. 曹雪芹 birth_year / death_year 置 NULL（bio 已保留「约 1715—1763，为推定值」）；
  3. 删除陈旧关联 book_places(一九八四 → 伦敦)（真实伦敦不再作为《一九八四》故事发生地）。
- 安全：所有值均通过参数化占位符（?）写入，禁止字符串拼接 SQL 值。
- 保护：不写入 reading_records；不修改、不覆盖任何已有阅读记录。
- 核验状态：所有 book_places 的 verification_status 一律写 'unverified'。
- 统计：明确报告各类实体的新增 / 复用，以及关联的插入 / 跳过数量。

用法（正式导入前必须先在临时库跑通 test_import_expansion.py）：
    cd backend
    .venv\\Scripts\\python.exe import_expansion.py [--db 目标库路径]

    --db 缺省时指向正式库 backend/literary_atlas.db；测试时必须用 --db 指定临时库。
"""

from __future__ import annotations

import argparse
import sqlite3

import database
from expansion_data import EXPANSION_DATA


# ---------------------------------------------------------------------------
# 基础实体的写入列与自然键（与 seed.py 保持一致）
# ---------------------------------------------------------------------------

_ENTITY_COLUMNS = {
    "books": ["title", "original_title", "language", "publication_year",
              "description", "source"],
    "authors": ["name", "birth_year", "death_year", "nationality", "bio"],
    "genres": ["name", "description"],
    "places": ["name", "place_type", "is_fictional", "latitude", "longitude",
               "country", "region", "parent_place_id", "description"],
}

_ENTITY_UNIQUE_COLUMN = {
    "books": "title",
    "authors": "name",
    "genres": "name",
    "places": "name",
}


def connect(db_path) -> sqlite3.Connection:
    """建立指向指定路径的 SQLite 连接（Row 行工厂 + 开启外键）。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    """复用 database 的建表语句创建全部表结构（幂等，不覆盖已有数据）。"""
    for statement in database._SCHEMA_STATEMENTS:
        conn.execute(statement)
    database._migrate(conn)
    conn.commit()


def _get_or_create(conn: sqlite3.Connection, table: str, item: dict):
    """按自然键查找基础实体，不存在则插入；返回 (id, 是否新建)。"""
    unique_col = _ENTITY_UNIQUE_COLUMN[table]
    unique_val = item[unique_col]

    row = conn.execute(
        f"SELECT id FROM {table} WHERE {unique_col} = ?", (unique_val,)
    ).fetchone()
    if row is not None:
        return row["id"], False

    columns = _ENTITY_COLUMNS[table]
    col_names = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    values = [item.get(col) for col in columns]
    cur = conn.execute(
        f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})", values
    )
    return cur.lastrowid, True


def _insert_relation_ignore(conn: sqlite3.Connection, table: str,
                            columns: list[str], values: list) -> bool:
    """写入关联表，遇到唯一约束冲突则忽略；返回是否真正插入。"""
    col_names = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    cur = conn.execute(
        f"INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({placeholders})",
        values,
    )
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# 数据修正（先于实体导入，与实体导入处于同一事务）
# ---------------------------------------------------------------------------

def _fix_book_title(conn: sqlite3.Connection) -> str:
    """《1984》→《一九八四》（按 original_title 匹配）。返回结果标记。"""
    row = conn.execute(
        "SELECT id, title FROM books WHERE original_title = ?",
        ("Nineteen Eighty-Four",),
    ).fetchone()
    if row is None:
        return "no_match"
    if row["title"] == "一九八四":
        return "already"
    conn.execute(
        "UPDATE books SET title = ? WHERE id = ?", ("一九八四", row["id"])
    )
    return "renamed"


def _fix_cao_xueqin_years(conn: sqlite3.Connection) -> str:
    """曹雪芹 birth_year / death_year 置 NULL。返回结果标记。"""
    row = conn.execute(
        "SELECT id, birth_year, death_year FROM authors WHERE name = ?",
        ("曹雪芹",),
    ).fetchone()
    if row is None:
        return "no_match"
    if row["birth_year"] is None and row["death_year"] is None:
        return "already"
    conn.execute(
        "UPDATE authors SET birth_year = NULL, death_year = NULL WHERE id = ?",
        (row["id"],),
    )
    return "updated"


def _fix_delete_1984_london(conn: sqlite3.Connection) -> int:
    """删除《一九八四/1984》与真实「伦敦」的 setting 关联；返回删除条数。"""
    cur = conn.execute(
        """
        DELETE FROM book_places
        WHERE relation_type = 'setting'
          AND book_id IN (SELECT id FROM books WHERE title IN ('一九八四', '1984'))
          AND place_id IN (SELECT id FROM places WHERE name = '伦敦')
        """
    )
    return cur.rowcount


# ---------------------------------------------------------------------------
# 主导入流程
# ---------------------------------------------------------------------------

def import_expansion(conn: sqlite3.Connection, data: dict | None = None) -> dict:
    """在单个事务中完成数据修正 + 实体导入 + 关联导入，返回统计报告。

    任一步骤抛出异常都会触发 rollback（含数据修正），保证不会出现半插入状态。
    conn 必须来自 connect() / database.get_db_connection()（已开启外键、已建表）。
    """
    data = data if data is not None else EXPANSION_DATA

    report = {
        "fixes": {},
        "genres": {"created": 0, "reused": 0},
        "authors": {"created": 0, "reused": 0},
        "places": {"created": 0, "reused": 0},
        "books": {"created": 0, "reused": 0},
        "book_authors": {"inserted": 0, "skipped": 0},
        "book_genres": {"inserted": 0, "skipped": 0},
        "book_places": {"inserted": 0, "skipped": 0},
        "failed": 0,
    }

    book_ids: dict[str, int] = {}
    author_ids: dict[str, int] = {}
    genre_ids: dict[str, int] = {}
    place_ids: dict[str, int] = {}

    try:
        # 0. 数据修正（与导入同事务，失败一并回滚）
        report["fixes"]["book_title_1984"] = _fix_book_title(conn)
        report["fixes"]["cao_xueqin_years"] = _fix_cao_xueqin_years(conn)
        report["fixes"]["deleted_1984_london"] = _fix_delete_1984_london(conn)

        # 1. 基础实体：按自然键先查后插
        for g in data["genres"]:
            genre_ids[g["name"]], created = _get_or_create(conn, "genres", g)
            report["genres"]["created" if created else "reused"] += 1
        for a in data["authors"]:
            author_ids[a["name"]], created = _get_or_create(conn, "authors", a)
            report["authors"]["created" if created else "reused"] += 1
        for p in data["places"]:
            place_ids[p["name"]], created = _get_or_create(conn, "places", p)
            report["places"]["created" if created else "reused"] += 1
        for b in data["books"]:
            book_ids[b["title"]], created = _get_or_create(conn, "books", b)
            report["books"]["created" if created else "reused"] += 1

        # 2. 关联表：通过已解析 id 写入，唯一约束冲突即跳过
        for ba in data["book_authors"]:
            inserted = _insert_relation_ignore(
                conn, "book_authors",
                ["book_id", "author_id", "role"],
                [book_ids[ba["book_title"]], author_ids[ba["author_name"]],
                 ba.get("role")],
            )
            report["book_authors"]["inserted" if inserted else "skipped"] += 1
        for bg in data["book_genres"]:
            inserted = _insert_relation_ignore(
                conn, "book_genres",
                ["book_id", "genre_id"],
                [book_ids[bg["book_title"]], genre_ids[bg["genre_name"]]],
            )
            report["book_genres"]["inserted" if inserted else "skipped"] += 1
        for bp in data["book_places"]:
            inserted = _insert_relation_ignore(
                conn, "book_places",
                ["book_id", "place_id", "relation_type", "source_name",
                 "source_url", "note", "verification_status"],
                [book_ids[bp["book_title"]], place_ids[bp["place_name"]],
                 bp["relation_type"], bp.get("source_name"), bp.get("source_url"),
                 bp.get("note"), "unverified"],
            )
            report["book_places"]["inserted" if inserted else "skipped"] += 1

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return report


def _print_report(report: dict) -> None:
    print("扩充数据导入完成：")
    print(f"  数据修正: 1984 改名 -> {report['fixes']['book_title_1984']}")
    print(f"            曹雪芹生卒年 -> {report['fixes']['cao_xueqin_years']}")
    print(f"            删除 1984→伦敦 关联 -> {report['fixes']['deleted_1984_london']} 条")
    for key, label in [
        ("genres", "流派"), ("authors", "作者"),
        ("places", "地点"), ("books", "作品"),
    ]:
        r = report[key]
        print(f"  {label}: 新增 {r['created']}，复用 {r['reused']}")
    for key, label in [
        ("book_authors", "book_authors"), ("book_genres", "book_genres"),
        ("book_places", "book_places"),
    ]:
        r = report[key]
        print(f"  {label}: 插入 {r['inserted']}，跳过 {r['skipped']}")
    print(f"  失败: {report['failed']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="导入第一版 50 部作品扩充数据（幂等、事务化）。"
    )
    parser.add_argument(
        "--db", default=None,
        help="目标数据库路径；缺省指向正式库 backend/literary_atlas.db。测试时务必指定临时库。",
    )
    args = parser.parse_args()

    db_path = args.db if args.db else str(database.DB_PATH)
    conn = connect(db_path)
    try:
        ensure_schema(conn)
        report = import_expansion(conn)
    finally:
        conn.close()

    _print_report(report)


if __name__ == "__main__":
    main()
