"""AI 作品识别模块（自主添加书籍功能）。

根据用户输入的书名（可选作者），调用 DeepSeek 生成结构化的作品信息草案，
供前端展示并经用户确认后再保存。本模块只做"识别与提取"，绝不写数据库，
也绝不生成经纬度（坐标一律由后端根据现有地点库匹配决定）。

设计要点：
- 复用 agent/llm_client.py 的 DeepSeek 客户端与模型配置，不修改该文件；
- 使用 openai SDK 支持的 JSON 输出模式（response_format=json_object），
  不新增任何依赖；
- 模型输出必须经过 JSON 解析 + 字段校验 + 规范化，非法字段直接丢弃；
- AI 调用失败 / 超时 / 输出格式错误时抛出 BookLookupError，
  由路由层转换为 502 等清晰错误。

能力边界（必须如实告知用户）：
- 模型基于自身知识识别作品，不具备实时联网检索能力；
- 结果未经互联网核实，地点坐标是否可信由后端地点库匹配结果决定，
  与本模块输出无关。
"""

import json
import logging

from agent.llm_client import DEEPSEEK_MODEL, _build_client

logger = logging.getLogger(__name__)

# 单次 AI 调用超时（秒）。识别 + 提取地点属于单轮大输出，留足时间。
_LOOKUP_TIMEOUT_SECONDS = 60

# 允许的作品-地点关系类型（与数据库 book_places.relation_type CHECK 约束一致）
_ALLOWED_RELATION_TYPES = ("setting", "depiction")

# 系统提示词：约束模型只做识别提取，禁止编造、禁止输出经纬度
_SYSTEM_PROMPT = (
    "你是文学作品信息识别助手，根据你已有的文学知识识别用户给出的作品并提取信息。"
    "你无法联网检索，只依据自身知识回答；不确定的内容必须返回 null，"
    "绝对不要编造作品、作者、国家、流派、地点或经纬度。"
)

# 用户消息模板：给出严格的 JSON 输出格式要求
_USER_PROMPT_TEMPLATE = """请识别以下作品并只输出一个 JSON 对象，不要输出任何其他文字或代码块标记。

书名：{title}
作者（可能为空）：{author}

JSON 格式要求（字段名必须完全一致）：
{{
  "found": 布尔值，是否能确定用户指的是哪部作品；
  "ambiguous": 布尔值，书名对应多部不同作品且无法根据作者确定时为 true；
  "candidates": [{{"title": "候选书名", "author": "候选作者", "year": 候选年份或null}}]，仅 ambiguous=true 时提供，最多 5 个；
  "title": 确定后的规范书名（中文常用译名），无法确定则为 null；
  "author": 作者规范译名，无法确定则为 null；
  "country": 作品所属国家或地区（指作品的文学归属国，如作者国籍），无法确定则为 null；
  "genre": 最主要的文学流派或类型（如 魔幻现实主义、反乌托邦），无法确定则为 null；
  "description": 不超过 80 字的作品简介，无法确定则为 null；
  "places": [
    {{
      "name": 地点名称（中文通用译名），
      "country": 地点所属国家或 null，
      "relation_type": "setting"（故事发生地/重要情节发生地）或 "depiction"（作品涉及或描写的其他地点），
      "is_fictional": 布尔值，虚构地点必须为 true
    }}
  ]
}}

places 提取规则：
1. 只提取作品内容中真实出现或明确涉及的地点（城市、地区、国家均可）；
2. 作者的出生地、国籍、长期居住地不能直接当作故事发生地；
3. 虚构地点（如完全虚构的小镇）必须标记 is_fictional=true；
4. 不确定是否与作品相关的地点不要输出；
5. 没有可靠地点时 places 为空数组；
6. 绝对不要输出任何经纬度数值。

无法识别任何作品时：found=false，其余字段为 null 或空数组。"""


class BookLookupError(Exception):
    """AI 作品识别失败（调用失败 / 超时 / 输出格式非法）。"""


def _extract_json_object(text: str) -> dict:
    """从模型输出文本中提取第一个 JSON 对象。

    兼容模型偶尔输出的代码块标记或前后多余文字。
    解析失败抛出 BookLookupError。
    """
    if not text or not text.strip():
        raise BookLookupError("AI 返回内容为空")

    text = text.strip()
    # 去掉可能的 markdown 代码块标记
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise BookLookupError("AI 返回内容中没有找到 JSON 对象")

    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        raise BookLookupError("AI 返回的内容不是合法 JSON")

    if not isinstance(data, dict):
        raise BookLookupError("AI 返回的 JSON 不是对象")
    return data


def _clean_str(value) -> str | None:
    """把任意值清洗为非空字符串，空值返回 None。"""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _clean_bool(value, default=False) -> bool:
    """把模型输出的布尔值规范化（兼容 0/1、'true' 等写法）。"""
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes")
    return default


def _normalize_candidates(raw) -> list[dict]:
    """规范化候选作品列表：最多 5 个，只保留 title/author/year。"""
    out = []
    if not isinstance(raw, list):
        return out
    for item in raw[:5]:
        if not isinstance(item, dict):
            continue
        cand = {
            "title": _clean_str(item.get("title")),
            "author": _clean_str(item.get("author")),
            "year": item.get("year") if isinstance(item.get("year"), int) else None,
        }
        if cand["title"]:
            out.append(cand)
    return out


def _normalize_places(raw) -> list[dict]:
    """规范化地点列表：丢弃非法项，relation_type 非法时默认 setting。"""
    out = []
    if not isinstance(raw, list):
        return out
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = _clean_str(item.get("name"))
        if not name:
            continue
        relation = _clean_str(item.get("relation_type"))
        if relation not in _ALLOWED_RELATION_TYPES:
            relation = "setting"
        # 同一地点 + 同一关系只保留一条
        key = (name, relation)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "name": name,
            "country": _clean_str(item.get("country")),
            "relation_type": relation,
            "is_fictional": _clean_bool(item.get("is_fictional")),
        })
    return out


def validate_draft(data: dict, fallback_title: str) -> dict:
    """校验并规范化模型输出的草案，保证返回结构稳定。

    任何字段的缺失、类型错误都被安全兜底，不会抛出异常
    （结构性的失败在 JSON 解析阶段已经处理）。
    """
    found = _clean_bool(data.get("found"), False)
    ambiguous = _clean_bool(data.get("ambiguous"), False)

    title = _clean_str(data.get("title")) or (fallback_title if found else None)
    author = _clean_str(data.get("author"))
    # 无法确定具体作品时，不输出可能误导用户的单一定稿信息
    if ambiguous:
        title = title or fallback_title

    return {
        "found": found,
        "ambiguous": ambiguous,
        "candidates": _normalize_candidates(data.get("candidates")),
        "title": title,
        "author": author,
        "country": _clean_str(data.get("country")),
        "genre": _clean_str(data.get("genre")),
        "description": _clean_str(data.get("description")),
        "places": [] if ambiguous or not found else _normalize_places(data.get("places")),
    }


async def lookup_book(title: str, author: str | None = None, client=None) -> dict:
    """识别作品并返回结构化草案（不写数据库，不生成经纬度）。

    Args:
        title : 书名，必填（调用方已做非空校验）。
        author: 作者，选填。提供后可帮助消歧。
        client: 可选，注入 AsyncOpenAI 客户端（测试用），None 时按配置构建。

    Returns:
        规范化后的作品草案 dict，字段见模块 docstring。

    Raises:
        BookLookupError: AI 调用失败、超时或输出无法解析为合法结构。
    """
    if client is None:
        try:
            client = _build_client()
        except ValueError as exc:
            # 缺少 API Key 等配置问题
            raise BookLookupError(f"AI 服务配置错误：{exc}")

    prompt = _USER_PROMPT_TEMPLATE.format(
        title=title.strip(),
        author=(author or "").strip() or "（未提供）",
    )
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    try:
        response = await client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            timeout=_LOOKUP_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        logger.warning("作品识别 AI 调用失败: %s", type(exc).__name__)
        raise BookLookupError("AI 服务调用失败，请稍后重试")

    content = response.choices[0].message.content if response.choices else None
    data = _extract_json_object(content)
    return validate_draft(data, fallback_title=title.strip())
