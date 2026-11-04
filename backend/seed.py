"""Literary Atlas 文学种子数据导入程序。

将审核通过的文学种子数据写入 SQLite 数据库。

设计要点：
- 幂等性：基础实体按自然键（书名 / 作者名 / 流派名 / 地点名）先查后插；
  关联表使用 INSERT OR IGNORE 依赖现有唯一约束，重复执行不会产生重复数据。
- 事务：整个导入在单个事务中完成，任一异常回滚，避免出现半插入状态。
- 安全：所有值均通过参数化占位符（?）写入，禁止字符串拼接 SQL 值。
- 保护：不写入 reading_records，不删除、覆盖或修改任何已有数据。
- 核验状态：所有 book_places / author_places 的 verification_status 一律写为
  'unverified'，不读取数据中的该字段，避免误标为已核验。

数据说明：已按审核通过的最终方案补全全部种子数据。
source / source_name / source_url / note 保持 NULL，不编造来源；
不确定的年份保持 NULL。

用法（仅在数据确认齐全后手动执行正式导入）：
    cd backend
    .venv\\Scripts\\python.exe seed.py
"""

from __future__ import annotations

import sqlite3

from database import get_db_connection, init_db


# ---------------------------------------------------------------------------
# 种子数据
#
# 结构约定：
# - books / authors / genres / places 为「基础实体」，通过自然键查重。
# - book_authors / book_genres / book_places / author_places 为「关联表」，
#   通过 book_title / author_name / genre_name / place_name 引用基础实体。
#
# 最终方案：6 部作品、6 位作者、6 个流派、16 处地点（country 2 + city 8 +
# fictional 6）、6 条 book_authors、6 条 book_genres、10 条 book_places、8 条
# author_places。所有 book_places / author_places 均为 unverified。
#
# 说明：
#   - source / source_name / source_url / note 一律保持 NULL，不得编造网址或
#     声称已完成来源核验。
#   - 不确定的年份（author_places.start_year / end_year）保持 NULL。
# ---------------------------------------------------------------------------

SEED_DATA = {
    "books": [
        {"title": "百年孤独", "original_title": "Cien años de soledad",
         "language": "西班牙语", "publication_year": 1967,
         "description": "加西亚·马尔克斯代表作，魔幻现实主义经典。", "source": None},
        {"title": "战争与和平", "original_title": "Война и мир",
         "language": "俄语", "publication_year": 1869,
         "description": "托尔斯泰长篇小说，以拿破仑战争为背景。", "source": None},
        {"title": "1984", "original_title": "Nineteen Eighty-Four",
         "language": "英语", "publication_year": 1949,
         "description": "乔治·奥威尔的反乌托邦小说。", "source": None},
        {"title": "神曲", "original_title": "La Divina Commedia",
         "language": "意大利语", "publication_year": 1472,
         "description": "但丁的叙事长诗，分地狱、炼狱、天堂三篇。", "source": None},
        {"title": "红楼梦", "original_title": None,
         "language": "中文", "publication_year": 1791,
         "description": "曹雪芹章回体小说，中国古典文学高峰。", "source": None},
        {"title": "老人与海", "original_title": "The Old Man and the Sea",
         "language": "英语", "publication_year": 1952,
         "description": "海明威的中篇小说。", "source": None},
    ],
    "authors": [
        {"name": "加夫列尔·加西亚·马尔克斯", "birth_year": 1927, "death_year": 2014,
         "nationality": "哥伦比亚", "bio": "哥伦比亚作家。"},
        {"name": "列夫·托尔斯泰", "birth_year": 1828, "death_year": 1910,
         "nationality": "俄国", "bio": "俄国作家。"},
        {"name": "乔治·奥威尔", "birth_year": 1903, "death_year": 1950,
         "nationality": "英国", "bio": "英国作家。"},
        {"name": "但丁·阿利吉耶里", "birth_year": 1265, "death_year": 1321,
         "nationality": "意大利", "bio": "意大利诗人。"},
        # 曹雪芹生卒年为推定，需在 bio 中说明
        {"name": "曹雪芹", "birth_year": 1715, "death_year": 1763,
         "nationality": "中国", "bio": "清代小说家；生卒年约 1715—1763，为推定值。"},
        {"name": "欧内斯特·海明威", "birth_year": 1899, "death_year": 1961,
         "nationality": "美国", "bio": "美国作家。"},
    ],
    "genres": [
        {"name": "魔幻现实主义", "description": "将现实与奇幻融合的文学流派。"},
        {"name": "现实主义", "description": "真实反映社会生活的文学流派。"},
        {"name": "现代主义", "description": "注重形式实验与主观体验的文学流派。"},
        {"name": "反乌托邦", "description": "描绘极权、压抑的未来社会的文学流派。"},
        {"name": "史诗", "description": "长篇叙事诗歌体裁，以重大历史或传奇为题材。"},
        {"name": "章回体小说", "description": "中国传统分章回叙事的长篇小说体裁。"},
    ],
    "places": [
        # --- 虚构地点（place_type=fictional，is_fictional=1，无经纬度）---
        {"name": "马孔多", "place_type": "fictional", "is_fictional": 1,
         "latitude": None, "longitude": None, "country": None, "region": None,
         "parent_place_id": None, "description": "《百年孤独》虚构小镇。"},
        {"name": "大洋国", "place_type": "fictional", "is_fictional": 1,
         "latitude": None, "longitude": None, "country": None, "region": None,
         "parent_place_id": None, "description": "《1984》虚构国家。"},
        {"name": "地狱", "place_type": "fictional", "is_fictional": 1,
         "latitude": None, "longitude": None, "country": None, "region": None,
         "parent_place_id": None, "description": "《神曲》叙事空间。"},
        {"name": "炼狱", "place_type": "fictional", "is_fictional": 1,
         "latitude": None, "longitude": None, "country": None, "region": None,
         "parent_place_id": None, "description": "《神曲》叙事空间。"},
        {"name": "天堂", "place_type": "fictional", "is_fictional": 1,
         "latitude": None, "longitude": None, "country": None, "region": None,
         "parent_place_id": None, "description": "《神曲》叙事空间。"},
        {"name": "大观园", "place_type": "fictional", "is_fictional": 1,
         "latitude": None, "longitude": None, "country": None, "region": None,
         "parent_place_id": None, "description": "《红楼梦》虚构园林。"},
        # --- 现实地点 ---
        {"name": "俄罗斯", "place_type": "country", "is_fictional": 0,
         "latitude": None, "longitude": None, "country": None, "region": None,
         "parent_place_id": None, "description": "国家。"},
        {"name": "莫斯科", "place_type": "city", "is_fictional": 0,
         "latitude": None, "longitude": None, "country": "俄罗斯", "region": None,
         "parent_place_id": None, "description": "城市。"},
        {"name": "圣彼得堡", "place_type": "city", "is_fictional": 0,
         "latitude": None, "longitude": None, "country": "俄罗斯", "region": None,
         "parent_place_id": None, "description": "城市。"},
        {"name": "伦敦", "place_type": "city", "is_fictional": 0,
         "latitude": None, "longitude": None, "country": "英国", "region": None,
         "parent_place_id": None, "description": "城市。"},
        {"name": "古巴", "place_type": "country", "is_fictional": 0,
         "latitude": None, "longitude": None, "country": None, "region": None,
         "parent_place_id": None, "description": "国家。"},
        {"name": "阿拉卡塔卡", "place_type": "city", "is_fictional": 0,
         "latitude": None, "longitude": None, "country": "哥伦比亚", "region": None,
         "parent_place_id": None, "description": "城市。"},
        {"name": "墨西哥城", "place_type": "city", "is_fictional": 0,
         "latitude": None, "longitude": None, "country": "墨西哥", "region": None,
         "parent_place_id": None, "description": "城市。"},
        {"name": "奥克帕克", "place_type": "city", "is_fictional": 0,
         "latitude": None, "longitude": None, "country": "美国", "region": None,
         "parent_place_id": None, "description": "城市。"},
        {"name": "莫蒂哈里", "place_type": "city", "is_fictional": 0,
         "latitude": None, "longitude": None, "country": "印度", "region": None,
         "parent_place_id": None, "description": "城市。"},
        {"name": "佛罗伦萨", "place_type": "city", "is_fictional": 0,
         "latitude": None, "longitude": None, "country": "意大利", "region": None,
         "parent_place_id": None, "description": "城市。"},
    ],
    "book_authors": [
        {"book_title": "百年孤独", "author_name": "加夫列尔·加西亚·马尔克斯", "role": "author"},
        {"book_title": "战争与和平", "author_name": "列夫·托尔斯泰", "role": "author"},
        {"book_title": "1984", "author_name": "乔治·奥威尔", "role": "author"},
        {"book_title": "神曲", "author_name": "但丁·阿利吉耶里", "role": "author"},
        {"book_title": "红楼梦", "author_name": "曹雪芹", "role": "author"},
        {"book_title": "老人与海", "author_name": "欧内斯特·海明威", "role": "author"},
    ],
    "book_genres": [
        {"book_title": "百年孤独", "genre_name": "魔幻现实主义"},
        {"book_title": "战争与和平", "genre_name": "现实主义"},
        {"book_title": "老人与海", "genre_name": "现代主义"},
        {"book_title": "1984", "genre_name": "反乌托邦"},
        {"book_title": "神曲", "genre_name": "史诗"},
        {"book_title": "红楼梦", "genre_name": "章回体小说"},
    ],
    "book_places": [
        {"book_title": "百年孤独", "place_name": "马孔多", "relation_type": "setting",
         "source_name": None, "source_url": None, "note": None},
        {"book_title": "战争与和平", "place_name": "俄罗斯", "relation_type": "setting",
         "source_name": None, "source_url": None, "note": None},
        {"book_title": "战争与和平", "place_name": "莫斯科", "relation_type": "setting",
         "source_name": None, "source_url": None, "note": None},
        {"book_title": "战争与和平", "place_name": "圣彼得堡", "relation_type": "setting",
         "source_name": None, "source_url": None, "note": None},
        {"book_title": "1984", "place_name": "大洋国", "relation_type": "setting",
         "source_name": None, "source_url": None, "note": None},
        {"book_title": "1984", "place_name": "伦敦", "relation_type": "setting",
         "source_name": None, "source_url": None, "note": None},
        {"book_title": "神曲", "place_name": "地狱", "relation_type": "setting",
         "source_name": None, "source_url": None, "note": None},
        {"book_title": "神曲", "place_name": "炼狱", "relation_type": "setting",
         "source_name": None, "source_url": None, "note": None},
        {"book_title": "神曲", "place_name": "天堂", "relation_type": "setting",
         "source_name": None, "source_url": None, "note": None},
        {"book_title": "红楼梦", "place_name": "大观园", "relation_type": "setting",
         "source_name": None, "source_url": None, "note": None},
    ],
    "author_places": [
        {"author_name": "加夫列尔·加西亚·马尔克斯", "place_name": "阿拉卡塔卡",
         "relation_type": "birthplace", "source_name": None, "source_url": None,
         "note": None, "start_year": None, "end_year": None},
        {"author_name": "加夫列尔·加西亚·马尔克斯", "place_name": "墨西哥城",
         "relation_type": "residence", "source_name": None, "source_url": None,
         "note": None, "start_year": None, "end_year": None},
        {"author_name": "加夫列尔·加西亚·马尔克斯", "place_name": "墨西哥城",
         "relation_type": "creation", "source_name": None, "source_url": None,
         "note": None, "start_year": None, "end_year": None},
        {"author_name": "欧内斯特·海明威", "place_name": "奥克帕克",
         "relation_type": "birthplace", "source_name": None, "source_url": None,
         "note": None, "start_year": None, "end_year": None},
        {"author_name": "欧内斯特·海明威", "place_name": "古巴",
         "relation_type": "residence", "source_name": None, "source_url": None,
         "note": None, "start_year": None, "end_year": None},
        {"author_name": "欧内斯特·海明威", "place_name": "古巴",
         "relation_type": "creation", "source_name": None, "source_url": None,
         "note": None, "start_year": None, "end_year": None},
        {"author_name": "乔治·奥威尔", "place_name": "莫蒂哈里",
         "relation_type": "birthplace", "source_name": None, "source_url": None,
         "note": None, "start_year": None, "end_year": None},
        {"author_name": "但丁·阿利吉耶里", "place_name": "佛罗伦萨",
         "relation_type": "birthplace", "source_name": None, "source_url": None,
         "note": None, "start_year": None, "end_year": None},
    ],
}


# ---------------------------------------------------------------------------
# 基础实体的写入列（列名固定，值全部参数化）
# ---------------------------------------------------------------------------

_ENTITY_COLUMNS = {
    "books": ["title", "original_title", "language", "publication_year",
              "description", "source"],
    "authors": ["name", "birth_year", "death_year", "nationality", "bio"],
    "genres": ["name", "description"],
    "places": ["name", "place_type", "is_fictional", "latitude", "longitude",
               "country", "region", "parent_place_id", "description"],
}

# 基础实体用于查重的自然键列
_ENTITY_UNIQUE_COLUMN = {
    "books": "title",
    "authors": "name",
    "genres": "name",
    "places": "name",
}


def _get_or_create_entity(conn: sqlite3.Connection, table: str, item: dict) -> int:
    """按自然键查找基础实体，不存在则插入，返回该实体 id。

    幂等关键：先查后插，避免对同一自然键重复插入。
    列名来自内部常量，值全部通过参数化占位符传入。
    """
    unique_col = _ENTITY_UNIQUE_COLUMN[table]
    unique_val = item[unique_col]

    row = conn.execute(
        f"SELECT id FROM {table} WHERE {unique_col} = ?", (unique_val,)
    ).fetchone()
    if row is not None:
        return row[0]

    columns = _ENTITY_COLUMNS[table]
    col_names = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    values = [item.get(col) for col in columns]
    cur = conn.execute(
        f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})", values
    )
    return cur.lastrowid


def _insert_relation_ignore(conn: sqlite3.Connection, table: str,
                            columns: list[str], values: list) -> None:
    """写入关联表，遇到唯一约束冲突则忽略（保证幂等）。"""
    col_names = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    conn.execute(
        f"INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({placeholders})",
        values,
    )


def seed_data(conn: sqlite3.Connection, data: dict | None = None) -> dict:
    """在单个事务中导入种子数据，返回各表最终行数。

    任一步骤抛出异常都会触发 rollback，保证不会出现半插入状态。
    conn 必须来自 get_db_connection()（已开启外键、已建表）。
    """
    data = data if data is not None else SEED_DATA

    book_ids: dict[str, int] = {}
    author_ids: dict[str, int] = {}
    genre_ids: dict[str, int] = {}
    place_ids: dict[str, int] = {}

    try:
        # 1. 基础实体：先插父表，并记录 自然键 -> id 映射
        for b in data["books"]:
            book_ids[b["title"]] = _get_or_create_entity(conn, "books", b)
        for a in data["authors"]:
            author_ids[a["name"]] = _get_or_create_entity(conn, "authors", a)
        for g in data["genres"]:
            genre_ids[g["name"]] = _get_or_create_entity(conn, "genres", g)
        for p in data["places"]:
            place_ids[p["name"]] = _get_or_create_entity(conn, "places", p)

        # 2. 关联表：通过已解析的 id 写入
        for ba in data["book_authors"]:
            _insert_relation_ignore(
                conn, "book_authors",
                ["book_id", "author_id", "role"],
                [book_ids[ba["book_title"]], author_ids[ba["author_name"]],
                 ba.get("role")],
            )
        for bg in data["book_genres"]:
            _insert_relation_ignore(
                conn, "book_genres",
                ["book_id", "genre_id"],
                [book_ids[bg["book_title"]], genre_ids[bg["genre_name"]]],
            )
        for bp in data["book_places"]:
            _insert_relation_ignore(
                conn, "book_places",
                ["book_id", "place_id", "relation_type", "source_name",
                 "source_url", "note", "verification_status"],
                [book_ids[bp["book_title"]], place_ids[bp["place_name"]],
                 bp["relation_type"], bp.get("source_name"), bp.get("source_url"),
                 bp.get("note"), "unverified"],
            )
        for ap in data["author_places"]:
            _insert_relation_ignore(
                conn, "author_places",
                ["author_id", "place_id", "relation_type", "source_name",
                 "source_url", "note", "verification_status",
                 "start_year", "end_year"],
                [author_ids[ap["author_name"]], place_ids[ap["place_name"]],
                 ap["relation_type"], ap.get("source_name"), ap.get("source_url"),
                 ap.get("note"), "unverified", ap.get("start_year"),
                 ap.get("end_year")],
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return _count_summary(conn)


def _count_summary(conn: sqlite3.Connection) -> dict:
    """返回各业务表（不含 reading_records 与内部表）的行数。"""
    tables = ["books", "authors", "genres", "places",
              "book_authors", "book_genres", "book_places", "author_places"]
    summary = {}
    for t in tables:
        summary[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    return summary


def run() -> dict:
    """正式导入入口：确保建表后，在事务中导入种子数据。

    注意：本函数会写入正式数据库 backend/literary_atlas.db，
    仅在数据确认齐全、得到审核通过后手动执行。
    """
    init_db()
    conn = get_db_connection()
    try:
        return seed_data(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    result = run()
    print("种子数据导入完成，各表行数：")
    for table, count in result.items():
        print(f"  {table}: {count}")
