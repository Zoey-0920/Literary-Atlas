"""作品（books）相关接口。

提供作品的：新增、列表查询、详情查询、部分修改。
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, StrictInt, field_validator

# 复用 database.py 中已经实现的数据库连接
from database import get_db_connection

# 统一路由前缀在 main.py 中通过 include_router 设置为 /api/books
router = APIRouter()


# ---------- Pydantic 模型：用于校验请求体 ----------

class BookCreate(BaseModel):
    """新增作品时的请求体。"""

    title: str
    original_title: str | None = None
    language: str | None = None
    # StrictInt：严格要求整数，拒绝布尔值、小数、字符串
    publication_year: StrictInt | None = None
    description: str | None = None
    source: str | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        """title 不能是空字符串或纯空格。"""
        if not v or not v.strip():
            raise ValueError("标题不能为空或全为空格")
        return v


class BookUpdate(BaseModel):
    """修改作品时的请求体，所有字段均可省略。"""

    title: str | None = None
    original_title: str | None = None
    language: str | None = None
    publication_year: StrictInt | None = None
    description: str | None = None
    source: str | None = None

    @field_validator("title")
    @classmethod
    def title_check(cls, v: str | None):
        """显式传入 title 时，不允许为 null 或空白字符串。"""
        if v is None:
            raise ValueError("标题不允许为空")
        if not v.strip():
            raise ValueError("标题不能为空白字符串")
        return v


class Book(BaseModel):
    """作品返回模型（完整信息）。"""

    id: int
    title: str
    original_title: str | None = None
    language: str | None = None
    publication_year: int | None = None
    description: str | None = None
    source: str | None = None
    created_at: str
    updated_at: str | None = None


class BookList(BaseModel):
    """作品列表返回模型。"""

    total: int
    items: list[Book]


# ---------- 作品详情关联模型 ----------

# 作者↔地点关系类型的中文含义
_AUTHOR_PLACE_RELATION_LABELS = {
    "birthplace": "出生地",
    "residence": "生活地",
    "creation": "创作地",
}

# 作品↔地点关系类型的中文含义
_BOOK_PLACE_RELATION_LABELS = {
    "setting": "故事发生地",
    "depiction": "作品描写地",
}


class AuthorPlace(BaseModel):
    """作品详情中作者关联的地点。"""

    id: int
    name: str
    place_type: str
    is_fictional: int
    country: str | None = None
    region: str | None = None
    relation_type: str
    relation_type_label: str
    start_year: int | None = None
    end_year: int | None = None
    verification_status: str


class BookAuthor(BaseModel):
    """作品详情中的作者信息。"""

    id: int
    name: str
    birth_year: int | None = None
    death_year: int | None = None
    nationality: str | None = None
    bio: str | None = None
    role: str | None = None
    places: list[AuthorPlace] = []


class BookGenre(BaseModel):
    """作品详情中的流派信息。"""

    id: int
    name: str
    description: str | None = None


class BookPlace(BaseModel):
    """作品详情中作品关联的地点（故事发生地 / 作品描写地）。"""

    id: int
    name: str
    place_type: str
    is_fictional: int
    latitude: float | None = None
    longitude: float | None = None
    country: str | None = None
    region: str | None = None
    relation_type: str
    relation_type_label: str
    verification_status: str
    source_name: str | None = None
    source_url: str | None = None
    note: str | None = None


class BookDetail(Book):
    """作品详情返回模型：在作品元数据基础上补充作者、流派与关联地点。"""

    authors: list[BookAuthor] = []
    genres: list[BookGenre] = []
    places: list[BookPlace] = []


# ---------- 辅助函数 ----------

def _row_to_dict(row) -> dict:
    """把 sqlite3.Row 转换成普通字典。"""
    return {key: row[key] for key in row.keys()}


# ---------- 1. 新增作品：POST /api/books ----------

@router.post("", response_model=Book, status_code=201)
def create_book(payload: BookCreate):
    """新增一部作品，返回新作品的完整信息。"""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO books
                (title, original_title, language, publication_year, description, source)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.title,
                payload.original_title,
                payload.language,
                payload.publication_year,
                payload.description,
                payload.source,
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM books WHERE id = ?", (new_id,)).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row)


# ---------- 2. 获取作品列表：GET /api/books ----------

@router.get("", response_model=BookList)
def list_books(
    keyword: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """分页获取作品列表，可按标题关键词搜索，按 id 升序。"""
    conn = get_db_connection()
    try:
        if keyword and keyword.strip():
            like = f"%{keyword.strip()}%"
            total = conn.execute(
                "SELECT COUNT(*) AS c FROM books "
                "WHERE title LIKE ? OR original_title LIKE ?",
                (like, like),
            ).fetchone()["c"]
            rows = conn.execute(
                "SELECT * FROM books WHERE title LIKE ? OR original_title LIKE ? "
                "ORDER BY id ASC LIMIT ? OFFSET ?",
                (like, like, limit, offset),
            ).fetchall()
        else:
            total = conn.execute("SELECT COUNT(*) AS c FROM books").fetchone()["c"]
            rows = conn.execute(
                "SELECT * FROM books ORDER BY id ASC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
    finally:
        conn.close()
    items = [_row_to_dict(row) for row in rows]
    return {"total": total, "items": items}


# ---------- 3. 查询作品详情：GET /api/books/{book_id} ----------

@router.get("/{book_id}", response_model=BookDetail)
def get_book(book_id: int):
    """根据 id 查询作品详情（含作者、流派、关联地点），找不到返回 404。"""
    conn = get_db_connection()
    try:
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if book is None:
            raise HTTPException(status_code=404, detail="作品不存在")

        # 关联作者（含 book_authors 中的角色）
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
                   p.latitude, p.longitude, p.country, p.region,
                   bp.relation_type, bp.verification_status,
                   bp.source_name, bp.source_url, bp.note
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
            "latitude": r["latitude"],
            "longitude": r["longitude"],
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
        **_row_to_dict(book),
        "authors": authors,
        "genres": genres,
        "places": places,
    }


# ---------- 4. 修改作品：PATCH /api/books/{book_id} ----------

@router.patch("/{book_id}", response_model=Book)
def update_book(book_id: int, payload: BookUpdate):
    """部分修改作品：未提供的字段保持不变；传 null 的字段置空。"""
    # 只取客户端真正提供的字段（exclude_unset），未提供的字段不进入 data
    data = payload.model_dump(exclude_unset=True)

    # 若客户端什么都不传，直接返回当前作品
    if not data:
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise HTTPException(status_code=404, detail="作品不存在")
        return _row_to_dict(row)

    conn = get_db_connection()
    try:
        # 先确认作品存在
        exists = conn.execute(
            "SELECT id FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if exists is None:
            raise HTTPException(status_code=404, detail="作品不存在")

        # 动态构建 SET 子句，字段名来自我们白名单，值一律用参数绑定
        columns = ", ".join(f"{key} = ?" for key in data.keys())
        values = list(data.values())
        # 每次修改都刷新 updated_at
        sql = f"UPDATE books SET {columns}, updated_at = datetime('now') WHERE id = ?"
        conn.execute(sql, values + [book_id])
        conn.commit()

        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row)