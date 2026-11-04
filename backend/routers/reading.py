"""个人阅读记录（reading_records）相关接口。

提供个人书架的增删改查：
- POST   /api/reading            添加一本书到书架
- GET    /api/reading            查看书架（可按阅读状态筛选）
- PATCH  /api/reading/{record_id} 修改阅读状态 / 进度 / 评分 / 笔记
- DELETE /api/reading/{record_id} 删除书架记录

说明：
- 当前项目尚无用户登录体系，统一使用 config.DEMO_USER_ID 作为演示用户，
  所有读写都按该用户隔离，不会返回其他用户的记录。
- 阅读状态取值：want_to_read（想读）、reading（在读）、finished（读完）。
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from config import DEMO_USER_ID
from database import get_db_connection

router = APIRouter()

# 阅读状态允许的取值（与数据库 CHECK 约束保持一致）
_READING_STATUSES = ("want_to_read", "reading", "finished")


# ---------- Pydantic 模型 ----------

class ReadingCreate(BaseModel):
    """新增书架记录时的请求体。"""

    book_id: int
    status: Literal["want_to_read", "reading", "finished"]
    rating: int | None = Field(default=None, ge=1, le=5)
    progress: int | None = Field(default=None, ge=0, le=100)
    started_at: str | None = None
    finished_at: str | None = None
    note: str | None = None


class ReadingUpdate(BaseModel):
    """修改书架记录时的请求体，所有字段均可省略。"""

    status: Literal["want_to_read", "reading", "finished"] | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    progress: int | None = Field(default=None, ge=0, le=100)
    started_at: str | None = None
    finished_at: str | None = None
    note: str | None = None


class ReadingRecord(BaseModel):
    """书架记录返回模型。"""

    id: int
    user_id: str
    book_id: int
    book_title: str | None = None
    status: str
    rating: int | None = None
    progress: int | None = None
    started_at: str | None = None
    finished_at: str | None = None
    note: str | None = None
    created_at: str
    updated_at: str | None = None


class ReadingList(BaseModel):
    """书架列表返回模型。"""

    total: int
    items: list[ReadingRecord]


class ReadingStatistics(BaseModel):
    """个人阅读统计返回模型。"""

    total: int
    want_to_read: int
    reading: int
    finished: int


class FootprintBook(BaseModel):
    """个人文学足迹中某地点关联的已读作品。"""

    id: int
    title: str


class FootprintPlace(BaseModel):
    """个人文学足迹中的一个真实地点。"""

    place_id: int
    name: str
    place_type: str
    latitude: float
    longitude: float
    country: str | None = None
    region: str | None = None
    books: list[FootprintBook]


class Footprint(BaseModel):
    """个人文学足迹返回模型。"""

    total: int
    items: list[FootprintPlace]


# ---------- 辅助函数 ----------

def _row_to_dict(row) -> dict:
    """把 sqlite3.Row 转换成普通字典。"""
    return {key: row[key] for key in row.keys()}


def _get_record(conn, record_id: int):
    """按 id 取当前演示用户的阅读记录（含书名），不存在返回 None。"""
    return conn.execute(
        """
        SELECT r.*, b.title AS book_title
        FROM reading_records AS r
        JOIN books AS b ON b.id = r.book_id
        WHERE r.id = ? AND r.user_id = ?
        """,
        (record_id, DEMO_USER_ID),
    ).fetchone()


# ---------- 1. 添加到书架：POST /api/reading ----------

@router.post("", response_model=ReadingRecord, status_code=201)
def create_reading_record(payload: ReadingCreate):
    """把一部作品加入演示用户的个人书架。"""
    conn = get_db_connection()
    try:
        # 作品必须真实存在
        book = conn.execute(
            "SELECT id FROM books WHERE id = ?", (payload.book_id,)
        ).fetchone()
        if book is None:
            raise HTTPException(status_code=404, detail="作品不存在")

        # 同一用户对同一作品只能有一条阅读记录
        exists = conn.execute(
            "SELECT id FROM reading_records WHERE user_id = ? AND book_id = ?",
            (DEMO_USER_ID, payload.book_id),
        ).fetchone()
        if exists is not None:
            raise HTTPException(status_code=409, detail="该作品已在书架中")

        cursor = conn.execute(
            """
            INSERT INTO reading_records
                (user_id, book_id, status, rating, progress,
                 started_at, finished_at, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                DEMO_USER_ID,
                payload.book_id,
                payload.status,
                payload.rating,
                payload.progress,
                payload.started_at,
                payload.finished_at,
                payload.note,
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid
        row = _get_record(conn, new_id)
    finally:
        conn.close()
    return _row_to_dict(row)


# ---------- 2. 查看书架：GET /api/reading ----------

@router.get("", response_model=ReadingList)
def list_reading_records(
    status: Literal["want_to_read", "reading", "finished"] | None = Query(None),
):
    """查看演示用户的个人书架，可按阅读状态筛选。"""
    conn = get_db_connection()
    try:
        if status is not None:
            total = conn.execute(
                "SELECT COUNT(*) AS c FROM reading_records WHERE user_id = ? AND status = ?",
                (DEMO_USER_ID, status),
            ).fetchone()["c"]
            rows = conn.execute(
                """
                SELECT r.*, b.title AS book_title
                FROM reading_records AS r
                JOIN books AS b ON b.id = r.book_id
                WHERE r.user_id = ? AND r.status = ?
                ORDER BY r.id DESC
                """,
                (DEMO_USER_ID, status),
            ).fetchall()
        else:
            total = conn.execute(
                "SELECT COUNT(*) AS c FROM reading_records WHERE user_id = ?",
                (DEMO_USER_ID,),
            ).fetchone()["c"]
            rows = conn.execute(
                """
                SELECT r.*, b.title AS book_title
                FROM reading_records AS r
                JOIN books AS b ON b.id = r.book_id
                WHERE r.user_id = ?
                ORDER BY r.id DESC
                """,
                (DEMO_USER_ID,),
            ).fetchall()
    finally:
        conn.close()
    return {"total": total, "items": [_row_to_dict(r) for r in rows]}


# ---------- 3. 修改书架记录：PATCH /api/reading/{record_id} ----------

@router.patch("/{record_id}", response_model=ReadingRecord)
def update_reading_record(record_id: int, payload: ReadingUpdate):
    """部分修改书架记录：未提供的字段保持不变。"""
    data = payload.model_dump(exclude_unset=True)

    conn = get_db_connection()
    try:
        row = _get_record(conn, record_id)
        if row is None:
            raise HTTPException(status_code=404, detail="阅读记录不存在")

        if data:
            columns = ", ".join(f"{key} = ?" for key in data.keys())
            values = list(data.values())
            sql = (
                f"UPDATE reading_records SET {columns}, updated_at = datetime('now') "
                "WHERE id = ? AND user_id = ?"
            )
            conn.execute(sql, values + [record_id, DEMO_USER_ID])
            conn.commit()

        row = _get_record(conn, record_id)
    finally:
        conn.close()
    return _row_to_dict(row)


# ---------- 4. 删除书架记录：DELETE /api/reading/{record_id} ----------

@router.delete("/{record_id}", status_code=204)
def delete_reading_record(record_id: int):
    """删除演示用户的一条书架记录。"""
    conn = get_db_connection()
    try:
        row = _get_record(conn, record_id)
        if row is None:
            raise HTTPException(status_code=404, detail="阅读记录不存在")

        conn.execute(
            "DELETE FROM reading_records WHERE id = ? AND user_id = ?",
            (record_id, DEMO_USER_ID),
        )
        conn.commit()
    finally:
        conn.close()
    return None


# ---------- 5. 个人阅读统计：GET /api/reading/statistics ----------

@router.get("/statistics", response_model=ReadingStatistics)
def get_reading_statistics_http():
    """统计当前演示用户的阅读记录数量（书架总数 / 想读 / 在读 / 读完）。"""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS c FROM reading_records "
            "WHERE user_id = ? GROUP BY status",
            (DEMO_USER_ID,),
        ).fetchall()
    finally:
        conn.close()

    counts = {"want_to_read": 0, "reading": 0, "finished": 0}
    for r in rows:
        if r["status"] in counts:
            counts[r["status"]] = r["c"]
    return {"total": sum(counts.values()), **counts}


# ---------- 6. 个人文学足迹：GET /api/reading/footprint ----------

@router.get("/footprint", response_model=Footprint)
def get_literary_footprint():
    """根据已读（finished）作品聚合其关联的真实地点，作为个人文学足迹。

    筛选规则：
    - 只统计 status='finished' 的阅读记录；
    - 只返回真实地点（is_fictional=0 且 place_type<>'fictional'）；
    - 只返回经纬度均有效（均非 NULL）的地点；
    - 只依据作品↔地点关系（book_places），不涉及作者出生地/生活地/创作地；
    - 同一地点关联多部已读作品时合并，保留全部关联作品 ID 与书名。
    """
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT p.id AS place_id, p.name, p.place_type,
                   p.latitude, p.longitude, p.country, p.region,
                   b.id AS book_id, b.title AS book_title
            FROM reading_records AS r
            JOIN book_places AS bp ON bp.book_id = r.book_id
            JOIN books AS b ON b.id = r.book_id
            JOIN places AS p ON p.id = bp.place_id
            WHERE r.user_id = ?
              AND r.status = 'finished'
              AND p.is_fictional = 0
              AND p.place_type <> 'fictional'
              AND p.latitude IS NOT NULL
              AND p.longitude IS NOT NULL
            ORDER BY p.id ASC, b.id ASC
            """,
            (DEMO_USER_ID,),
        ).fetchall()
    finally:
        conn.close()

    # 按地点聚合，合并同一地点关联的多部作品
    places: dict[int, dict] = {}
    for r in rows:
        item = places.get(r["place_id"])
        if item is None:
            item = {
                "place_id": r["place_id"],
                "name": r["name"],
                "place_type": r["place_type"],
                "latitude": r["latitude"],
                "longitude": r["longitude"],
                "country": r["country"],
                "region": r["region"],
                "books": [],
            }
            places[r["place_id"]] = item
        item["books"].append({"id": r["book_id"], "title": r["book_title"]})

    items = list(places.values())
    return {"total": len(items), "items": items}
