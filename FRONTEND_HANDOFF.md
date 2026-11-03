# Literary Atlas 后端接口与数据结构交接文档

> 用途：前后端联调交接资料
> 生成日期：2026-11-03
> 依据：项目实际代码（backend/）、SQLite 实际数据库（backend/literary_atlas.db）、运行中的真实 HTTP 服务
> 说明：本文档仅做检查与整理，未修改任何代码、数据库、接口或既有文档。

---

## 0. 交接文档定位说明（重要）

- 本项目最新版 API 文档实际位于项目根目录的 `docs/API.md`，**并非** `backend/docs/API.md`。
- `backend/docs/` 目录此前不存在，本文档（`backend/docs/FRONTEND_HANDOFF.md`）为首次创建。
- 真实联调服务本次运行在 `http://127.0.0.1:8001`（`docs/API.md` 中示例写的是 `8000`，见下方差异说明）。
- Swagger 交互式文档：`http://127.0.0.1:8001/docs`。

---

## 1. 现有 API 文档与代码一致性核对

已读取 `docs/API.md` 全文，并与代码逐条比对。接口定义（方法、路径、请求/响应字段、状态码语义）与代码**一致**，结论如下：

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 系统 | GET | `/` | 欢迎信息 |
| 系统 | GET | `/health` | 健康检查 |
| 系统 | GET | `/docs` | Swagger 文档 |
| 作品 | POST | `/api/books` | 新增作品（201） |
| 作品 | GET | `/api/books` | 作品列表（分页 + keyword） |
| 作品 | GET | `/api/books/{book_id}` | 作品详情 |
| 作品 | PATCH | `/api/books/{book_id}` | 部分修改作品 |
| 地点 | GET | `/api/places` | 地点列表（分页 + keyword） |
| 地点 | GET | `/api/places/{place_id}` | 地点详情 |
| 地点 | GET | `/api/places/{place_id}/literature` | 地点关联作品 |
| 阅读 | POST | `/api/reading` | 加书到书架（201） |
| 阅读 | GET | `/api/reading` | 查看书架（可按 status 筛选） |
| 阅读 | PATCH | `/api/reading/{record_id}` | 修改书架记录 |
| 阅读 | DELETE | `/api/reading/{record_id}` | 删除书架记录（204） |
| Agent | POST | `/api/agent/chat` | AI 聊天 |

### 文档与代码的差异（仅列出，未修改）

以下均属**示例数据 / 环境描述层面**的差异，非接口逻辑差异：

1. **服务地址**：`docs/API.md` 头部及示例写的是 `http://127.0.0.1:8000`，实际本次联调服务运行在 `http://127.0.0.1:8001`。
2. **地点坐标示例**：文档「获取地点列表」示例中的"伦敦"带经纬度 `51.5 / -0.12`。但实际数据库中 **16 个地点的 `latitude`、`longitude` 全部为 `null`**（第一版不编造坐标）。
3. **作品示例 id**：文档示例用 `id: 1`，实际数据库作品 id 从 `2` 开始，**不存在 id=1 的作品**。
4. **文学作品示例**：文档「地点关联作品」示例用 `place_id: 1` 关联"伦敦游记"。实际 `place_id: 1` 是"马孔多"（虚构），其关联作品是"百年孤独"；"伦敦游记"并不存在于库中。

---

## 2. 数据库完整结构（9 张表，PRAGMA 实测）

以下结构与约束均通过实际数据库执行 `PRAGMA table_info`、`PRAGMA foreign_key_list`、`sqlite_master` 获取，非凭记忆推断。

> 通用约定：所有表 `created_at TEXT NOT NULL DEFAULT (datetime('now'))`；`updated_at TEXT`（可空）。

### 2.1 books（作品）

| 字段 | 类型 | NULL | 默认值 | 约束 |
|------|------|------|--------|------|
| id | INTEGER | 否(PK自增) | - | PRIMARY KEY AUTOINCREMENT |
| title | TEXT | 否 | - | NOT NULL |
| original_title | TEXT | 是 | NULL | - |
| language | TEXT | 是 | NULL | - |
| publication_year | INTEGER | 是 | NULL | - |
| description | TEXT | 是 | NULL | - |
| source | TEXT | 是 | NULL | - |
| created_at | TEXT | 否 | datetime('now') | NOT NULL |
| updated_at | TEXT | 是 | NULL | - |

无外键、无 UNIQUE、无 CHECK。

### 2.2 authors（作者）

| 字段 | 类型 | NULL | 默认值 | 约束 |
|------|------|------|--------|------|
| id | INTEGER | 否(PK自增) | - | PRIMARY KEY AUTOINCREMENT |
| name | TEXT | 否 | - | NOT NULL |
| birth_year | INTEGER | 是 | NULL | - |
| death_year | INTEGER | 是 | NULL | - |
| nationality | TEXT | 是 | NULL | - |
| bio | TEXT | 是 | NULL | - |
| created_at | TEXT | 否 | datetime('now') | NOT NULL |
| updated_at | TEXT | 是 | NULL | - |

无外键、无 UNIQUE、无 CHECK。

### 2.3 places（地点）

| 字段 | 类型 | NULL | 默认值 | 约束 |
|------|------|------|--------|------|
| id | INTEGER | 否(PK自增) | - | PRIMARY KEY AUTOINCREMENT |
| name | TEXT | 否 | - | NOT NULL |
| place_type | TEXT | 否 | - | NOT NULL，CHECK ∈ (country, city, region, fictional) |
| is_fictional | INTEGER | 否 | 0 | NOT NULL，CHECK ∈ (0, 1) |
| latitude | REAL | 是 | NULL | CHECK 范围 -90~90 |
| longitude | REAL | 是 | NULL | CHECK 范围 -180~180 |
| country | TEXT | 是 | NULL | - |
| region | TEXT | 是 | NULL | - |
| parent_place_id | INTEGER | 是 | NULL | 外键 → places(id) ON DELETE SET NULL |
| description | TEXT | 是 | NULL | - |
| created_at | TEXT | 否 | datetime('now') | NOT NULL |
| updated_at | TEXT | 是 | NULL | - |

CHECK 约束（完整）：

- `is_fictional IN (0, 1)`
- `place_type IN ('country', 'city', 'region', 'fictional')`
- `latitude IS NULL OR (latitude BETWEEN -90 AND 90)`
- `longitude IS NULL OR (longitude BETWEEN -180 AND 180)`
- 经纬度必须**同时为空或同时填写**：`(latitude IS NULL AND longitude IS NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL)`
- 虚构地点不能填坐标：`NOT (is_fictional = 1 AND (latitude IS NOT NULL OR longitude IS NOT NULL))`
- `place_type` 与 `is_fictional` 一致：`(place_type='fictional' AND is_fictional=1) OR (place_type<>'fictional' AND is_fictional=0)`

### 2.4 genres（文学流派）

| 字段 | 类型 | NULL | 默认值 | 约束 |
|------|------|------|--------|------|
| id | INTEGER | 否(PK自增) | - | PRIMARY KEY AUTOINCREMENT |
| name | TEXT | 否 | - | NOT NULL，**UNIQUE** |
| description | TEXT | 是 | NULL | - |
| created_at | TEXT | 否 | datetime('now') | NOT NULL |
| updated_at | TEXT | 是 | NULL | - |

### 2.5 book_authors（作品 ↔ 作者）

| 字段 | 类型 | NULL | 默认值 | 约束 |
|------|------|------|--------|------|
| book_id | INTEGER | 否(PK) | - | 复合主键；外键 → books(id) ON DELETE CASCADE |
| author_id | INTEGER | 否(PK) | - | 复合主键；外键 → authors(id) ON DELETE CASCADE |
| role | TEXT | 是 | NULL | CHECK ∈ (author, translator, editor) |
| created_at | TEXT | 否 | datetime('now') | NOT NULL |

主键：`PRIMARY KEY (book_id, author_id)`。role 可空（空即视为作者身份）。

### 2.6 book_places（作品 ↔ 地点，核心关联表）

| 字段 | 类型 | NULL | 默认值 | 约束 |
|------|------|------|--------|------|
| id | INTEGER | 否(PK自增) | - | PRIMARY KEY AUTOINCREMENT |
| book_id | INTEGER | 否 | - | 外键 → books(id) ON DELETE CASCADE |
| place_id | INTEGER | 否 | - | 外键 → places(id) ON DELETE CASCADE |
| relation_type | TEXT | 否 | - | NOT NULL，CHECK ∈ (setting, depiction) |
| source_name | TEXT | 是 | NULL | - |
| source_url | TEXT | 是 | NULL | - |
| note | TEXT | 是 | NULL | - |
| verification_status | TEXT | 否 | 'unverified' | CHECK ∈ (verified, unverified, disputed) |
| created_at | TEXT | 否 | datetime('now') | NOT NULL |
| updated_at | TEXT | 是 | NULL | - |

UNIQUE：`(book_id, place_id, relation_type)`。

### 2.7 book_genres（作品 ↔ 流派）

| 字段 | 类型 | NULL | 默认值 | 约束 |
|------|------|------|--------|------|
| book_id | INTEGER | 否(PK) | - | 复合主键；外键 → books(id) ON DELETE CASCADE |
| genre_id | INTEGER | 否(PK) | - | 复合主键；外键 → genres(id) ON DELETE CASCADE |
| created_at | TEXT | 否 | datetime('now') | NOT NULL |

主键：`PRIMARY KEY (book_id, genre_id)`。

### 2.8 author_places（作者 ↔ 地点）

| 字段 | 类型 | NULL | 默认值 | 约束 |
|------|------|------|--------|------|
| id | INTEGER | 否(PK自增) | - | PRIMARY KEY AUTOINCREMENT |
| author_id | INTEGER | 否 | - | 外键 → authors(id) ON DELETE CASCADE |
| place_id | INTEGER | 否 | - | 外键 → places(id) ON DELETE CASCADE |
| relation_type | TEXT | 否 | - | NOT NULL，CHECK ∈ (birthplace, residence, creation) |
| source_name | TEXT | 是 | NULL | - |
| source_url | TEXT | 是 | NULL | - |
| note | TEXT | 是 | NULL | - |
| verification_status | TEXT | 否 | 'unverified' | CHECK ∈ (verified, unverified, disputed) |
| start_year | INTEGER | 是 | NULL | - |
| end_year | INTEGER | 是 | NULL | - |
| created_at | TEXT | 否 | datetime('now') | NOT NULL |
| updated_at | TEXT | 是 | NULL | - |

UNIQUE：`(author_id, place_id, relation_type)`。

### 2.9 reading_records（个人阅读记录）

> ⚠️ **代码与实际库差异点**：`database.py` 建表语句里定义了 `CHECK (progress IS NULL OR (progress BETWEEN 0 AND 100))`，但当前实际数据库中的 `reading_records` 表**并不包含 progress 的 CHECK 约束**。原因是 `progress` 列是通过 `_migrate()` 的 `ALTER TABLE ADD COLUMN` 后补的（SQLite 的 ALTER ADD COLUMN 无法附加 CHECK）。此外实际库中 `progress` 位于表尾（第 11 列），建表语句中则紧跟 rating。前端校验 progress（0~100）应自行保证，不能依赖数据库约束。

| 字段 | 类型 | NULL | 默认值 | 约束 |
|------|------|------|--------|------|
| id | INTEGER | 否(PK自增) | - | PRIMARY KEY AUTOINCREMENT |
| user_id | TEXT | 否 | - | NOT NULL |
| book_id | INTEGER | 否 | - | 外键 → books(id) ON DELETE CASCADE |
| status | TEXT | 否 | - | NOT NULL，CHECK ∈ (want_to_read, reading, finished) |
| rating | INTEGER | 是 | NULL | CHECK NULL 或 BETWEEN 1 AND 5 |
| started_at | TEXT | 是 | NULL | - |
| finished_at | TEXT | 是 | NULL | - |
| note | TEXT | 是 | NULL | - |
| created_at | TEXT | 否 | datetime('now') | NOT NULL |
| updated_at | TEXT | 是 | NULL | - |
| progress | INTEGER | 是 | NULL | 见上方⚠️说明，实际库无 CHECK |

UNIQUE：`(user_id, book_id)`（同一用户对同一作品只能有一条记录）。

---

## 3. 真实 HTTP 接口响应示例

以下均为本次对 `http://127.0.0.1:8001` 的真实 HTTP 请求结果。

### 3.1 GET `/api/books`

- 方法：GET
- 路径：`/api/books`
- 参数：无（可选 query：`limit`、`offset`、`keyword`）
- 状态码：`200`

```json
{
  "total": 6,
  "items": [
    {"id": 2, "title": "百年孤独", "original_title": "Cien años de soledad", "language": "西班牙语", "publication_year": 1967, "description": "加西亚·马尔克斯代表作，魔幻现实主义经典。", "source": null, "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 3, "title": "战争与和平", "original_title": "Война и мир", "language": "俄语", "publication_year": 1869, "description": "托尔斯泰长篇小说，以拿破仑战争为背景。", "source": null, "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 4, "title": "1984", "original_title": "Nineteen Eighty-Four", "language": "英语", "publication_year": 1949, "description": "乔治·奥威尔的反乌托邦小说。", "source": null, "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 5, "title": "神曲", "original_title": "La Divina Commedia", "language": "意大利语", "publication_year": 1472, "description": "但丁的叙事长诗，分地狱、炼狱、天堂三篇。", "source": null, "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 6, "title": "红楼梦", "original_title": null, "language": "中文", "publication_year": 1791, "description": "曹雪芹章回体小说，中国古典文学高峰。", "source": null, "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 7, "title": "老人与海", "original_title": "The Old Man and the Sea", "language": "英语", "publication_year": 1952, "description": "海明威的中篇小说。", "source": null, "created_at": "2026-11-03 07:30:45", "updated_at": null}
  ]
}
```

### 3.2 GET `/api/books/2`

- 方法：GET
- 路径：`/api/books/2`
- 参数：无
- 状态码：`200`

```json
{
  "id": 2,
  "title": "百年孤独",
  "original_title": "Cien años de soledad",
  "language": "西班牙语",
  "publication_year": 1967,
  "description": "加西亚·马尔克斯代表作，魔幻现实主义经典。",
  "source": null,
  "created_at": "2026-11-03 07:30:45",
  "updated_at": null
}
```

### 3.3 GET `/api/places`

- 方法：GET
- 路径：`/api/places`
- 参数：无
- 状态码：`200`

```json
{
  "total": 16,
  "items": [
    {"id": 1, "name": "马孔多", "place_type": "fictional", "is_fictional": 1, "latitude": null, "longitude": null, "country": null, "region": null, "parent_place_id": null, "description": "《百年孤独》虚构小镇。", "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 2, "name": "大洋国", "place_type": "fictional", "is_fictional": 1, "latitude": null, "longitude": null, "country": null, "region": null, "parent_place_id": null, "description": "《1984》虚构国家。", "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 3, "name": "地狱", "place_type": "fictional", "is_fictional": 1, "latitude": null, "longitude": null, "country": null, "region": null, "parent_place_id": null, "description": "《神曲》叙事空间。", "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 4, "name": "炼狱", "place_type": "fictional", "is_fictional": 1, "latitude": null, "longitude": null, "country": null, "region": null, "parent_place_id": null, "description": "《神曲》叙事空间。", "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 5, "name": "天堂", "place_type": "fictional", "is_fictional": 1, "latitude": null, "longitude": null, "country": null, "region": null, "parent_place_id": null, "description": "《神曲》叙事空间。", "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 6, "name": "大观园", "place_type": "fictional", "is_fictional": 1, "latitude": null, "longitude": null, "country": null, "region": null, "parent_place_id": null, "description": "《红楼梦》虚构园林。", "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 7, "name": "俄罗斯", "place_type": "country", "is_fictional": 0, "latitude": null, "longitude": null, "country": null, "region": null, "parent_place_id": null, "description": "国家。", "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 8, "name": "莫斯科", "place_type": "city", "is_fictional": 0, "latitude": null, "longitude": null, "country": "俄罗斯", "region": null, "parent_place_id": null, "description": "城市。", "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 9, "name": "圣彼得堡", "place_type": "city", "is_fictional": 0, "latitude": null, "longitude": null, "country": "俄罗斯", "region": null, "parent_place_id": null, "description": "城市。", "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 10, "name": "伦敦", "place_type": "city", "is_fictional": 0, "latitude": null, "longitude": null, "country": "英国", "region": null, "parent_place_id": null, "description": "城市。", "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 11, "name": "古巴", "place_type": "country", "is_fictional": 0, "latitude": null, "longitude": null, "country": null, "region": null, "parent_place_id": null, "description": "国家。", "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 12, "name": "阿拉卡塔卡", "place_type": "city", "is_fictional": 0, "latitude": null, "longitude": null, "country": "哥伦比亚", "region": null, "parent_place_id": null, "description": "城市。", "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 13, "name": "墨西哥城", "place_type": "city", "is_fictional": 0, "latitude": null, "longitude": null, "country": "墨西哥", "region": null, "parent_place_id": null, "description": "城市。", "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 14, "name": "奥克帕克", "place_type": "city", "is_fictional": 0, "latitude": null, "longitude": null, "country": "美国", "region": null, "parent_place_id": null, "description": "城市。", "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 15, "name": "莫蒂哈里", "place_type": "city", "is_fictional": 0, "latitude": null, "longitude": null, "country": "印度", "region": null, "parent_place_id": null, "description": "城市。", "created_at": "2026-11-03 07:30:45", "updated_at": null},
    {"id": 16, "name": "佛罗伦萨", "place_type": "city", "is_fictional": 0, "latitude": null, "longitude": null, "country": "意大利", "region": null, "parent_place_id": null, "description": "城市。", "created_at": "2026-11-03 07:30:45", "updated_at": null}
  ]
}
```

### 3.4 GET `/api/places/1`

- 方法：GET
- 路径：`/api/places/1`
- 参数：无
- 状态码：`200`

```json
{
  "id": 1,
  "name": "马孔多",
  "place_type": "fictional",
  "is_fictional": 1,
  "latitude": null,
  "longitude": null,
  "country": null,
  "region": null,
  "parent_place_id": null,
  "description": "《百年孤独》虚构小镇。",
  "created_at": "2026-11-03 07:30:45",
  "updated_at": null
}
```

### 3.5 GET `/api/places/1/literature`

- 方法：GET
- 路径：`/api/places/1/literature`
- 参数：无
- 状态码：`200`

```json
{
  "place_id": 1,
  "total": 1,
  "items": [
    {
      "book": {
        "id": 2,
        "title": "百年孤独",
        "original_title": "Cien años de soledad",
        "language": "西班牙语",
        "publication_year": 1967,
        "description": "加西亚·马尔克斯代表作，魔幻现实主义经典。",
        "source": null,
        "created_at": "2026-11-03 07:30:45",
        "updated_at": null
      },
      "relation_type": "setting",
      "verification_status": "unverified",
      "source_name": null,
      "source_url": null,
      "note": null
    }
  ]
}
```

### 3.6 GET `/api/reading`

- 方法：GET
- 路径：`/api/reading`
- 参数：无
- 状态码：`200`

```json
{
  "total": 0,
  "items": []
}
```

> 当前数据库 `reading_records` 为空，故返回空列表。阅读记录的字段结构见 `docs/API.md` 第 8 节及下方第 5 节说明。

### 3.7 POST `/api/agent/chat`

- 方法：POST
- 路径：`/api/agent/chat`
- 请求体：`{"message": "帮我介绍《百年孤独》这本书"}`
- Content-Type：`application/json`
- 状态码：`502`（上游模型服务调用失败）

```json
{
  "detail": "上游模型服务调用失败"
}
```

> 说明：本次联调运行环境中，上游模型服务未能成功调用（模型 API Key 未生效/不可用），因此**未能捕获真实成功示例**。成功路径（HTTP 200）的响应结构按代码与 `docs/API.md` 约定为 `{"reply": "..."}`（仅 `reply` 字段，无 `answer`、无流式）。接口本身已正确接入：上游失败时返回 502 而非把错误伪装成 200。

### 3.8 边界情况补充实测

| 请求 | 状态码 | 响应 |
|------|--------|------|
| GET `/api/places/11/literature` | 200 | `{"place_id":11,"total":0,"items":[]}`（真实地点但无关联作品，返回空数组） |
| GET `/api/places/99/literature` | 404 | `{"detail":"地点不存在"}` |
| GET `/api/books/1` | 404 | `{"detail":"作品不存在"}` |
| GET `/api/books/999` | 404 | `{"detail":"作品不存在"}` |

---

## 4. 阅读统计与「文学足迹」接口核对（已实现）

- **独立的个人阅读统计 HTTP API**：✅ 已实现。
  - 路径：`GET /api/reading/statistics`。
  - 返回：`total` / `want_to_read` / `reading` / `finished`（只统计 `DEMO_USER_ID`，口径与 `GET /api/reading` 一致）。
  - 与 `backend/agent/tools.py` 里的 `get_reading_statistics`（Agent 内部只读工具）**相互独立**：前者是 HTTP API，后者仅供 AI 助手调用。

- **根据已读作品聚合真实地点的「文学足迹」HTTP API**：✅ 已实现。
  - 路径：`GET /api/reading/footprint`。
  - 规则：只统计 `status=finished` 的阅读记录；只保留真实地点（`is_fictional=0` 且 `place_type<>'fictional'`）；只保留经纬度均非 `null` 的地点；同一地点关联多部已读作品时合并（`books` 保留全部作品 `id`/`title`）；不涉及作者出生地/生活地/创作地。
  - ⚠️ 当前数据库所有地点经纬度均为 `null`，因此在补充坐标前，该接口在真实数据下总会返回空数组（空数组为合法结果，不编造坐标）。

---

## 5. 作品详情字段核对

`GET /api/books/{book_id}` 现已补充作者、流派、作品关联地点三类关联数据（旧字段保持不变）。

| 期望字段 | 是否提供 | 说明 |
|----------|----------|------|
| 作品 ID | ✅ 已实现 | 字段 `id` |
| 名称 | ✅ 已实现 | 字段 `title` |
| 简介 | ✅ 已实现 | 字段 `description` |
| 封面 | ❌ 未实现 | 无 `cover` / 封面字段，数据库也无封面列 |
| 创作年代 | ✅ 已实现 | 字段 `publication_year`（首次出版年份） |
| 作者 | ✅ 已实现 | 新增 `authors` 数组（含 name/nationality/bio/role） |
| 国家或地区 | ⚠️ 部分 | 通过 `authors[].nationality` 表达作者国籍；作品本身无独立「国家」字段 |
| 文学流派 | ✅ 已实现 | 新增 `genres` 数组（id/name/description） |
| 关联地点 | ✅ 已实现 | 新增 `places` 数组（作品的关联地点） |
| 地点关系类型 | ✅ 已实现 | `places[].relation_type`（setting/depiction）+ `relation_type_label` |

结论：

- 作品元数据旧字段（`id`/`title`/`original_title`/`language`/`publication_year`/`description`/`source`/`created_at`/`updated_at`）**不变**。
- 新增字段：`authors`（每位作者含其 `places`，区分作者出生地/生活地/创作地）、`genres`、`places`（区分作品故事发生地/描写地）。
- 无作者 / 无流派 / 无地点时对应数组返回 `[]`，不编造。

---

## 6. 现有文学数据清单

### 6.1 作品（6 部）

| id | title | language | publication_year |
|----|-------|----------|------------------|
| 2 | 百年孤独 | 西班牙语 | 1967 |
| 3 | 战争与和平 | 俄语 | 1869 |
| 4 | 1984 | 英语 | 1949 |
| 5 | 神曲 | 意大利语 | 1472 |
| 6 | 红楼梦 | 中文 | 1791 |
| 7 | 老人与海 | 英语 | 1952 |

### 6.2 作者（6 位）

| id | name | nationality | birth_year | death_year |
|----|------|-------------|------------|------------|
| 1 | 加夫列尔·加西亚·马尔克斯 | 哥伦比亚 | 1927 | 2014 |
| 2 | 列夫·托尔斯泰 | 俄国 | 1828 | 1910 |
| 3 | 乔治·奥威尔 | 英国 | 1903 | 1950 |
| 4 | 但丁·阿利吉耶里 | 意大利 | 1265 | 1321 |
| 5 | 曹雪芹 | 中国 | 1715(推定) | 1763(推定) |
| 6 | 欧内斯特·海明威 | 美国 | 1899 | 1961 |

### 6.3 地点（16 个）

**虚构地点（6 个，`is_fictional=1`，`place_type=fictional`，均无坐标）：**

| id | name | 关联作品 |
|----|------|----------|
| 1 | 马孔多 | 百年孤独 |
| 2 | 大洋国 | 1984 |
| 3 | 地狱 | 神曲 |
| 4 | 炼狱 | 神曲 |
| 5 | 天堂 | 神曲 |
| 6 | 大观园 | 红楼梦 |

**真实地点（10 个，`is_fictional=0`，均无坐标）：**

| id | name | place_type | country |
|----|------|------------|---------|
| 7 | 俄罗斯 | country | null |
| 8 | 莫斯科 | city | 俄罗斯 |
| 9 | 圣彼得堡 | city | 俄罗斯 |
| 10 | 伦敦 | city | 英国 |
| 11 | 古巴 | country | null |
| 12 | 阿拉卡塔卡 | city | 哥伦比亚 |
| 13 | 墨西哥城 | city | 墨西哥 |
| 14 | 奥克帕克 | city | 美国 |
| 15 | 莫蒂哈里 | city | 印度 |
| 16 | 佛罗伦萨 | city | 意大利 |

> ⚠️ 全部 16 个地点的 `latitude`/`longitude` 当前均为 `null`，第一版地图**尚无任何坐标数据**。

### 6.4 流派（6 个）

| id | name |
|----|------|
| 1 | 魔幻现实主义 |
| 2 | 现实主义 |
| 3 | 现代主义 |
| 4 | 反乌托邦 |
| 5 | 史诗 |
| 6 | 章回体小说 |

### 6.5 作品 ↔ 作者（6 条，全部 role=author）

| 作品 | 作者 |
|------|------|
| 百年孤独 | 加夫列尔·加西亚·马尔克斯 |
| 战争与和平 | 列夫·托尔斯泰 |
| 1984 | 乔治·奥威尔 |
| 神曲 | 但丁·阿利吉耶里 |
| 红楼梦 | 曹雪芹 |
| 老人与海 | 欧内斯特·海明威 |

### 6.6 作品 ↔ 地点（10 条，全部 relation_type=setting）

| 作品 | 地点 | relation_type |
|------|------|---------------|
| 百年孤独 | 马孔多(虚构) | setting |
| 战争与和平 | 俄罗斯 | setting |
| 战争与和平 | 莫斯科 | setting |
| 战争与和平 | 圣彼得堡 | setting |
| 1984 | 大洋国(虚构) | setting |
| 1984 | 伦敦 | setting |
| 神曲 | 地狱(虚构) | setting |
| 神曲 | 炼狱(虚构) | setting |
| 神曲 | 天堂(虚构) | setting |
| 红楼梦 | 大观园(虚构) | setting |

> 注意到《老人与海》当前**没有作品-地点关联**。

### 6.7 作品 ↔ 流派（6 条）

| 作品 | 流派 |
|------|------|
| 百年孤独 | 魔幻现实主义 |
| 战争与和平 | 现实主义 |
| 老人与海 | 现代主义 |
| 1984 | 反乌托邦 |
| 神曲 | 史诗 |
| 红楼梦 | 章回体小说 |

---

## 7. 地图字段核实结论

1. **`place_type` 允许值**：`country`（国家）、`city`（城市）、`region`（地区）、`fictional`（虚构）。由数据库 CHECK 约束强制；实际数据中只用到 `country`、`city`、`fictional` 三种，`region` 暂无用例。

2. **经纬度字段名称**：`latitude`（纬度，REAL）、`longitude`（经度，REAL）。

3. **`is_fictional` 用法**：`INTEGER`，`0` = 现实地点，`1` = 虚构地点。虚构地点（`is_fictional=1` / `place_type=fictional`）**强制无经纬度**（CHECK 约束，坐标必须为 null）。

4. **没有地点关联的作品，接口返回什么**：
   - `GET /api/books/{id}` 返回的 `places` 为 `[]`（现在作品详情已含 `places` 字段）。
   - 反向查询 `GET /api/places/{place_id}/literature`，当地点无关联作品时返回 `{"place_id": N, "total": 0, "items": []}`（实测 `places/11` 返回 200 空数组）。

5. **没有经纬度的地点，接口返回什么**：`latitude` 与 `longitude` 均返回 `null`（当前全部 16 个地点均如此）。

6. **作品 ↔ 地点关系表达**：`book_places` 表，`relation_type ∈ {setting(故事发生地), depiction(作品描写地)}`，通过 `GET /api/places/{place_id}/literature` 返回（附带 `verification_status`）。

7. **作者 ↔ 地点关系表达**：`author_places` 表，`relation_type ∈ {birthplace(出生地), residence(生活地), creation(创作地)}`，另有 `start_year`/`end_year`。现通过 `GET /api/books/{id}` 的 `authors[].places` 返回（与 `places`（作品地点）相互独立）。

> **第一版地图约束**：不展示 `place_type = 'fictional'`（`is_fictional = 1`）的地点；且当前所有地点均无坐标，前端**不得编造经纬度**。真实地点坐标需后续单独补充。

---

## 8. 附：敏感信息与未实现清单

### 敏感信息

本文档未包含任何 `.env`、API Key、上游模型凭证等内容。相关配置仅存在于 `backend/.env`（不纳入交接文档）。

### 已实现接口清单（完整）

- 系统：`GET /`、`GET /health`、`GET /docs`
- 作品：`POST/GET /api/books`、`GET/PATCH /api/books/{id}`（`GET /api/books/{id}` 已补全作者/流派/地点）
- 地点：`GET /api/places`、`GET /api/places/{id}`、`GET /api/places/{id}/literature`
- 阅读：`POST/GET /api/reading`、`PATCH/DELETE /api/reading/{id}`、`GET /api/reading/statistics`、`GET /api/reading/footprint`
- Agent：`POST /api/agent/chat`

### 当前缺失 / 未实现清单

1. 作品**封面**字段 —— 未实现（数据库无封面列，接口无 `cover` 字段）。
2. 作品独立的**国家/地区**字段 —— 未实现（仅能通过 `authors[].nationality` 间接表达作者国籍）。
3. 真实地点的**经纬度坐标数据** —— 全部为空，未录入（导致 `GET /api/reading/footprint` 当前在真实数据下总返回空数组）。
4. AI Agent 上游**模型配额** —— 外部限制，当前 `POST /api/agent/chat` 返回 502（上游 429 AccountQuotaExceeded，需等待配额重置或升级）。