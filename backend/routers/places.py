"""地点（places）相关查询接口。

只提供查询，不提供地点的增删改。
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from database import get_db_connection

# 复用 books.py 中已经定义的作品返回模型
from routers.books import Book

router = APIRouter()


# ---------- Pydantic 返回模型 ----------

class Place(BaseModel):
    """地点返回模型。"""

    id: int
    name: str
    place_type: str
    is_fictional: int  # 0=现实地点，1=虚构地点
    latitude: float | None = None
    longitude: float | None = None
    country: str | None = None
    region: str | None = None
    parent_place_id: int | None = None
    description: str | None = None
    created_at: str
    updated_at: str | None = None


class PlaceList(BaseModel):
    """地点列表返回模型。"""

    total: int
    items: list[Place]


class PlaceBook(BaseModel):
    """地点关联的作品，附带关联信息。"""

    book: Book
    relation_type: str
    verification_status: str
    source_name: str | None = None
    source_url: str | None = None
    note: str | None = None


class PlaceLiterature(BaseModel):
    """某地点的关联作品列表返回模型。"""

    place_id: int
    total: int
    items: list[PlaceBook]


# books 表的字段列表，用于从 JOIN 结果中拆分出作品信息
_BOOK_COLUMNS = [
    "id", "title", "original_title", "language",
    "publication_year", "description", "source",
    "created_at", "updated_at",
]


def _row_to_dict(row) -> dict:
    """把 sqlite3.Row 转换成普通字典。"""
    return {key: row[key] for key in row.keys()}


# ---------- 1. 地点列表：GET /api/places ----------

@router.get("", response_model=PlaceList)
def list_places(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    keyword: str | None = Query(None),
):
    """分页查询地点列表，可按名称模糊搜索，按 id 升序。"""
    conn = get_db_connection()
    try:
        if keyword:
            # 模糊搜索：LIKE 的值通过参数传入，避免 SQL 注入
            like = f"%{keyword}%"
            total = conn.execute(
                "SELECT COUNT(*) AS c FROM places WHERE name LIKE ?", (like,)
            ).fetchone()["c"]
            rows = conn.execute(
                "SELECT * FROM places WHERE name LIKE ? ORDER BY id ASC LIMIT ? OFFSET ?",
                (like, limit, offset),
            ).fetchall()
        else:
            total = conn.execute("SELECT COUNT(*) AS c FROM places").fetchone()["c"]
            rows = conn.execute(
                "SELECT * FROM places ORDER BY id ASC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
    finally:
        conn.close()
    return {"total": total, "items": [_row_to_dict(r) for r in rows]}


# ---------- 2. 地点详情：GET /api/places/{place_id} ----------

@router.get("/{place_id}", response_model=Place)
def get_place(place_id: int):
    """根据 id 查询地点详情，找不到返回 404。"""
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM places WHERE id = ?", (place_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="地点不存在")
    return _row_to_dict(row)


# ---------- 3. 地点关联作品：GET /api/places/{place_id}/literature ----------

@router.get("/{place_id}/literature", response_model=PlaceLiterature)
def get_place_literature(place_id: int):
    """查询与指定地点有关联的作品，同时返回关联类型与核验状态。"""
    conn = get_db_connection()
    try:
        exists = conn.execute(
            "SELECT id FROM places WHERE id = ?", (place_id,)
        ).fetchone()
        if exists is None:
            raise HTTPException(status_code=404, detail="地点不存在")

        rows = conn.execute(
            """
            SELECT b.*, bp.relation_type, bp.verification_status,
                   bp.source_name, bp.source_url, bp.note
            FROM book_places AS bp
            JOIN books AS b ON b.id = bp.book_id
            WHERE bp.place_id = ?
            ORDER BY b.id ASC
            """,
            (place_id,),
        ).fetchall()
    finally:
        conn.close()

    items = []
    for row in rows:
        book = {k: row[k] for k in _BOOK_COLUMNS}
        items.append({
            "book": book,
            "relation_type": row["relation_type"],
            "verification_status": row["verification_status"],
            "source_name": row["source_name"],
            "source_url": row["source_url"],
            "note": row["note"],
        })
    return {"place_id": place_id, "total": len(items), "items": items}