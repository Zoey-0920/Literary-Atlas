"""DeepSeek 大模型客户端。

使用 OpenAI Python SDK 的 AsyncOpenAI 连接 DeepSeek，
通过 python-dotenv 从 backend/.env 读取配置。

注意：本模块绝不把 API Key 打印或返回给调用者。
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

# backend/.env 位于本文件上一级目录（即 backend/）。
# 使用 __file__ 定位，确保无论从哪个工作目录运行都能正确找到。
_BACKEND_DIR = Path(__file__).resolve().parent.parent

# 加载 backend/.env；若文件不存在则静默跳过，沿用进程已有环境变量。
load_dotenv(_BACKEND_DIR / ".env")

# 从环境变量读取配置，model / base_url 提供默认值
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


def _build_client() -> AsyncOpenAI:
    """构建 AsyncOpenAI 客户端；缺少 API Key 时给出明确错误提示。"""
    if not DEEPSEEK_API_KEY:
        raise ValueError(
            "缺少 DEEPSEEK_API_KEY，请在 backend/.env 中配置后重试"
        )
    return AsyncOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )


async def chat(prompt: str) -> str:
    """向 DeepSeek 发送一条简单消息，返回模型文本回复。

    Args:
        prompt: 发送给模型的用户消息内容。

    Returns:
        模型返回的文本内容（去空）。
    """
    client = _build_client()
    response = await client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    # 只返回文本内容，绝不返回任何与密钥相关的信息
    return response.choices[0].message.content or ""
