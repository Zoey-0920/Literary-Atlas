"""DeepSeek 连通性测试。

向 DeepSeek 发送一条消息，验证 API Key 配置与网络连通性。

运行方式（在 backend/ 目录下）：
    .venv\\Scripts\\python.exe test_deepseek.py

注意：本脚本不打印 API Key，不修改数据库，不修改现有接口。
"""

import asyncio

from agent.llm_client import chat


async def main() -> None:
    prompt = "你好，请用一句话介绍你自己。"
    reply = await chat(prompt)
    print("DeepSeek 回复：")
    print(reply)


if __name__ == "__main__":
    asyncio.run(main())
