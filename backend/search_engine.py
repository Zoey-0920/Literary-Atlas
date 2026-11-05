"""统一模糊检索引擎（全站搜索 + AI Agent 查询工具共用）。

提供一套轻量级模糊匹配能力，复用现有 SQLite 数据库，只读、不写库：
- 归一化：去首尾空格、连续空格合并、英文不区分大小写（casefold）
- 多级相关度评分：精确匹配 > 前缀匹配 > 包含匹配 > 分词全命中 > 容错匹配
- 轻量拼写容错：Damerau-Levenshtein 编辑距离（纯 Python，无第三方依赖），
  仅对长度 >= 2 的关键词启用，容错结果分数最低且条数受限，
  避免模糊匹配返回大量无关结果。

数据量小（约 50 部作品 / 50 位作者 / 80 个地点 / 12 个流派），
每次搜索直接全量读取内存中打分，无需引入全文索引。
"""

import re
import sqlite3

from database import get_db_connection

# 每类结果的默认/最大返回条数
_DEFAULT_PER_GROUP = 5
_MAX_PER_GROUP = 20

# 容错（fuzzy）结果在每组内的条数上限，防止近似匹配刷屏
_FUZZY_PER_GROUP_CAP = 3

# 评分常量：分数越高越相关
_SCORE_EXACT = 100     # 归一化后完全相等
_SCORE_PREFIX = 85     # 候选以关键词开头
_SCORE_CONTAINS = 70   # 候选包含关键词
_SCORE_TOKEN = 60      # 关键词的每个分词都是候选的子串
_SCORE_FUZZY_BASE = 40  # 容错匹配基准分（再按编辑距离递减）

# 匹配类型标识（随结果返回，供调用方/AI 判断匹配可靠程度）
MATCH_EXACT = "exact"
MATCH_PREFIX = "prefix"
MATCH_CONTAINS = "contains"
MATCH_TOKEN = "token"
MATCH_FUZZY = "fuzzy"

# 英文单词切分（用于分词级容错），中文整串不切分
_WORD_SPLIT_RE = re.compile(r"\s+")

# 去除所有空白与人名分隔符（用于"百年 孤独"→"百年孤独"、
# "列夫·托尔斯泰"→"列夫托尔斯泰"这类连续化匹配）
_WHITESPACE_RE = re.compile(r"\s+")
_SEPARATOR_RE = re.compile(r"[·•・]")


# ---------- 文本归一化 ----------

def normalize_text(text) -> str:
    """归一化：去首尾空格、连续空白合并为单个空格、英文转小写。"""
    if text is None:
        return ""
    return _WHITESPACE_RE.sub(" ", str(text)).strip().casefold()


def squeeze_text(text) -> str:
    """去除全部空白与人名分隔符：让"百年 孤独"能命中"百年孤独"。"""
    if text is None:
        return ""
    return _SEPARATOR_RE.sub("", _WHITESPACE_RE.sub("", str(text))).casefold()


# ---------- Damerau-Levenshtein 编辑距离（带长度差剪枝） ----------

def _edit_distance_at_most(a: str, b: str, k: int) -> int:
    """计算 a、b 的 Damerau-Levenshtein 距离；若确定超过 k 则提前返回 k + 1。

    使用滚动数组实现，空间 O(len(b))；长度差超过 k 直接剪枝。
    """
    la, lb = len(a), len(b)
    if abs(la - lb) > k:
        return k + 1
    if a == b:
        return 0
    # 保证 b 是较短的串，减少内层长度
    if la < lb:
        a, b, la, lb = b, a, lb, la
    prev2 = None  # 上上行（换位转移用）
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        ca = a[i - 1]
        row_min = cur[0]
        for j in range(1, lb + 1):
            cost = 0 if ca == b[j - 1] else 1
            best = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            # 相邻换位（Damerau 扩展）：a[i-2]==b[j-1] 且 a[i-1]==b[j-2]
            if (
                i > 1 and j > 1
                and ca == b[j - 2] and a[i - 2] == b[j - 1]
                and prev2 is not None
            ):
                best = min(best, prev2[j - 2] + 1)
            cur[j] = best
            if best < row_min:
                row_min = best
        if row_min > k:
            return k + 1
        prev2, prev = prev, cur
    return prev[lb]


def _fuzzy_threshold(length: int) -> int:
    """按关键词长度给出容错编辑距离阈值：<=4 字容错 1，>=5 字容错 2。

    关键词很短（1 字）时返回 0（不做容错），避免大量无关命中。
    """
    if length <= 1:
        return 0
    if length <= 4:
        return 1
    return 2


def _fuzzy_substring_score(query_sq: str, value_sq: str, thr: int) -> int | None:
    """滑动窗口子串容错：在候选串上寻找与关键词编辑距离 <= thr 的窗口。

    解决"托尔斯基→列夫·托尔斯泰"这类关键词只是候选一部分、
    且候选含分隔符/前后缀导致整串距离过大的情形。
    返回最小编辑距离（<= thr），无匹配返回 None。
    """
    lq, lv = len(query_sq), len(value_sq)
    if lq == 0 or lv == 0 or thr <= 0:
        return None
    # 快速剪枝：无任何公共字符时，每个字符都至少需要一次编辑，
    # 关键词长度超过阈值则必然不可能匹配（也天然跳过中英文跨语言组合）
    if lq > thr and not (set(query_sq) & set(value_sq)):
        return None
    best = None
    lo = max(1, lq - thr)
    hi = min(lv, lq + thr)
    for size in range(lo, hi + 1):
        for start in range(0, lv - size + 1):
            d = _edit_distance_at_most(query_sq, value_sq[start:start + size], thr)
            if best is None or d < best:
                best = d
                if best <= 1:
                    # 已足够接近，无需继续扫描（完全相等的情形已被 contains 覆盖）
                    return best
    return best if best is not None and best <= thr else None


def _token_hit(t: str, w: str) -> bool:
    """判断查询单词 t 是否命中候选单词 w（分词级匹配 / 容错共用）。"""
    if t == w:
        return True
    thr_t = _fuzzy_threshold(len(t))
    if thr_t > 0 and _edit_distance_at_most(t, w, thr_t) <= thr_t:
        return True
    # 词序连续化：用户把多个词连写（"oldman" 含 "old"/"man"）
    if len(w) >= 3 and w in t:
        return True
    # 输入了单词的一部分（"eighty" 命中……反向："eig" ⊂ "eighty"）
    if len(t) >= 3 and t in w:
        return True
    return False


# ---------- 单字段评分 ----------

def score_field(query_norm: str, query_sq: str, raw_value) -> tuple[int, str | None]:
    """对单个字段值打分，返回 (最高分, 匹配类型)；完全不匹配返回 (0, None)。

    匹配优先级：精确 > 前缀 > 包含 > 分词全命中 > 容错。
    query_norm 为归一化关键词；query_sq 为去空白关键词（中文匹配用）。
    """
    if not query_norm:
        return 0, None
    value_norm = normalize_text(raw_value)
    if not value_norm:
        return 0, None

    best_score, best_type = 0, None

    def consider(score: int, mtype: str):
        nonlocal best_score, best_type
        if score > best_score:
            best_score, best_type = score, mtype

    value_sq = squeeze_text(raw_value)

    # 1) 精确匹配（含"百年 孤独"→去空白后相等的情形）
    if query_norm == value_norm or (query_sq and query_sq == value_sq):
        consider(_SCORE_EXACT, MATCH_EXACT)
    # 2) 前缀匹配
    if value_norm.startswith(query_norm) or (query_sq and value_sq.startswith(query_sq)):
        consider(_SCORE_PREFIX, MATCH_PREFIX)
    # 3) 包含匹配（原生形态 + 去空白形态，覆盖中英混排）
    if query_norm in value_norm or (query_sq and query_sq in value_sq):
        consider(_SCORE_CONTAINS, MATCH_CONTAINS)
    # 4) 分词全命中：英文多词查询（如 "war peace"）的每个词都出现即可
    tokens = [t for t in _WORD_SPLIT_RE.split(query_norm) if t]
    if len(tokens) > 1 and all(t in value_norm or (t and t in value_sq) for t in tokens):
        consider(_SCORE_TOKEN, MATCH_TOKEN)

    # 5) 轻量容错：仅关键词 >= 2 字符时启用
    if len(query_sq) >= 2:
        thr = _fuzzy_threshold(len(query_sq))
        if thr > 0:
            # 子串窗口容错（覆盖整串近似与"关键词是候选一部分"两种情形）
            dist = _fuzzy_substring_score(query_sq, value_sq, thr)
            if dist is not None:
                consider(_SCORE_FUZZY_BASE - dist * 5, MATCH_FUZZY)
            elif len(tokens) >= 2:
                # 分词级容错（英文多词查询）：每个词都命中才算匹配
                q_tokens = [t for t in tokens if len(t) >= 2]
                v_words = [w for w in _WORD_SPLIT_RE.split(value_norm) if w]
                if len(q_tokens) >= 2 and v_words:
                    if all(any(_token_hit(t, w) for w in v_words) for t in q_tokens):
                        consider(_SCORE_FUZZY_BASE - 5, MATCH_FUZZY)

    return best_score, best_type


# ---------- 数据装载（全量小表，只读） ----------

def _rows(conn: sqlite3.Connection, sql: str, params=()) -> list[dict]:
    return [
        {key: row[key] for key in row.keys()}
        for row in conn.execute(sql, params).fetchall()
    ]


def load_search_data() -> dict:
    """一次性读取搜索所需的全部数据（小表全量，只读）。"""
    conn = get_db_connection()
    try:
        books = _rows(
            conn,
            "SELECT id, title, original_title, language, publication_year "
            "FROM books ORDER BY id ASC",
        )
        authors = _rows(
            conn,
            "SELECT id, name, nationality FROM authors ORDER BY id ASC",
        )
        # 作品 ↔ 地点（供国家维度的作品数统计）
        book_place_rows = _rows(
            conn,
            "SELECT book_id, place_id FROM book_places ORDER BY book_id ASC",
        )
        # 作品 ↔ 作者（聚合作者名，供作品搜索与展示）
        book_author_rows = _rows(
            conn,
            """
            SELECT ba.book_id, a.id AS author_id, a.name AS author_name
            FROM book_authors AS ba
            JOIN authors AS a ON a.id = ba.author_id
            ORDER BY ba.book_id ASC, a.id ASC
            """,
        )
        # 作品 ↔ 流派
        book_genre_rows = _rows(
            conn,
            """
            SELECT bg.book_id, g.id AS genre_id, g.name AS genre_name
            FROM book_genres AS bg
            JOIN genres AS g ON g.id = bg.genre_id
            ORDER BY bg.book_id ASC, g.id ASC
            """,
        )
        places = _rows(
            conn,
            """
            SELECT id, name, place_type, is_fictional, country, region
            FROM places ORDER BY id ASC
            """,
        )
        genres = _rows(
            conn, "SELECT id, name, description FROM genres ORDER BY id ASC"
        )
    finally:
        conn.close()

    authors_by_book: dict[int, list[dict]] = {}
    for r in book_author_rows:
        authors_by_book.setdefault(r["book_id"], []).append(
            {"id": r["author_id"], "name": r["author_name"]}
        )
    genres_by_book: dict[int, list[dict]] = {}
    for r in book_genre_rows:
        genres_by_book.setdefault(r["book_id"], []).append(
            {"id": r["genre_id"], "name": r["genre_name"]}
        )
    place_ids_by_book: dict[int, list[int]] = {}
    for r in book_place_rows:
        place_ids_by_book.setdefault(r["book_id"], []).append(r["place_id"])
    for b in books:
        b["_authors"] = authors_by_book.get(b["id"], [])
        b["_genres"] = genres_by_book.get(b["id"], [])
        b["_place_ids"] = place_ids_by_book.get(b["id"], [])

    return {
        "books": books,
        "authors": authors,
        "places": places,
        "genres": genres,
        "_places_by_id": {p["id"]: p for p in places},
    }


# ---------- 通用打分排序 ----------

def _match_candidates(query: str, candidates: list[tuple[dict, list]]) -> tuple[list[dict], list[dict]]:
    """对候选列表打分排序。

    candidates 每项为 (entity, fields)；fields 为 [(字段值, 字段标签), ...]。
    返回 (确定级命中列表, 容错命中列表)，各自按分数降序；
    容错列表已按 _FUZZY_PER_GROUP_CAP 限量。
    调用方决定容错结果的启停策略（全局兜底）。
    """
    query_norm = normalize_text(query)
    query_sq = squeeze_text(query)
    if not query_norm:
        return [], []

    scored = []
    for entity, fields in candidates:
        best_score, best_type, best_field, best_idx = 0, None, None, -1
        for idx, (value, label) in enumerate(fields):
            score, mtype = score_field(query_norm, query_sq, value)
            if score > best_score:
                best_score, best_type, best_field, best_idx = score, mtype, label, idx
        if best_score <= 0:
            continue
        # 次级字段（非首个字段，如作者名/国家/流派）上的容错命中降权，
        # 降低"巴黎→巴西"这类弱相关近似结果的排序位置
        if best_type == MATCH_FUZZY and best_idx > 0:
            best_score -= 10
        scored.append(
            {
                "entity": entity,
                "score": best_score,
                "match_type": best_type,
                "matched_field": best_field,
            }
        )

    scored.sort(key=lambda x: (-x["score"], x["entity"]["id"]))

    solid = [x for x in scored if x["match_type"] != MATCH_FUZZY]
    fuzzy = [
        x for x in scored if x["match_type"] == MATCH_FUZZY
    ][:_FUZZY_PER_GROUP_CAP]
    return solid, fuzzy


# ---------- 面向全站搜索的聚合检索 ----------

def search_all(query: str, per_group: int = _DEFAULT_PER_GROUP) -> dict:
    """统一模糊检索：跨作品/作者/地点/国家/流派返回分组结果。

    容错为全局兜底：仅当本次查询在任何分组都没有确定级命中
    （精确/前缀/包含/分词）时，才返回容错（近似）结果，且每组限量，
    避免模糊匹配返回大量无关结果。

    返回结构：
    {
      "query": 清洗后的关键词, "total": 总命中条数,
      "fuzzy_fallback": 是否为容错兜底结果,
      "groups": {
        "works":    [{id, title, original_title, publication_year, authors, genres, match_type, matched_by}],
        "authors":  [{id, name, nationality, work_titles, match_type, matched_by}],
        "places":   [{id, name, place_type, is_fictional, country, region, match_type, matched_by}],
        "countries":[{name, place_id, work_count, match_type}],
        "genres":   [{id, name, description, work_count, match_type}],
      }
    }
    """
    per_group = max(1, min(int(per_group or _DEFAULT_PER_GROUP), _MAX_PER_GROUP))
    cleaned = re.sub(r"\s+", " ", str(query or "")).strip()
    if not cleaned:
        return {"query": "", "total": 0, "fuzzy_fallback": False, "groups": _empty_groups()}

    data = load_search_data()

    # --- 作品：书名 / 原名 / 作者名 / 流派名 任一命中 ---
    book_candidates = []
    for b in data["books"]:
        fields = [(b["title"], "title")]
        if b["original_title"]:
            fields.append((b["original_title"], "original_title"))
        for a in b["_authors"]:
            fields.append((a["name"], "author"))
        for g in b["_genres"]:
            fields.append((g["name"], "genre"))
        book_candidates.append((b, fields))
    works_solid, works_fuzzy = _match_candidates(cleaned, book_candidates)

    # --- 作者：姓名 / 国籍 任一命中 ---
    author_candidates = [
        (a, [(a["name"], "name"), (a["nationality"], "nationality")])
        for a in data["authors"]
    ]
    authors_solid, authors_fuzzy = _match_candidates(cleaned, author_candidates)

    # --- 地点：名称 / 国家 / 区域 任一命中 ---
    place_candidates = [
        (p, [(p["name"], "name"), (p["country"], "country"), (p["region"], "region")])
        for p in data["places"]
    ]
    places_solid, places_fuzzy = _match_candidates(cleaned, place_candidates)

    # --- 流派：流派名命中 ---
    genre_candidates = [(g, [(g["name"], "name")]) for g in data["genres"]]
    genres_solid, genres_fuzzy = _match_candidates(cleaned, genre_candidates)

    # --- 国家候选：country 类型地点 + 各地点 country 字段 + 作者国籍 ---
    q_norm, q_sq = normalize_text(cleaned), squeeze_text(cleaned)
    country_hits: dict[str, dict] = {}

    def add_country(name, place_id, score, mtype):
        if score <= 0 or not name:
            return
        cur = country_hits.get(name)
        if cur is None or score > cur["_score"]:
            country_hits[name] = {
                "name": name,
                "place_id": place_id if cur is None else cur["place_id"],
                "match_type": mtype,
                "_score": score,
            }

    for p, is_solid in (
        [(x, True) for x in places_solid] + [(x, False) for x in places_fuzzy]
    ):
        ent = p["entity"]
        if ent["place_type"] == "country":
            add_country(ent["name"], ent["id"], p["score"], p["match_type"])

    # 非国家类型地点的 country 字段 / 作者国籍中出现的国家名（独立打分）
    for p in data["places"]:
        if p["country"]:
            score, mtype = score_field(q_norm, q_sq, p["country"])
            add_country(p["country"], None, score, mtype)
    for a in data["authors"]:
        if a["nationality"]:
            score, mtype = score_field(q_norm, q_sq, a["nationality"])
            add_country(a["nationality"], None, score, mtype)

    # --- 全局容错兜底判定 ---
    solid_exists = bool(
        works_solid or authors_solid or places_solid or genres_solid
        or any(c["match_type"] != MATCH_FUZZY for c in country_hits.values())
    )
    if solid_exists:
        works, authors, places, genres = (
            works_solid, authors_solid, places_solid, genres_solid
        )
        country_hits = {
            n: c for n, c in country_hits.items()
            if c["match_type"] != MATCH_FUZZY
        }
    else:
        works, authors, places, genres = (
            works_fuzzy, authors_fuzzy, places_fuzzy, genres_fuzzy
        )

    # --- 组装输出 ---
    author_titles: dict[int, list[str]] = {}
    for b in data["books"]:
        for a in b["_authors"]:
            author_titles.setdefault(a["id"], []).append(b["title"])
    genre_counts: dict[int, int] = {}
    for b in data["books"]:
        for g in b["_genres"]:
            genre_counts[g["id"]] = genre_counts.get(g["id"], 0) + 1

    work_items = []
    for w in works[:per_group]:
        b = w["entity"]
        work_items.append({
            "id": b["id"],
            "title": b["title"],
            "original_title": b["original_title"],
            "publication_year": b.get("publication_year"),
            "authors": [a["name"] for a in b["_authors"]],
            "genres": [g["name"] for g in b["_genres"]],
            "match_type": w["match_type"],
            "matched_by": w["matched_field"],
        })

    author_items = []
    for a in authors[:per_group]:
        ent = a["entity"]
        author_items.append({
            "id": ent["id"],
            "name": ent["name"],
            "nationality": ent["nationality"],
            "work_titles": author_titles.get(ent["id"], []),
            "match_type": a["match_type"],
            "matched_by": a["matched_field"],
        })

    place_items = []
    for p in places[:per_group]:
        ent = p["entity"]
        if ent["place_type"] == "country":
            continue  # 国家类型地点已归入 countries 分组
        place_items.append({
            "id": ent["id"],
            "name": ent["name"],
            "place_type": ent["place_type"],
            "is_fictional": ent["is_fictional"],
            "country": ent["country"],
            "region": ent["region"],
            "match_type": p["match_type"],
            "matched_by": p["matched_field"],
        })

    country_list = sorted(
        country_hits.values(), key=lambda x: (-x["_score"], x["name"])
    )[:per_group]
    country_items = []
    for c in country_list:
        c["work_count"] = _count_works_for_country(data, c["name"])
        c.pop("_score", None)
        country_items.append(c)

    genre_items = []
    for g in genres[:per_group]:
        ent = g["entity"]
        genre_items.append({
            "id": ent["id"],
            "name": ent["name"],
            "description": ent["description"],
            "work_count": genre_counts.get(ent["id"], 0),
            "match_type": g["match_type"],
        })

    groups = {
        "works": work_items,
        "authors": author_items,
        "places": place_items,
        "countries": country_items,
        "genres": genre_items,
    }
    total = sum(len(v) for v in groups.values())
    return {
        "query": cleaned,
        "total": total,
        "fuzzy_fallback": bool(total) and not solid_exists,
        "groups": groups,
    }


def _count_works_for_country(data: dict, country_name: str) -> int:
    """统计某国家关联的作品数（作者国籍或作品关联地点的 country 命中，去重）。"""
    target = normalize_text(country_name)
    book_ids = set()
    # 作者国籍命中 → 其全部作品
    for a in data["authors"]:
        if normalize_text(a["nationality"]) == target:
            for b in data["books"]:
                if any(x["id"] == a["id"] for x in b["_authors"]):
                    book_ids.add(b["id"])
    # 作品关联地点的 country 命中
    for b in data["books"]:
        if b["id"] in book_ids:
            continue
        for pid in b.get("_place_ids", []):
            place = data["_places_by_id"].get(pid)
            if place is not None and normalize_text(place["country"]) == target:
                book_ids.add(b["id"])
                break
    return len(book_ids)


def _empty_groups() -> dict:
    return {
        "works": [],
        "authors": [],
        "places": [],
        "countries": [],
        "genres": [],
    }


# ---------- 面向 AI 工具的单类检索 ----------

def search_books_fuzzy(keyword: str, limit: int | None = None) -> dict:
    """按关键词模糊搜索作品（书名/原名/作者名/流派名，含容错），按相关度排序。

    返回 {"total": 命中总数, "exact_match_exists": 是否存在确定级命中,
    "items": [...]}；items 附 match_type / matched_by，供 AI 区分
    "确定命中"与"近似候选"。容错仅在无任何确定级命中时兜底返回。
    """
    cleaned = re.sub(r"\s+", " ", str(keyword or "")).strip()
    if not cleaned:
        return {"total": 0, "exact_match_exists": False, "items": []}
    limit = max(1, min(int(limit or 5), _MAX_PER_GROUP))

    data = load_search_data()
    candidates = []
    for b in data["books"]:
        fields = [(b["title"], "title")]
        if b["original_title"]:
            fields.append((b["original_title"], "original_title"))
        for a in b["_authors"]:
            fields.append((a["name"], "author"))
        for g in b["_genres"]:
            fields.append((g["name"], "genre"))
        candidates.append((b, fields))

    solid, fuzzy = _match_candidates(cleaned, candidates)
    scored = solid if solid else fuzzy
    items = []
    for w in scored[:limit]:
        b = w["entity"]
        items.append({
            "id": b["id"],
            "title": b["title"],
            "original_title": b["original_title"],
            "language": b.get("language"),
            "publication_year": b.get("publication_year"),
            "author_names": [a["name"] for a in b["_authors"]],
            "genre_names": [g["name"] for g in b["_genres"]],
            "match_type": w["match_type"],
            "matched_by": w["matched_field"],
        })
    return {
        "total": len(scored),
        "exact_match_exists": bool(solid),
        "items": items,
    }


def search_places_fuzzy(keyword: str, limit: int | None = None) -> dict:
    """按关键词模糊搜索地点（名称/国家/区域，含容错），按相关度排序。"""
    cleaned = re.sub(r"\s+", " ", str(keyword or "")).strip()
    if not cleaned:
        return {"total": 0, "exact_match_exists": False, "items": []}
    limit = max(1, min(int(limit or 5), _MAX_PER_GROUP))

    data = load_search_data()
    candidates = [
        (p, [(p["name"], "name"), (p["country"], "country"), (p["region"], "region")])
        for p in data["places"]
    ]
    solid, fuzzy = _match_candidates(cleaned, candidates)
    scored = solid if solid else fuzzy
    items = []
    for p in scored[:limit]:
        ent = p["entity"]
        items.append({
            "id": ent["id"],
            "name": ent["name"],
            "place_type": ent["place_type"],
            "is_fictional": ent["is_fictional"],
            "country": ent["country"],
            "region": ent["region"],
            "match_type": p["match_type"],
            "matched_by": p["matched_field"],
        })
    return {"total": len(scored), "exact_match_exists": bool(solid), "items": items}


def search_authors_fuzzy(keyword: str, limit: int | None = None) -> dict:
    """按关键词模糊搜索作者（姓名/国籍，含容错），按相关度排序。"""
    cleaned = re.sub(r"\s+", " ", str(keyword or "")).strip()
    if not cleaned:
        return {"total": 0, "exact_match_exists": False, "items": []}
    limit = max(1, min(int(limit or 5), _MAX_PER_GROUP))

    data = load_search_data()
    author_titles: dict[int, list[str]] = {}
    for b in data["books"]:
        for a in b["_authors"]:
            author_titles.setdefault(a["id"], []).append(b["title"])
    candidates = [
        (a, [(a["name"], "name"), (a["nationality"], "nationality")])
        for a in data["authors"]
    ]
    solid, fuzzy = _match_candidates(cleaned, candidates)
    scored = solid if solid else fuzzy
    items = []
    for a in scored[:limit]:
        ent = a["entity"]
        items.append({
            "id": ent["id"],
            "name": ent["name"],
            "nationality": ent["nationality"],
            "work_titles": author_titles.get(ent["id"], []),
            "match_type": a["match_type"],
            "matched_by": a["matched_field"],
        })
    return {"total": len(scored), "exact_match_exists": bool(solid), "items": items}
