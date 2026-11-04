"""AI Agent HTTP 接口测试。

使用 Mock 替换 chat_with_agent，不调用真实企业模型 API。
使用临时 SQLite 数据库隔离，不污染正式数据库。

运行方式（在 backend/ 目录下）：
    .venv\\Scripts\\python.exe test_agent_api.py
"""

import tempfile
from pathlib import Path

# 隔离：临时数据库
import database
from database import init_db

_tmpdir = tempfile.mkdtemp()
database.DB_PATH = Path(_tmpdir) / "test.db"
init_db()

from fastapi.testclient import TestClient
from openai import APIError

import routers.agent as agent_router
from main import app

client = TestClient(app)

# 保存原始函数，测试中替换为 Mock
_original_chat = agent_router.chat_with_agent

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


def set_chat(fn):
    """替换路由模块中引用的 chat_with_agent 为 Mock 函数。"""
    agent_router.chat_with_agent = fn


print("=== AI Agent HTTP 接口测试 ===\n")

# 1-3. 正常请求
async def fake_ok(message):
    return "这是回答"


set_chat(fake_ok)
resp = client.post("/api/agent/chat", json={"message": "帮我介绍一下《百年孤独》"})
check("正常请求返回 200", resp.status_code == 200)
data = resp.json()
check("成功响应包含 reply", "reply" in data and data["reply"] == "这是回答")
check("成功响应不包含 answer", "answer" not in data)

# 4. 空字符串
resp = client.post("/api/agent/chat", json={"message": ""})
check("空字符串返回 422", resp.status_code == 422)

# 5. 只有空格
resp = client.post("/api/agent/chat", json={"message": "   "})
check("只有空格返回 422", resp.status_code == 422)

# 6. 缺少 message
resp = client.post("/api/agent/chat", json={})
check("缺少 message 返回 422", resp.status_code == 422)

# 7. 模型服务异常 -> 502
async def fake_api_error(message):
    raise APIError("upstream failed", None, body=None)


set_chat(fake_api_error)
resp = client.post("/api/agent/chat", json={"message": "hi"})
check("模型服务异常返回 502", resp.status_code == 502)
check("502 响应为 detail 格式", resp.json().get("detail") is not None)

# 8. 其他未预期异常 -> 500，且不泄露细节
async def fake_internal_error(message):
    raise RuntimeError("secret-internal-detail")


set_chat(fake_internal_error)
resp = client.post("/api/agent/chat", json={"message": "hi"})
check("其他异常返回 500", resp.status_code == 500)
check("500 响应不泄露内部细节",
      "secret-internal-detail" not in resp.text and "RuntimeError" not in resp.text)

# 9. 原有 /health 正常
resp = client.get("/health")
check("/health 正常", resp.status_code == 200 and resp.json().get("status") == "healthy")

# 10. 原有作品和地点接口未受影响
resp = client.get("/api/books")
check("/api/books 正常", resp.status_code == 200)
resp = client.get("/api/places")
check("/api/places 正常", resp.status_code == 200)

# 恢复原始函数（避免影响后续可能的导入）
agent_router.chat_with_agent = _original_chat

print(f"\n=== 测试汇总 ===\n总数: {PASS + FAIL}  通过: {PASS}  失败: {FAIL}")
if FAIL:
    raise SystemExit(1)
