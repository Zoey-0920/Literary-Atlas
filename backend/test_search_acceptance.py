# -*- coding: utf-8 -*-
"""八项验收测试：调用运行中的后端服务验证统一模糊检索。"""
import io
import json
import sys
import urllib.parse
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = "http://127.0.0.1:8001"


def api(path, params=None):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read().decode("utf-8"))


def search(q):
    return api("/api/search", {"q": q})


def summarize(r):
    out = []
    for w in r["groups"]["works"]:
        out.append("作品:%s(%s)" % (w["title"], w["match_type"]))
    for a in r["groups"]["authors"]:
        out.append("作者:%s(%s)" % (a["name"], a["match_type"]))
    for p in r["groups"]["places"]:
        out.append("地点:%s(%s)" % (p["name"], p["match_type"]))
    for c in r["groups"]["countries"]:
        out.append("国家:%s(%d部)" % (c["name"], c["work_count"]))
    for g in r["groups"]["genres"]:
        out.append("类型:%s(%d部,%s)" % (g["name"], g["work_count"], g["match_type"]))
    return out


passed, failed = 0, 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("[PASS] %s %s" % (name, detail))
    else:
        failed += 1
        print("[FAIL] %s %s" % (name, detail))


print("=== 1. 输入完整书名 ===")
r = search("百年孤独")
check("1 完整书名", r["total"] >= 1 and r["groups"]["works"][0]["title"] == "百年孤独"
      and r["groups"]["works"][0]["match_type"] == "exact", summarize(r))

print("=== 2. 输入部分书名 ===")
r = search("百年")
check("2 部分书名", any(w["title"] == "百年孤独" for w in r["groups"]["works"]), summarize(r))
r2 = search("百年 孤独")  # 中文空格分隔也能精确命中
check("2b 空格分隔书名", r2["groups"]["works"] and r2["groups"]["works"][0]["match_type"] == "exact",
      summarize(r2))

print("=== 3. 输入部分作者名 ===")
r = search("马尔克斯")
check("3 部分作者名(搜到作品)", any(w["title"] == "百年孤独" for w in r["groups"]["works"]), summarize(r))
r = search("加西亚")
check("3b 作者片段", any(a["name"] == "加夫列尔·加西亚·马尔克斯" for a in r["groups"]["authors"]), summarize(r))

print("=== 4. 输入国家或城市 ===")
r = search("哥伦比亚")
check("4 国家", any(c["name"] == "哥伦比亚" for c in r["groups"]["countries"])
      and any(a["name"] == "加夫列尔·加西亚·马尔克斯" for a in r["groups"]["authors"]), summarize(r))
r = search("巴黎")
check("4b 城市", any(p["name"] == "巴黎" for p in r["groups"]["places"])
      and any(w["title"] == "巴黎圣母院" for w in r["groups"]["works"]), summarize(r))

print("=== 5. 英文关键词 + 大小写 ===")
r1 = search("old man")
r2 = search("OLD MAN AND THE SEA")
ok5 = any(w["title"] == "老人与海" for w in r1["groups"]["works"]) and \
      any(w["title"] == "老人与海" for w in r2["groups"]["works"])
check("5 英文不区分大小写", ok5, summarize(r1))

print("=== 6. 带少量错误的关键词 ===")
r = search("百念孤独")
check("6 中文错字容错", r["fuzzy_fallback"] and
      any(w["title"] == "百年孤独" and w["match_type"] == "fuzzy" for w in r["groups"]["works"]), summarize(r))
r = search("托尔斯基")
check("6b 作者名错字", any(a["name"] == "列夫·托尔斯泰" for a in r["groups"]["authors"]), summarize(r))
r = search("oldman and the sa")
check("6c 英文连写+错字", any(w["title"] == "老人与海" for w in r["groups"]["works"]), summarize(r))

print("=== 7. 不存在的关键词 ===")
r = search("xyz不存在的内容")
check("7 空结果", r["total"] == 0 and all(len(v) == 0 for v in r["groups"].values()))
r = search("不存在的书名查询")
check("7b 中文不存在的书", r["total"] == 0, summarize(r))

print("=== 7c. 空白处理 ===")
r = search("   multiple   spaces   ")
check("7c 连续空格合并", r["query"] == "multiple spaces", repr(r["query"]))

print("=== 8. 现有接口行为不受影响 ===")
b = api("/api/books", {"keyword": "百年"})
check("8 books LIKE 兼容", any(x["title"] == "百年孤独" for x in b["items"]))
p = api("/api/places", {"keyword": "伦"})
check("8b places LIKE 兼容", p["total"] >= 1)
a = api("/api/authors", {"keyword": "马尔克斯"})
check("8c authors LIKE 兼容", a["total"] >= 1)

print()
print("汇总: 通过 %d, 失败 %d" % (passed, failed))
sys.exit(1 if failed else 0)
