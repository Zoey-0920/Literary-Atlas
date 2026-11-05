"""Literary Atlas Agent 核心执行逻辑。

负责把只读数据库工具注册给大模型，并执行多轮工具调用循环：
模型提出 tool_calls -> 后端执行对应只读工具 -> 结果回传模型 -> 直到模型给出最终回答。

安全约束：
- 只执行白名单内的五个只读工具，不执行任意 Python 函数。
- 不执行模型生成的 SQL。
- 限制最大工具调用轮数，避免无限循环。
- 工具执行失败只返回脱敏错误，不泄露 API Key / 数据库密码等敏感信息。
"""

import json
import logging

from agent.llm_client import DEEPSEEK_MODEL, _build_client
from agent.tools import (
    get_book_detail,
    get_reading_records,
    get_reading_statistics,
    list_books,
    search_authors,
    search_books,
    search_places,
)

# 调试日志：记录每一轮的工具调用与 finish_reason，便于排查循环问题。
# 默认 DEBUG 级别不会输出到控制台，仅需排查时提升日志级别即可；绝不记录 API Key。
logger = logging.getLogger(__name__)

# 最大工具调用轮数（每轮 = 一次模型调用 + 一次工具执行）
MAX_TOOL_ROUNDS = 5

# 达到最大轮数仍未得到最终回答时返回的提示
_MAX_ROUNDS_MESSAGE = "已达到最大工具调用轮数，未能生成最终回答。"

# 引导模型减少无意义的重复工具调用，并保证推荐来自数据库真实作品
_SYSTEM_PROMPT = (
    "你是「文学地理图谱」助手，基于数据库中的真实文学资料回答用户问题。"
    "规则：1) 涉及具体作品、作者、地点、阅读记录时先调用工具查询数据库，再据实回答；"
    "2) 已获得足够信息后直接给出最终回答，不要反复调用同一个工具；"
    "3) 推荐作品必须来自数据库真实存在的作品，不要虚构；"
    "4) 数据库没有的信息不要编造，可如实说明不确定；"
    "5) 搜索工具支持不完整书名、部分作者名、地点/国家/流派关键词、英文大小写"
    "不敏感及少量拼写容错；结果按相关度排序并带 match_type 字段："
    "exact/prefix/contains/token 表示确定级命中，fuzzy 表示近似匹配（可能是用户"
    "输入有误的候选）。仅当存在确定级命中且能明确对应用户所指时，才把它当作"
    "确定的作品/作者信息；若只有 fuzzy 匹配或多个候选，应向用户列出候选并请其"
    "确认，绝不能把模糊匹配结果当成用户确定指代的作品。"
)

# ---------- 1. 工具注册（OpenAI tools 格式，参数定义与真实函数一致） ----------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_books",
            "description": (
                "模糊搜索文学作品。匹配书名、原名、作者姓名、文学流派名；"
                "支持不完整书名、部分作者名、英文大小写不敏感及少量拼写容错。"
                "返回作品 ID、书名、原名、语言、出版年份、作者、流派、match_type。"
                "结果按相关度排序：match_type 为 exact/prefix/contains/token 表示"
                "确定级命中，fuzzy 表示近似匹配（仅作候选，需用户确认）。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "书名/作者名/流派名关键词，可以是不完整片段",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回条数上限，默认 5，最大 20",
                    },
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_authors",
            "description": (
                "模糊搜索作家。匹配作者姓名、国籍；支持不完整姓名、"
                "英文大小写不敏感及少量拼写容错。返回作者 ID、姓名、国籍、"
                "其作品名列表、match_type。结果按相关度排序，fuzzy 为近似候选。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "作者姓名或国籍关键词，可以是不完整片段",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回条数上限，默认 5，最大 20",
                    },
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_books",
            "description": "列出数据库中的全部作品（按 ID 升序），返回作品 ID、书名、原名、语言、出版年份。用于推荐或浏览全部作品时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回条数上限，默认 100，最大 100",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "偏移量，默认 0",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_places",
            "description": (
                "模糊搜索地点。匹配地点名称、所属国家、所属区域；"
                "支持不完整名称、英文大小写不敏感及少量拼写容错。"
                "返回地点 ID、名称、类型、是否虚构、国家、地区、match_type。"
                "结果按相关度排序，fuzzy 为近似候选。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "地点/国家/区域名称关键词，可以是不完整片段",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回条数上限，默认 5，最大 20",
                    },
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_book_detail",
            "description": "根据作品 ID 查询作品详情，关联作者、地点与文学流派。",
            "parameters": {
                "type": "object",
                "properties": {
                    "book_id": {"type": "integer", "description": "作品 ID"},
                },
                "required": ["book_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_reading_records",
            "description": "查询当前用户的个人阅读记录，可按阅读状态筛选（want_to_read / reading / finished）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "可选，阅读状态：want_to_read（想读）/ reading（在读）/ finished（读完）",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_reading_statistics",
            "description": "统计当前用户的阅读记录数量（想读 / 在读 / 读完 / 总数）。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

# 工具名称 -> 实际 Python 函数（白名单，仅允许调用这些）
TOOL_HANDLERS = {
    "search_books": search_books,
    "search_authors": search_authors,
    "list_books": list_books,
    "search_places": search_places,
    "get_book_detail": get_book_detail,
    "get_reading_records": get_reading_records,
    "get_reading_statistics": get_reading_statistics,
}


# ---------- 2. 工具执行 ----------

def _execute_tool(name: str, arguments_json: str) -> str:
    """执行一个白名单内的只读工具，返回结果的 JSON 字符串。

    任何失败都返回脱敏后的 {"error": ...}，不向上抛出敏感信息。
    """
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        # 未知工具：安全拒绝，绝不执行任意函数
        return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)

    try:
        args = json.loads(arguments_json) if arguments_json else {}
    except json.JSONDecodeError:
        return json.dumps({"error": "工具参数 JSON 解析失败"}, ensure_ascii=False)

    if not isinstance(args, dict):
        return json.dumps({"error": "工具参数必须是 JSON 对象"}, ensure_ascii=False)

    try:
        result = handler(**args)
    except TypeError as exc:
        return json.dumps(
            {"error": f"工具参数不匹配: {exc}"}, ensure_ascii=False
        )
    except Exception:
        # 不泄露异常细节（可能含路径、密码等），只返回通用错误
        return json.dumps({"error": "工具执行失败"}, ensure_ascii=False)

    try:
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception:
        return json.dumps({"error": "工具结果序列化失败"}, ensure_ascii=False)


def _assistant_tool_call_message(message) -> dict:
    """把模型的 assistant 消息（含 tool_calls）转成标准消息格式。"""
    return {
        "role": "assistant",
        "content": message.content,
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in message.tool_calls
        ],
    }


# ---------- 3. 多轮调用循环 ----------

async def chat_with_agent(message: str, client=None) -> str:
    """接收用户问题，返回模型最终生成的文本回答。

    Args:
        message: 用户问题。
        client : 可选，传入已构建的 AsyncOpenAI 客户端（测试时用于注入 Mock）。
                 为 None 时使用默认 DeepSeek 客户端。

    Returns:
        模型最终回答文本。
    """
    if client is None:
        client = _build_client()

    # 对话上下文：首条为系统提示 + 用户消息，后续追加 assistant/tool 消息
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]

    for round_index in range(MAX_TOOL_ROUNDS):
        response = await client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )

        msg = response.choices[0].message
        finish_reason = getattr(response.choices[0], "finish_reason", None)
        logger.debug("round=%s finish_reason=%s", round_index, finish_reason)

        # 没有工具调用 -> 这就是最终回答
        if not msg.tool_calls:
            return msg.content or ""

        # 有工具调用 -> 把 assistant 消息与逐条工具结果都追加进上下文
        tool_names = [tc.function.name for tc in msg.tool_calls]
        logger.debug("round=%s tool_calls=%s", round_index, tool_names)

        messages.append(_assistant_tool_call_message(msg))
        for tc in msg.tool_calls:
            result_str = _execute_tool(tc.function.name, tc.function.arguments)
            logger.debug(
                "round=%s tool=%s result_len=%s",
                round_index,
                tc.function.name,
                len(result_str),
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                }
            )

    # 达到最大轮数仍未得到最终回答：做一次禁止工具调用的强制文本合成。
    # 让模型基于前面已经查到的工具结果直接回答，避免开放式问题（如推荐）卡死在循环里。
    logger.warning(
        "达到最大工具调用轮数 %s，尝试禁止工具调用的强制文本合成", MAX_TOOL_ROUNDS
    )
    messages.append(
        {
            "role": "user",
            "content": "请基于以上工具查询到的真实资料，直接给出最终回答，不要再调用任何工具。",
        }
    )
    try:
        response = await client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="none",
        )
        final_msg = response.choices[0].message
        if final_msg.content:
            return final_msg.content
    except Exception:
        logger.exception("强制文本合成调用失败")

    return _MAX_ROUNDS_MESSAGE
