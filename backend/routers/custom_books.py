"""自主添加书籍（自定义作品）接口。

用户在探索页面通过 AI 辅助添加自己的作品。三个接口：

- POST   /api/custom-books/lookup    AI 识别作品 + 匹配现有地点（只读，不写库）
- POST   /api/custom-books           用户确认后保存自定义作品（事务）
- DELETE /api/custom-books/{book_id} 删除自定义作品（仅限 source='custom'）

数据边界约定（与整体方案一致）：
- 复用现有 9 张表，不新增表、不修改表结构；
- 自定义作品写入 books 表并用 source='custom' 与公共精选作品区分；
- 原有公共作品（source IS NULL，共 50 部）绝不被修改或删除；
- 新增地点一律不写经纬度（coordinates 待核实），不会在地图上出现；
- 复用现有阅读记录机制（加入书架由前端调用现有 POST /api/reading 完成）；
- 无用户体系，行为主体即 config.DEMO_USER_ID 演示用户（本路由不直接涉及）。
"""

import sqlite3

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from agent.book_lookup import BookLookupError, lookup_book
from database import get_db_connection

router = APIRouter()

# 与数据库 CHECK 约束保持一致的枚举值（Pydantic Literal 自动校验并返回 422）
_ALLOWED_RELATION_TYPES = ("setting", "depiction")


# ---------- Pydantic 请求/响应模型 ----------

class LookupRequest(BaseModel):
    """AI 识别请求：书名必填，作者选填。"""

    title: str
    author: str | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("书名不能为空或全为空格")
        return v.strip()


class DraftPlace(BaseModel):
    """草案中的单个地点（含与现有地点库的匹配结果）。"""

    name: str
    country: str | None = None
    relation_type: str = "setting"
    is_fictional: bool = False
    # 与现有地点库的匹配结果：
    # reused         已存在且复用（含坐标时附带 place_id/经纬度）
    # exists_no_coords 已存在但无坐标（待核实，不会出现在地图上）
    # new            现有库中不存在，保存时将新建（无坐标，待核实）
    match_status: str
    place_id: int | None = None
    latitude: float | None = None
    longitude: float | None = None


class LookupResponse(BaseModel):
    """AI 识别结果（草案 + 重复检查 + 地点匹配），供用户确认。"""

    draft: dict
    # 与现有作品重复的检查结果
    duplicate: dict | None = None
    possible_duplicates: list[dict] = []


class PlaceIn(BaseModel):
    """确认保存时提交的单个地点。"""

    name: str
    country: str | None = None
    relation_type: str = "setting"
    is_fictional: bool = False

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("地点名称不能为空")
        return v.strip()

    @field_validator("relation_type")
    @classmethod
    def relation_allowed(cls, v: str) -> str:
        if v not in _ALLOWED_RELATION_TYPES:
            raise ValueError("relation_type 只允许 setting 或 depiction")
        return v


class CustomBookCreate(BaseModel):
    """确认保存自定义作品的请求体（内容应来自用户确认过的草案）。"""

    title: str
    author: str | None = None
    country: str | None = None
    genre: str | None = None
    description: str | None = None
    places: list[PlaceIn] = []

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("书名不能为空或全为空格")
        return v.strip()


# ---------- 内部辅助 ----------

def _normalize_title(title: str) -> str:
    """书名规范化：去首尾空白并压缩连续空白，用于重复检查的精确匹配。"""
    return " ".join(title.split())


def _find_title_matches(conn: sqlite3.Connection, title: str) -> list[sqlite3.Row]:
    """按规范化书名精确匹配现有作品（含公共与自定义，含原名字段）。"""
    t = _normalize_title(title)
    return conn.execute(
        """
        SELECT id, title, original_title, source, description
        FROM books
        WHERE REPLACE(TRIM(title), '  ', ' ') = ?
           OR REPLACE(TRIM(COALESCE(original_title, '')), '  ', ' ') = ?
        ORDER BY id ASC
        """,
        (t, t),
    ).fetchall()


def _get_book_author_names(conn: sqlite3.Connection, book_id: int) -> list[str]:
    """查询某作品关联的全部作者名。"""
    rows = conn.execute(
        """
        SELECT a.name FROM book_authors AS ba
        JOIN authors AS a ON a.id = ba.author_id
        WHERE ba.book_id = ?
        ORDER BY a.id ASC
        """,
        (book_id,),
    ).fetchall()
    return [r["name"] for r in rows]


def check_duplicate(conn: sqlite3.Connection, title: str, author: str | None) -> tuple[dict | None, list[dict]]:
    """重复作品检查。

    规则：
    - 书名精确匹配到现有作品时，若用户提供的作者与该书作者一致（或用户未填
      作者且匹配结果唯一），认定为重复；
    - 书名相同但作者明确不同：不认定为同一本书，仅放入 possible_duplicates；
    - 多个同名结果且无法确认时，同样只提示歧义。

    Returns:
        (duplicate, possible_duplicates)
    """
    rows = _find_title_matches(conn, title)
    if not rows:
        return None, []

    candidates = []
    for r in rows:
        candidates.append({
            "book_id": r["id"],
            "title": r["title"],
            "source": r["source"],
            "is_public": r["source"] is None,
            "authors": _get_book_author_names(conn, r["id"]),
        })

    input_author = (author or "").strip()
    for c in candidates:
        if not input_author:
            # 未提供作者：唯一匹配时按重复处理，多个结果视为歧义
            if len(candidates) == 1:
                return c, candidates
            return None, candidates
        # 提供了作者：任一匹配作品的作者名一致即认定重复
        for name in c["authors"]:
            if name == input_author:
                return c, candidates

    # 书名相同但作者不同：不认定为重复，仅提示存在同名作品
    return None, candidates


def match_place(conn: sqlite3.Connection, name: str, is_fictional: bool) -> dict:
    """把一个地点草案匹配到现有地点库（只读）。

    匹配优先级：同名且虚实一致 > 同名（任意类型，取最小 id）。
    """
    flag = 1 if is_fictional else 0
    row = conn.execute(
        "SELECT id, latitude, longitude FROM places WHERE name = ? AND is_fictional = ? "
        "ORDER BY id ASC LIMIT 1",
        (name, flag),
    ).fetchone()
    if row is None:
        row = conn.execute(
            "SELECT id, latitude, longitude FROM places WHERE name = ? ORDER BY id ASC LIMIT 1",
            (name,),
        ).fetchone()

    if row is None:
        return {"match_status": "new", "place_id": None, "latitude": None, "longitude": None}
    if row["latitude"] is not None and row["longitude"] is not None:
        return {
            "match_status": "reused",
            "place_id": row["id"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
        }
    # 存在同名地点但没有坐标：待核实（不会出现在地图上）
    return {
        "match_status": "exists_no_coords",
        "place_id": row["id"],
        "latitude": None,
        "longitude": None,
    }


def _find_or_create_author(conn: sqlite3.Connection, name: str) -> int:
    """按名字查找作者，不存在则新增（只写名字，其余字段保持 NULL，不编造）。"""
    row = conn.execute("SELECT id FROM authors WHERE name = ?", (name,)).fetchone()
    if row is not None:
        return row["id"]
    cursor = conn.execute("INSERT INTO authors (name) VALUES (?)", (name,))
    return cursor.lastrowid


def _find_or_create_genre(conn: sqlite3.Connection, name: str) -> int:
    """按名字查找流派，不存在则新增（genres.name 有 UNIQUE 约束）。"""
    row = conn.execute("SELECT id FROM genres WHERE name = ?", (name,)).fetchone()
    if row is not None:
        return row["id"]
    cursor = conn.execute("INSERT INTO genres (name) VALUES (?)", (name,))
    return cursor.lastrowid


def _create_place(conn: sqlite3.Connection, place: PlaceIn) -> int:
    """新建地点记录。

    硬性约束（与 places 表 CHECK 一致）：
    - 新地点一律不写经纬度，绝不伪造坐标，等待人工核实；
    - 虚构地点 place_type='fictional'、is_fictional=1，且不允许有坐标；
    - 真实地点默认按 'city' 处理；当地点名本身就是国家名时按 'country'。
    """
    flag = 1 if place.is_fictional else 0
    if place.is_fictional:
        place_type = "fictional"
    elif place.country and place.country.strip() == place.name.strip():
        place_type = "country"
    else:
        place_type = "city"

    cursor = conn.execute(
        """
        INSERT INTO places (name, place_type, is_fictional, latitude, longitude,
                            country, region, description)
        VALUES (?, ?, ?, NULL, NULL, ?, NULL, NULL)
        """,
        (place.name.strip(), place_type, flag, (place.country or None)),
    )
    return cursor.lastrowid


def _get_book_full(conn: sqlite3.Connection, book_id: int) -> dict:
    """组装自定义作品保存后的完整返回（结构与 GET /api/books/{id} 同源）。"""
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    authors = conn.execute(
        """
        SELECT a.id, a.name, a.birth_year, a.death_year, a.nationality, a.bio, ba.role
        FROM book_authors AS ba JOIN authors AS a ON a.id = ba.author_id
        WHERE ba.book_id = ? ORDER BY a.id ASC
        """,
        (book_id,),
    ).fetchall()
    genres = conn.execute(
        """
        SELECT g.id, g.name, g.description
        FROM book_genres AS bg JOIN genres AS g ON g.id = bg.genre_id
        WHERE bg.book_id = ? ORDER BY g.id ASC
        """,
        (book_id,),
    ).fetchall()
    places = conn.execute(
        """
        SELECT p.id, p.name, p.place_type, p.is_fictional, p.latitude, p.longitude,
               p.country, p.region, bp.relation_type, bp.verification_status,
               bp.source_name, bp.source_url, bp.note
        FROM book_places AS bp JOIN places AS p ON p.id = bp.place_id
        WHERE bp.book_id = ? ORDER BY p.id ASC
        """,
        (book_id,),
    ).fetchall()

    def rd(row):
        return {k: row[k] for k in row.keys()}

    return {
        **rd(book),
        "authors": [rd(a) for a in authors],
        "genres": [rd(g) for g in genres],
        "places": [rd(p) for p in places],
    }


# ---------- 1. AI 识别 + 地点匹配（只读）：POST /api/custom-books/lookup ----------

@router.post("/lookup", response_model=LookupResponse)
async def lookup_custom_book(payload: LookupRequest):
    """调用 AI 识别作品并匹配现有地点库。

    本接口完全只读：不写 books/places 等任何表。
    AI 结果仅供前端展示与用户确认，确认后需调用 POST /api/custom-books 保存。
    """
    conn = get_db_connection()
    try:
        # 先做重复检查（书名命中现有作品时，无需打扰 AI）
        duplicate, possible = check_duplicate(conn, payload.title, payload.author)

        draft_places = []
        draft = {}
        if duplicate is None:
            try:
                draft = await lookup_book(payload.title, payload.author)
            except BookLookupError as exc:
                raise HTTPException(status_code=502, detail=str(exc))
            # 对 AI 提取的地点逐一匹配现有地点库（只读查询）
            for p in draft.get("places", []):
                m = match_place(conn, p["name"], bool(p.get("is_fictional")))
                draft_places.append({**p, **m})
            draft["places"] = draft_places
    finally:
        conn.close()

    return {"draft": draft, "duplicate": duplicate, "possible_duplicates": possible}


# ---------- 2. 保存自定义作品（事务）：POST /api/custom-books ----------

@router.post("", status_code=201)
def create_custom_book(payload: CustomBookCreate):
    """保存用户确认后的自定义作品。

    全程使用单个事务：books + book_authors + book_genres + places + book_places
    任一步失败即整体回滚，不会留下半成品数据。
    """
    # 请求内按 (地点名, 关系类型) 去重，避免命中 book_places 唯一约束
    seen: set[tuple[str, str]] = set()
    places: list[PlaceIn] = []
    for p in payload.places:
        key = (p.name.strip(), p.relation_type)
        if key not in seen:
            seen.add(key)
            places.append(p)

    conn = get_db_connection()
    try:
        # 1) 再次重复检查（防止确认期间他人已添加同一本书）
        duplicate, _ = check_duplicate(conn, payload.title, payload.author)
        if duplicate is not None:
            raise HTTPException(
                status_code=409,
                detail=f"作品库已存在同名作品《{duplicate['title']}》(id={duplicate['book_id']})，请勿重复添加",
            )

        # 2) 作品主表：source='custom' 与公共精选作品（source IS NULL）区分
        cursor = conn.execute(
            """
            INSERT INTO books (title, original_title, language, publication_year,
                               description, source)
            VALUES (?, NULL, NULL, NULL, ?, 'custom')
            """,
            (payload.title.strip(), payload.description),
        )
        book_id = cursor.lastrowid

        # 3) 作者：存在则复用，不存在则新增；写作关联 role='author'
        author_name = (payload.author or "").strip()
        if author_name:
            author_id = _find_or_create_author(conn, author_name)
            conn.execute(
                "INSERT INTO book_authors (book_id, author_id, role) VALUES (?, ?, 'author')",
                (book_id, author_id),
            )

        # 4) 流派：存在则复用，不存在则新增
        genre_name = (payload.genre or "").strip()
        if genre_name:
            genre_id = _find_or_create_genre(conn, genre_name)
            conn.execute(
                "INSERT INTO book_genres (book_id, genre_id) VALUES (?, ?)",
                (book_id, genre_id),
            )

        # 5) 地点：已有地点复用 place_id；新地点一律无坐标入库
        for p in places:
            m = match_place(conn, p.name.strip(), p.is_fictional)
            if m["match_status"] == "new":
                place_id = _create_place(conn, p)
            else:
                place_id = m["place_id"]
            conn.execute(
                """
                INSERT INTO book_places
                    (book_id, place_id, relation_type, source_name, source_url,
                     note, verification_status)
                VALUES (?, ?, ?, NULL, NULL, ?, 'unverified')
                """,
                (book_id, place_id, p.relation_type, "AI辅助添加，坐标待核实"),
            )

        conn.commit()
        result = _get_book_full(conn, book_id)
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="保存自定义作品失败，已回滚")
    finally:
        conn.close()

    return result


# ---------- 3. 删除自定义作品：DELETE /api/custom-books/{book_id} ----------

@router.delete("/{book_id}", status_code=204)
def delete_custom_book(book_id: int):
    """删除自定义作品（仅限 source='custom'）。

    - 公共精选作品（source IS NULL）一律返回 403，绝不删除；
    - 关联数据（book_authors / book_genres / book_places / reading_records）
      由现有外键 ON DELETE CASCADE 自动清理；
    - 作者、地点、流派为共享实体，不做删除（可能被其他作品引用）。
    """
    conn = get_db_connection()
    try:
        book = conn.execute(
            "SELECT id, source FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if book is None:
            raise HTTPException(status_code=404, detail="作品不存在")
        if book["source"] != "custom":
            raise HTTPException(status_code=403, detail="公共精选作品不允许通过此接口删除")

        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="删除自定义作品失败，已回滚")
    finally:
        conn.close()
    return None
