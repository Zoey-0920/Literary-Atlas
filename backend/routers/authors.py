"""作者（authors）相关接口。

提供作者的：列表查询、详情查询（含该作者关联的作品）。

说明：
- 统一路由前缀在 main.py 中通过 include_router 设置为 /api/authors。
- 本模块只做只读查询，不写数据库。
- 作者与作品的关联来自 book_authors 表，role 取值为 author / translator / editor。
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

# 复用 database.py 中已经实现的数据库连接
from database import get_db_connection

router = APIRouter()


# ---------- Pydantic 模型：用于定义响应结构 ----------

class Author(BaseModel):
    """作者基本信息返回模型。"""

    id: int
    name: str
    birth_year: int | None = None
    death_year: int | None = None
    nationality: str | None = None
    bio: str | None = None
    created_at: str
    updated_at: str | None = None


class AuthorList(BaseModel):
    """作者列表返回模型。"""

    total: int
    items: list[Author]


class AuthorBook(BaseModel):
    """作者详情中该作者关联的单部作品。"""

    id: int
    title: str
    original_title: str | None = None
    language: str | None = None
    publication_year: int | None = None
    role: str | None = None


class AuthorDetail(Author):
    """作者详情返回模型：在基本信息基础上补充关联作品。"""

    books: list[AuthorBook] = []


# ---------- 辅助函数 ----------

def _row_to_dict(row) -> dict:
    """把 sqlite3.Row 转换成普通字典。"""
    return {key: row[key] for key in row.keys()}


# ---------- 1. 获取作者列表：GET /api/authors ----------

@router.get("", response_model=AuthorList)
def list_authors(
    keyword: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """分页获取作者列表，可按姓名关键词搜索，按 id 升序。"""
    conn = get_db_connection()
    try:
        if keyword and keyword.strip():
            like = f"%{keyword.strip()}%"
            total = conn.execute(
                "SELECT COUNT(*) AS c FROM authors WHERE name LIKE ?",
                (like,),
            ).fetchone()["c"]
            rows = conn.execute(
                "SELECT * FROM authors WHERE name LIKE ? "
                "ORDER BY id ASC LIMIT ? OFFSET ?",
                (like, limit, offset),
            ).fetchall()
        else:
            total = conn.execute("SELECT COUNT(*) AS c FROM authors").fetchone()["c"]
            rows = conn.execute(
                "SELECT * FROM authors ORDER BY id ASC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
    finally:
        conn.close()
    return {"total": total, "items": [_row_to_dict(row) for row in rows]}


# ---------- 2. 查询作者详情：GET /api/authors/{author_id} ----------

@router.get("/{author_id}", response_model=AuthorDetail)
def get_author(author_id: int):
    """根据 id 查询作者详情（含其关联的全部作品），找不到返回 404。"""
    conn = get_db_connection()
    try:
        author = conn.execute(
            "SELECT * FROM authors WHERE id = ?", (author_id,)
        ).fetchone()
        if author is None:
            raise HTTPException(status_code=404, detail="作者不存在")

        # 该作者关联的作品（role 保留 book_authors 中的真实关联角色）
        book_rows = conn.execute(
            """
            SELECT b.id, b.title, b.original_title, b.language,
                   b.publication_year, ba.role
            FROM book_authors AS ba
            JOIN books AS b ON b.id = ba.book_id
            WHERE ba.author_id = ?
            ORDER BY b.id ASC
            """,
            (author_id,),
        ).fetchall()
    finally:
        conn.close()

    books = [_row_to_dict(row) for row in book_rows]
    return {**_row_to_dict(author), "books": books}
