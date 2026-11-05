"""统一搜索接口（全站搜索框使用）。

GET /api/search?q=<关键词>&per_group=<每组条数上限>

跨作品、作者、地点、国家、文学流派返回分组模糊检索结果：
- 复用 search_engine 的统一模糊匹配（归一化 + 相关度评分 + 轻量容错）
- 只读查询，不修改任何数据
"""

from fastapi import APIRouter, Query

from pydantic import BaseModel

from search_engine import search_all

router = APIRouter()


class SearchWorkItem(BaseModel):
    """搜索结果：作品条目。"""

    id: int
    title: str
    original_title: str | None = None
    publication_year: int | None = None
    authors: list[str] = []
    genres: list[str] = []
    match_type: str
    matched_by: str


class SearchAuthorItem(BaseModel):
    """搜索结果：作者条目。"""

    id: int
    name: str
    nationality: str | None = None
    work_titles: list[str] = []
    match_type: str
    matched_by: str


class SearchPlaceItem(BaseModel):
    """搜索结果：地点条目（城市 / 区域 / 虚构地点）。"""

    id: int
    name: str
    place_type: str
    is_fictional: int
    country: str | None = None
    region: str | None = None
    match_type: str
    matched_by: str


class SearchCountryItem(BaseModel):
    """搜索结果：国家条目。"""

    name: str
    place_id: int | None = None
    work_count: int = 0
    match_type: str


class SearchGenreItem(BaseModel):
    """搜索结果：文学流派条目。"""

    id: int
    name: str
    description: str | None = None
    work_count: int = 0
    match_type: str


class SearchGroups(BaseModel):
    """按类型分组的搜索结果。"""

    works: list[SearchWorkItem] = []
    authors: list[SearchAuthorItem] = []
    places: list[SearchPlaceItem] = []
    countries: list[SearchCountryItem] = []
    genres: list[SearchGenreItem] = []


class SearchResponse(BaseModel):
    """统一搜索响应。"""

    query: str
    total: int
    # 是否为容错兜底结果（本次查询没有任何确定级命中时为 True）
    fuzzy_fallback: bool = False
    groups: SearchGroups


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    per_group: int = Query(5, ge=1, le=20, description="每类结果条数上限"),
):
    """全站统一模糊搜索：作品 / 作者 / 地点 / 国家 / 文学流派。"""
    return search_all(q, per_group=per_group)
