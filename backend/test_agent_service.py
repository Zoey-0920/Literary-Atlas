"""Agent 核心执行逻辑测试（使用 Mock 模型，不调用真实 API）。

覆盖：无工具直接回答、单工具执行、连续多工具、未知工具、JSON 参数错误、
最大轮数停止、工具结果回传、以及整个过程不修改数据库。

运行方式（在 backend/ 目录下）：
    .venv\\Scripts\\python.exe test_agent_service.py
"""

import asyncio
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

# 隔离：使用临时数据库，避免污染正式库
import database
from database import get_db_connection, init_db

_tmpdir = tempfile.mkdtemp()
database.DB_PATH = Path(_tmpdir) / "test.db"
init_db()

from agent.agent_service import MAX_TOOL_ROUNDS, chat_with_agent

# ---------- 测试统计 ----------

PASS = 0
FAIL = 0


def check(name: str, cond: bool):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name}")


# ---------- 准备数据（临时库） ----------

def setup_data():
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO books (title) VALUES (?)", ("百年孤独",))
        conn.commit()
    finally:
        conn.close()


def table_counts() -> dict:
    tables = ["books", "authors", "places", "genres",
              "book_authors", "book_places", "book_genres", "author_places"]
    conn = get_db_connection()
    try:
        counts = {t: conn.execute(f"SELECT COUNT(*) AS c FROM {t}").fetchone()["c"]
                  for t in tables}
    finally:
        conn.close()
    return counts


setup_data()

# ---------- Mock 大模型 ----------

class FakeToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.function = SimpleNamespace(name=name, arguments=arguments)


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class FakeChoice:
    def __init__(self, message):
        self.message = message
        self.finish_reason = "tool_calls" if message.tool_calls else "stop"


class FakeResponse:
    def __init__(self, message):
        self.choices = [FakeChoice(message)]


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []  # 记录每次 create 的 kwargs（含 messages）
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("Mock 响应已耗尽，疑似循环未停止")
        return FakeResponse(self.responses.pop(0))


def tool_msg_of_call(call, index=0):
    """取第 index 次模型调用时上下文里的 tool 消息。"""
    messages = call["messages"]
    tools = [m for m in messages if m["role"] == "tool"]
    return tools[index] if tools else None


# ---------- 测试 ----------

async def run_tests():
    print("=== Agent 核心执行逻辑测试 ===\n")

    # 1. 不需要工具时直接返回模型文本
    client = FakeClient([FakeMessage(content="你好，我可以帮你查询文学作品。")])
    answer = await chat_with_agent("你好", client=client)
    check("不需要工具：直接返回模型文本",
          answer == "你好，我可以帮你查询文学作品。" and len(client.calls) == 1)

    # 2. 调用 search_books，后端成功执行
    client = FakeClient([
        FakeMessage(tool_calls=[
            FakeToolCall("c1", "search_books", json.dumps({"keyword": "百年"}))
        ]),
        FakeMessage(content="已为你找到《百年孤独》。"),
    ])
    answer = await chat_with_agent("帮我查百年孤独", client=client)
    check("调用 search_books：返回最终答案", answer == "已为你找到《百年孤独》。")
    check("调用 search_books：共两轮模型调用", len(client.calls) == 2)

    # 3. 连续调用两个工具（search_books -> get_book_detail）
    client = FakeClient([
        FakeMessage(tool_calls=[
            FakeToolCall("c1", "search_books", json.dumps({"keyword": "百年"}))
        ]),
        FakeMessage(tool_calls=[
            FakeToolCall("c2", "get_book_detail", json.dumps({"book_id": 1}))
        ]),
        FakeMessage(content="这是《百年孤独》的详细介绍。"),
    ])
    answer = await chat_with_agent("帮我详细介绍百年孤独", client=client)
    check("连续两个工具：返回最终答案", answer == "这是《百年孤独》的详细介绍。")
    check("连续两个工具：共三轮模型调用", len(client.calls) == 3)

    # 4. 未知工具：不执行任意函数，安全拒绝
    client = FakeClient([
        FakeMessage(tool_calls=[
            FakeToolCall("c9", "dangerous_tool", json.dumps({}))
        ]),
        FakeMessage(content="抱歉，我无法执行该操作。"),
    ])
    answer = await chat_with_agent("执行危险操作", client=client)
    tm = tool_msg_of_call(client.calls[1])
    check("未知工具：不崩溃并返回最终答案", answer == "抱歉，我无法执行该操作。")
    check("未知工具：回传结果含未知工具提示",
          tm is not None and "未知工具" in tm["content"])

    # 5. 工具参数 JSON 格式错误：安全处理
    client = FakeClient([
        FakeMessage(tool_calls=[
            FakeToolCall("c1", "search_books", "这不是合法JSON")
        ]),
        FakeMessage(content="参数格式有误，请重新说明。"),
    ])
    answer = await chat_with_agent("查询", client=client)
    tm = tool_msg_of_call(client.calls[1])
    check("JSON 参数错误：不崩溃并返回最终答案", answer == "参数格式有误，请重新说明。")
    check("JSON 参数错误：回传结果含解析失败提示",
          tm is not None and "JSON 解析失败" in tm["content"])

    # 6. 达到最大工具调用轮数后强制文本合成：最终响应仍无内容时回退停止提示
    endless_responses = [
        FakeMessage(tool_calls=[
            FakeToolCall(f"c{i}", "search_books", json.dumps({"keyword": "x"}))
        ])
        for i in range(MAX_TOOL_ROUNDS + 5)
    ]
    client = FakeClient(endless_responses)
    answer = await chat_with_agent("循环测试", client=client)
    check("最大轮数：最终无内容时返回停止提示", "最大工具调用轮数" in answer)
    check("最大轮数：调用次数 = 上限 + 1 次强制合成", len(client.calls) == MAX_TOOL_ROUNDS + 1)

    # 6b. 达到最大工具调用轮数后强制文本合成：模型给出最终回答
    synth_responses = [
        FakeMessage(tool_calls=[
            FakeToolCall(f"c{i}", "search_books", json.dumps({"keyword": "x"}))
        ])
        for i in range(MAX_TOOL_ROUNDS)
    ] + [FakeMessage(content="根据查询结果，为你推荐这些作品。")]
    client = FakeClient(synth_responses)
    answer = await chat_with_agent("推荐几部作品", client=client)
    check("强制合成：返回最终回答", answer == "根据查询结果，为你推荐这些作品。")
    check("强制合成：调用次数 = 上限 + 1", len(client.calls) == MAX_TOOL_ROUNDS + 1)

    # 7. 工具执行结果正确传回模型（检查 tool 消息内容与 tool_call_id）
    client = FakeClient([
        FakeMessage(tool_calls=[
            FakeToolCall("c1", "search_books", json.dumps({"keyword": "百年"}))
        ]),
        FakeMessage(content="查询完成。"),
    ])
    await chat_with_agent("查询百年孤独", client=client)
    tm = tool_msg_of_call(client.calls[1])
    check("结果回传：存在 tool 消息", tm is not None)
    check("结果回传：tool_call_id 正确",
          tm is not None and tm["tool_call_id"] == "c1")
    check("结果回传：内容含真实查询结果",
          tm is not None and "百年孤独" in tm["content"])

    # 8. 整个过程不修改数据库
    before = table_counts()
    client = FakeClient([
        FakeMessage(tool_calls=[
            FakeToolCall("c1", "search_books", json.dumps({"keyword": "百年"}))
        ]),
        FakeMessage(content="完成"),
    ])
    await chat_with_agent("查询", client=client)
    after = table_counts()
    check("不修改数据库：各表行数保持不变", before == after)

    print(f"\n=== 测试汇总 ===\n总数: {PASS + FAIL}  通过: {PASS}  失败: {FAIL}")
    if FAIL:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(run_tests())
