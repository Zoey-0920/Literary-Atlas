"""作品（books）与地点（places）HTTP 接口测试。

使用临时 SQLite 数据库隔离，导入种子数据后验证列表、分页、关键词搜索、
详情、修改、地点关联作品等接口。

运行方式（在 backend/ 目录下）：
    .venv\\Scripts\\python.exe test_api.py
"""

import tempfile
from pathlib import Path

# 隔离：临时数据库（必须在导入 main 前重写 DB_PATH）
import database
from database import get_db_connection, init_db

_tmpdir = tempfile.mkdtemp()
database.DB_PATH = Path(_tmpdir) / "test.db"
init_db()

from seed import seed_data

_conn = get_db_connection()
try:
    seed_data(_conn)
finally:
    _conn.close()

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

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


print("=== 作品与地点 HTTP 接口测试 ===\n")

# ---------- Books ----------
resp = client.get("/api/books")
check("作品列表返回 200", resp.status_code == 200)
check("作品列表总数 6", resp.json().get("total") == 6)

resp = client.get("/api/books", params={"limit": 2})
check("分页 limit=2 返回 2 条", len(resp.json().get("items")) == 2)
check("分页 total 仍为 6", resp.json().get("total") == 6)

resp = client.get("/api/books", params={"keyword": "百年"})
check("关键词搜索 '百年' 返回 1 条", resp.json().get("total") == 1)
check("关键词搜索命中《百年孤独》", resp.json()["items"][0]["title"] == "百年孤独")

resp = client.get("/api/books", params={"keyword": "1984"})
check("关键词搜索 '1984' 返回 1 条", resp.json().get("total") == 1)

resp = client.get("/api/books", params={"keyword": "不存在的书"})
check("关键词无结果返回 0", resp.json().get("total") == 0)

book_id = client.get("/api/books", params={"keyword": "百年"}).json()["items"][0]["id"]
resp = client.get(f"/api/books/{book_id}")
check("作品详情返回 200", resp.status_code == 200)
check("作品详情标题正确", resp.json().get("title") == "百年孤独")

resp = client.get("/api/books/99999")
check("不存在的作品返回 404", resp.status_code == 404)

resp = client.patch(f"/api/books/{book_id}", json={"description": "魔幻现实主义经典之作"})
check("修改作品返回 200", resp.status_code == 200)
check("修改作品描述生效", resp.json().get("description") == "魔幻现实主义经典之作")

resp = client.patch("/api/books/99999", json={"description": "x"})
check("修改不存在作品返回 404", resp.status_code == 404)

# ---------- Places ----------
resp = client.get("/api/places")
check("地点列表返回 200", resp.status_code == 200)
check("地点列表总数 16", resp.json().get("total") == 16)

resp = client.get("/api/places", params={"keyword": "马孔多"})
check("地点关键词搜索返回 1 条", resp.json().get("total") == 1)
macondo_id = resp.json()["items"][0]["id"]
check("马孔多为虚构地点", resp.json()["items"][0]["is_fictional"] == 1)

resp = client.get("/api/places/99999")
check("不存在的地点返回 404", resp.status_code == 404)

resp = client.get(f"/api/places/{macondo_id}/literature")
check("地点关联作品返回 200", resp.status_code == 200)
check("马孔多关联 1 部作品", resp.json().get("total") == 1)
check("马孔多关联《百年孤独》", resp.json()["items"][0]["book"]["title"] == "百年孤独")

# 俄罗斯关联《战争与和平》（setting）
russia = client.get("/api/places", params={"keyword": "俄罗斯"}).json()["items"][0]["id"]
resp = client.get(f"/api/places/{russia}/literature")
check("俄罗斯关联《战争与和平》",
      any(it["book"]["title"] == "战争与和平" for it in resp.json()["items"]))

resp = client.get("/api/places/99999/literature")
check("不存在地点的关联作品返回 404", resp.status_code == 404)

print(f"\n=== 测试汇总 ===\n总数: {PASS + FAIL}  通过: {PASS}  失败: {FAIL}")
if FAIL:
    raise SystemExit(1)
