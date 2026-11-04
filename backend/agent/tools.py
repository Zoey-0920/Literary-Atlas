"""Literary Atlas Agent 数据库查询工具。

提供只读的数据库查询能力，供大模型（Agent）调用：
- search_books        : 按书名关键词模糊搜索作品
- list_books          : 列出数据库中的全部作品（用于推荐 / 浏览）
- search_places       : 按地点名关键词模糊搜索地点
- get_book_detail     : 按作品 ID 查询详情（关联作者、地点、流派）
- get_reading_records : 查询演示用户的个人阅读记录
- get_reading_statistics: 统计演示用户的阅读记录（在读/想读/读完）

约束：
- 只做 SELECT 查询，绝不新增 / 修改 / 删除数据。
- 所有 SQL 均使用参数化占位符，杜绝拼接用户输入。
- 数据库连接统一复用 database.py 的 get_db_connection()。
- 阅读工具只读取 config.DEMO_USER_ID 的记录，保证用户隔离。
"""

from config import DEMO_USER_ID
from database import get_db_connection

# 搜索结果默认返回条数，以及上限（避免一次返回过多数据）
_DEFAULT_LIMIT = 5
_MAX_LIMIT = 20

# 列出全部作品时的上限（覆盖当前 50 部作品，并留有余量）
_LIST_MAX_LIMIT = 100

# book_places.relation_type 的中文含义（作品 ↔ 地点）
_BOOK_PLACE_RELATION_LABELS = {
    "setting": "故事发生地",
    "depiction": "作品描写地",
}

# author_places.relation_type 的中文含义（作者 ↔ 地点）
_AUTHOR_PLACE_RELATION_LABELS = {
    "birthplace": "出生地",
    "residence": "生活地",
    "creation": "创作地",
}


def _row_to_dict(row) -> dict:
    """把 sqlite3.Row 转换成普通字典。"""
    return {key: row[key] for key in row.keys()}


def _normalize_keyword(keyword: str) -> str | None:
    """清洗关键词；为空或纯空白时返回 None。"""
    if keyword is None:
        return None
    kw = keyword.strip()
    return kw if kw else None


def _normalize_limit(limit: int | None) -> int:
    """把 limit 钳制到 [1, _MAX_LIMIT] 区间。"""
    if limit is None:
        return _DEFAULT_LIMIT
    return max(1, min(int(limit), _MAX_LIMIT))


# ---------- 1. 按书名关键词搜索作品 ----------

def search_books(keyword: str, limit: int | None = None) -> dict:
    """按作品名称关键词模糊搜索文学作品。

    参数：
        keyword: 书名关键词（必填）。
        limit  : 返回条数上限，默认 5，最大 20。

    返回：
        {"total": 匹配总数, "items": [作品概要, ...]}
        作品概要包含：id、title、original_title、language、publication_year。
    """
    kw = _normalize_keyword(keyword)
    if kw is None:
        # 空关键词：不执行 LIKE '%%' 全表返回
        return {"total": 0, "items": []}

    limit = _normalize_limit(limit)
    like = f"%{kw}%"

    conn = get_db_connection()
    try:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM books WHERE title LIKE ?", (like,)
        ).fetchone()["c"]
        rows = conn.execute(
            """
            SELECT id, title, original_title, language, publication_year
            FROM books
            WHERE title LIKE ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (like, limit),
        ).fetchall()
    finally:
        conn.close()

    items = [_row_to_dict(r) for r in rows]
    return {"total": total, "items": items}


# ---------- 1b. 列出全部作品 ----------

def list_books(limit: int | None = None, offset: int = 0) -> dict:
    """列出数据库中的作品，用于推荐或浏览全部作品。

    参数：
        limit : 返回条数上限，默认 100（一次可列出全部作品），最大 100。
        offset: 偏移量，默认 0。

    返回：
        {"total": 作品总数, "items": [作品概要, ...]}
    """
    limit = _LIST_MAX_LIMIT if limit is None else max(1, min(int(limit), _LIST_MAX_LIMIT))
    offset = max(0, int(offset or 0))

    conn = get_db_connection()
    try:
        total = conn.execute("SELECT COUNT(*) AS c FROM books").fetchone()["c"]
        rows = conn.execute(
            """
            SELECT id, title, original_title, language, publication_year
            FROM books
            ORDER BY id ASC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
    finally:
        conn.close()

    items = [_row_to_dict(r) for r in rows]
    return {"total": total, "items": items}


# ---------- 2. 按地点名关键词搜索地点 ----------

def search_places(keyword: str, limit: int | None = None) -> dict:
    """按地点名称关键词模糊搜索地点。

    参数：
        keyword: 地点名关键词（必填）。
        limit  : 返回条数上限，默认 5，最大 20。

    返回：
        {"total": 匹配总数, "items": [地点概要, ...]}
        地点概要包含：id、name、place_type、is_fictional、country、region。
        保留 is_fictional 与 place_type，便于区分虚构地点与现实地点。
    """
    kw = _normalize_keyword(keyword)
    if kw is None:
        return {"total": 0, "items": []}

    limit = _normalize_limit(limit)
    like = f"%{kw}%"

    conn = get_db_connection()
    try:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM places WHERE name LIKE ?", (like,)
        ).fetchone()["c"]
        rows = conn.execute(
            """
            SELECT id, name, place_type, is_fictional, country, region
            FROM places
            WHERE name LIKE ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (like, limit),
        ).fetchall()
    finally:
        conn.close()

    items = [_row_to_dict(r) for r in rows]
    return {"total": total, "items": items}


# ---------- 3. 按作品 ID 查询详情 ----------

def get_book_detail(book_id: int) -> dict:
    """按作品 ID 查询详情，关联作者、地点与文学流派。

    参数：
        book_id: 作品 ID。

    返回：
        成功时返回作品完整信息，含：
        - 作者列表（含 role 角色；每个作者附其地点关系，如出生地/生活地/创作地）
        - 流派列表
        - 地点列表（作品的故事发生地 / 作品描写地）
        作者 nationality 单独保留在作者对象中，不会混入作品地点。
        若作品不存在，返回 {"error": "作品不存在", "book_id": ...}。
    """
    conn = get_db_connection()
    try:
        book = conn.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if book is None:
            return {"error": "作品不存在", "book_id": book_id}

        # 关联作者（含在 book_authors 中的角色）
        author_rows = conn.execute(
            """
            SELECT a.id, a.name, a.birth_year, a.death_year,
                   a.nationality, a.bio, ba.role
            FROM book_authors AS ba
            JOIN authors AS a ON a.id = ba.author_id
            WHERE ba.book_id = ?
            ORDER BY a.id ASC
            """,
            (book_id,),
        ).fetchall()

        # 这些作者的地点关系（出生地 / 生活地 / 创作地）
        author_place_rows = conn.execute(
            """
            SELECT ap.author_id, p.id, p.name, p.place_type, p.is_fictional,
                   p.country, p.region, ap.relation_type,
                   ap.start_year, ap.end_year, ap.verification_status
            FROM author_places AS ap
            JOIN places AS p ON p.id = ap.place_id
            WHERE ap.author_id IN (
                SELECT author_id FROM book_authors WHERE book_id = ?
            )
            ORDER BY ap.author_id ASC, p.id ASC
            """,
            (book_id,),
        ).fetchall()

        # 关联流派
        genre_rows = conn.execute(
            """
            SELECT g.id, g.name, g.description
            FROM book_genres AS bg
            JOIN genres AS g ON g.id = bg.genre_id
            WHERE bg.book_id = ?
            ORDER BY g.id ASC
            """,
            (book_id,),
        ).fetchall()

        # 作品相关地点（故事发生地 / 作品描写地）
        book_place_rows = conn.execute(
            """
            SELECT p.id, p.name, p.place_type, p.is_fictional,
                   p.country, p.region, bp.relation_type,
                   bp.verification_status, bp.source_name, bp.source_url, bp.note
            FROM book_places AS bp
            JOIN places AS p ON p.id = bp.place_id
            WHERE bp.book_id = ?
            ORDER BY p.id ASC
            """,
            (book_id,),
        ).fetchall()
    finally:
        conn.close()

    # 组装作者，并把每位作者的地点关系挂到对应作者下
    author_places_by_author: dict[int, list[dict]] = {}
    for r in author_place_rows:
        rel = r["relation_type"]
        author_places_by_author.setdefault(r["author_id"], []).append({
            "id": r["id"],
            "name": r["name"],
            "place_type": r["place_type"],
            "is_fictional": r["is_fictional"],
            "country": r["country"],
            "region": r["region"],
            "relation_type": rel,
            "relation_type_label": _AUTHOR_PLACE_RELATION_LABELS.get(rel, rel),
            "start_year": r["start_year"],
            "end_year": r["end_year"],
            "verification_status": r["verification_status"],
        })

    authors = []
    for r in author_rows:
        authors.append({
            "id": r["id"],
            "name": r["name"],
            "birth_year": r["birth_year"],
            "death_year": r["death_year"],
            "nationality": r["nationality"],
            "bio": r["bio"],
            "role": r["role"],
            "places": author_places_by_author.get(r["id"], []),
        })

    genres = [_row_to_dict(r) for r in genre_rows]

    places = []
    for r in book_place_rows:
        rel = r["relation_type"]
        places.append({
            "id": r["id"],
            "name": r["name"],
            "place_type": r["place_type"],
            "is_fictional": r["is_fictional"],
            "country": r["country"],
            "region": r["region"],
            "relation_type": rel,
            "relation_type_label": _BOOK_PLACE_RELATION_LABELS.get(rel, rel),
            "verification_status": r["verification_status"],
            "source_name": r["source_name"],
            "source_url": r["source_url"],
            "note": r["note"],
        })

    return {
        "id": book["id"],
        "title": book["title"],
        "original_title": book["original_title"],
        "language": book["language"],
        "publication_year": book["publication_year"],
        "description": book["description"],
        "source": book["source"],
        "created_at": book["created_at"],
        "updated_at": book["updated_at"],
        "authors": authors,
        "genres": genres,
        "places": places,
    }


# ---------- 4. 查询演示用户的阅读记录 ----------

# 阅读状态的中文含义
_READING_STATUS_LABELS = {
    "want_to_read": "想读",
    "reading": "在读",
    "finished": "读完",
}


def get_reading_records(status: str | None = None) -> dict:
    """查询演示用户的个人阅读记录（只读）。

    参数：
        status: 可选，按阅读状态筛选。取值：want_to_read / reading / finished。

    返回：
        {"total": 数量, "items": [阅读记录, ...]}
        每条阅读记录包含：作品 ID、书名、状态、评分、进度、笔记、起止时间。
    """
    conn = get_db_connection()
    try:
        if status is not None:
            rows = conn.execute(
                """
                SELECT r.id, r.book_id, b.title AS book_title,
                       r.status, r.rating, r.progress, r.started_at,
                       r.finished_at, r.note
                FROM reading_records AS r
                JOIN books AS b ON b.id = r.book_id
                WHERE r.user_id = ? AND r.status = ?
                ORDER BY r.id DESC
                """,
                (DEMO_USER_ID, status),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT r.id, r.book_id, b.title AS book_title,
                       r.status, r.rating, r.progress, r.started_at,
                       r.finished_at, r.note
                FROM reading_records AS r
                JOIN books AS b ON b.id = r.book_id
                WHERE r.user_id = ?
                ORDER BY r.id DESC
                """,
                (DEMO_USER_ID,),
            ).fetchall()
    finally:
        conn.close()

    items = []
    for r in rows:
        st = r["status"]
        items.append({
            "id": r["id"],
            "book_id": r["book_id"],
            "book_title": r["book_title"],
            "status": st,
            "status_label": _READING_STATUS_LABELS.get(st, st),
            "rating": r["rating"],
            "progress": r["progress"],
            "started_at": r["started_at"],
            "finished_at": r["finished_at"],
            "note": r["note"],
        })
    return {"total": len(items), "items": items}


# ---------- 5. 统计演示用户的阅读情况 ----------

def get_reading_statistics() -> dict:
    """统计演示用户个人阅读记录（只读）。

    返回：
        按阅读状态分组的数量统计，以及总数。
    """
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT status, COUNT(*) AS c
            FROM reading_records
            WHERE user_id = ?
            GROUP BY status
            """,
            (DEMO_USER_ID,),
        ).fetchall()
    finally:
        conn.close()

    counts = {"want_to_read": 0, "reading": 0, "finished": 0}
    for r in rows:
        if r["status"] in counts:
            counts[r["status"]] = r["c"]

    counts["total"] = sum(counts.values())
    return counts
