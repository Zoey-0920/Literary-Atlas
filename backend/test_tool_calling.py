"""DeepSeek Tool Calling（Function Calling）能力测试。

验证当前模型是否支持 OpenAI 兼容接口的 tools 参数与 tool_choice="auto"。

本脚本只验证模型能否发出工具调用请求：
- 不真正执行工具
- 不连接数据库
- 不打印 API Key
- 不修改现有 .env / main.py / database.py / routers/

运行方式（在 backend/ 目录下）：
    .venv\\Scripts\\python.exe test_tool_calling.py
"""

import asyncio
import json

from agent.llm_client import DEEPSEEK_MODEL, _build_client

# 虚拟工具定义：仅用于观察模型是否返回 tool_calls
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_books",
            "description": "根据书名搜索文学作品。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "要搜索的书名关键词",
                    },
                },
                "required": ["keyword"],
            },
        },
    }
]


async def main() -> None:
    client = _build_client()

    response = await client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {
                "role": "user",
                "content": "帮我查一下《百年孤独》",
            },
        ],
        tools=TOOLS,
        tool_choice="auto",
    )

    choice = response.choices[0]
    message = choice.message
    finish_reason = choice.finish_reason

    print("=== Tool Calling 测试结果 ===")
    print(f"finish_reason: {finish_reason}")
    print(f"message.tool_calls 是否存在: {message.tool_calls is not None}")

    if message.tool_calls:
        for tc in message.tool_calls:
            print(f"工具名称: {tc.function.name}")
            print(f"工具参数原文: {tc.function.arguments}")
            try:
                args = json.loads(tc.function.arguments)
                print(f"提取到的 keyword 参数: {args.get('keyword')}")
            except json.JSONDecodeError as exc:
                print(f"参数 JSON 解析失败: {exc}")
    else:
        print("未返回 tool_calls，模型普通回复内容如下：")
        print(message.content)


if __name__ == "__main__":
    asyncio.run(main())
