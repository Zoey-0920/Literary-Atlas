# Literary Atlas 后端 API 文档

> 服务地址：`http://127.0.0.1:8000`
> 接口统一前缀：作品 `/api/books`、地点 `/api/places`、作者 `/api/authors`、个人阅读 `/api/reading`、Agent `/api/agent`

## 通用说明

- 请求与响应均为 `application/json`。
- 校验失败（参数不合法）返回 HTTP `422`。
- 资源不存在返回 HTTP `404`。

---

## 1. 新增作品

`POST /api/books`

### 请求体（JSON）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | 书名，不能为空或纯空格 |
| original_title | string | 否 | 原语言书名 |
| language | string | 否 | 原著语言 |
| publication_year | integer | 否 | 首次出版年份，必须是整数（不接受小数/布尔值） |
| description | string | 否 | 内容简介 |
| source | string | 否 | 元数据来源 |

> 客户端不能指定 `id`、`created_at`、`updated_at`，它们由服务端生成。

### 请求示例

```json
{
  "title": "百年孤独",
  "original_title": "Cien años de soledad",
  "language": "西班牙语",
  "publication_year": 1967,
  "description": "布恩迪亚家族七代人的传奇故事。",
  "source": "待核实"
}
```

### 成功响应（HTTP 201）

```json
{
  "id": 1,
  "title": "百年孤独",
  "original_title": "Cien años de soledad",
  "language": "西班牙语",
  "publication_year": 1967,
  "description": "布恩迪亚家族七代人的传奇故事。",
  "source": "待核实",
  "created_at": "2026-11-03 10:00:00",
  "updated_at": null
}
```

### 常见错误

| 状态码 | 说明 |
|--------|------|
| 422 | 缺少 `title`，或 `title` 为空/纯空格，或 `publication_year` 不是整数 |

---

## 2. 获取作品列表

`GET /api/books`

### 查询参数

| 参数 | 类型 | 默认 | 范围 | 说明 |
|------|------|------|------|------|
| limit | integer | 20 | 1 ~ 100 | 每页数量 |
| offset | integer | 0 | >= 0 | 跳过的条数 |
| keyword | string | 无 | - | 可选，按书名或原名模糊搜索 |

结果按 `id` 升序排列。

### 请求示例

```
GET /api/books?limit=20&offset=0&keyword=百年
```

### 成功响应（HTTP 200）

```json
{
  "total": 1,
  "items": [
    {
      "id": 1,
      "title": "百年孤独",
      "original_title": "Cien años de soledad",
      "language": "西班牙语",
      "publication_year": 1967,
      "description": "布恩迪亚家族七代人的传奇故事。",
      "source": "待核实",
      "created_at": "2026-11-03 10:00:00",
      "updated_at": null
    }
  ]
}
```

### 常见错误

| 状态码 | 说明 |
|--------|------|
| 422 | `limit` 超出 1~100，或 `offset` 小于 0 |

---

## 3. 查询作品详情

`GET /api/books/{book_id}`

### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| book_id | integer | 作品 id |

### 成功响应（HTTP 200）

返回作品元数据（字段同「新增作品」），并在此基础上补充作者、流派、关联地点三类关联数据。**旧字段保持不变**，新增字段为 `authors`、`genres`、`places`。

| 新增字段 | 类型 | 说明 |
|----------|------|------|
| authors | array | 作者列表（含每位作者自己的关联地点） |
| genres | array | 文学流派列表 |
| places | array | 作品关联地点（故事发生地 / 作品描写地） |

`authors`、`genres`、`places` 的嵌套结构见下方示例。

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
  "updated_at": null,
  "authors": [
    {
      "id": 1,
      "name": "加夫列尔·加西亚·马尔克斯",
      "birth_year": 1927,
      "death_year": 2014,
      "nationality": "哥伦比亚",
      "bio": "哥伦比亚作家。",
      "role": "author",
      "places": [
        {
          "id": 12,
          "name": "阿拉卡塔卡",
          "place_type": "city",
          "is_fictional": 0,
          "country": "哥伦比亚",
          "region": null,
          "relation_type": "birthplace",
          "relation_type_label": "出生地",
          "start_year": null,
          "end_year": null,
          "verification_status": "unverified"
        },
        {
          "id": 13,
          "name": "墨西哥城",
          "place_type": "city",
          "is_fictional": 0,
          "country": "墨西哥",
          "region": null,
          "relation_type": "creation",
          "relation_type_label": "创作地",
          "start_year": null,
          "end_year": null,
          "verification_status": "unverified"
        }
      ]
    }
  ],
  "genres": [
    {
      "id": 1,
      "name": "魔幻现实主义",
      "description": "将现实与奇幻融合的文学流派。"
    }
  ],
  "places": [
    {
      "id": 1,
      "name": "马孔多",
      "place_type": "fictional",
      "is_fictional": 1,
      "latitude": null,
      "longitude": null,
      "country": null,
      "region": null,
      "relation_type": "setting",
      "relation_type_label": "故事发生地",
      "verification_status": "unverified",
      "source_name": null,
      "source_url": null,
      "note": null
    }
  ]
}
```

字段说明：

- `authors[].places`：该作者的关联地点（`relation_type` ∈ `birthplace`/`residence`/`creation`）。
- `places`：作品的关联地点（`relation_type` ∈ `setting`/`depiction`），与作者地点相互独立。
- 无作者 / 无流派 / 无地点时，对应数组返回 `[]`。
- `latitude`/`longitude` 为地点坐标，未录入时为 `null`（当前全部为 `null`）。

### 常见错误

| 状态码 | 说明 |
|--------|------|
| 404 | 该 id 的作品不存在 |

---

## 4. 修改作品（部分更新）

`PATCH /api/books/{book_id}`

### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| book_id | integer | 作品 id |

### 请求体（JSON，所有字段均可省略）

| 字段 | 类型 | 说明 |
|------|------|------|
| title | string | 若提供，不能为空或纯空格 |
| original_title | string | 传 `null` 表示清空 |
| language | string | 传 `null` 表示清空 |
| publication_year | integer | 整数；传 `null` 表示清空 |
| description | string | 传 `null` 表示清空 |
| source | string | 传 `null` 表示清空 |

规则：

- 未提供的字段保持不变。
- 显式传 `null` 的字段（`title` 除外）会被置空。
- 每次修改都会自动更新 `updated_at`。

### 请求示例

```json
{
  "description": "布恩迪亚家族七代人的传奇故事，魔幻现实主义代表作。"
}
```

### 成功响应（HTTP 200）

返回修改后的完整作品信息（`updated_at` 已刷新）。

### 常见错误

| 状态码 | 说明 |
|--------|------|
| 404 | 该 id 的作品不存在 |
| 422 | `title` 传入空/纯空格（或 null），或 `publication_year` 不是整数 |

---

## 5. 获取地点列表

`GET /api/places`

### 查询参数

| 参数 | 类型 | 默认 | 范围 | 说明 |
|------|------|------|------|------|
| limit | integer | 20 | 1 ~ 100 | 每页数量 |
| offset | integer | 0 | >= 0 | 跳过的条数 |
| keyword | string | 无 | - | 可选，按地点名称模糊搜索 |

结果按 `id` 升序排列。

### 请求示例

```
GET /api/places?limit=20&offset=0&keyword=伦
```

### 成功响应（HTTP 200）

```json
{
  "total": 1,
  "items": [
    {
      "id": 1,
      "name": "伦敦",
      "place_type": "city",
      "is_fictional": 0,
      "latitude": 51.5,
      "longitude": -0.12,
      "country": "英国",
      "region": "英格兰",
      "parent_place_id": null,
      "description": null,
      "created_at": "2026-11-03 02:00:00",
      "updated_at": null
    }
  ]
}
```

### 常见错误

| 状态码 | 说明 |
|--------|------|
| 422 | `limit` 超出 1~100，或 `offset` 小于 0 |

---

## 6. 查询地点详情

`GET /api/places/{place_id}`

### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| place_id | integer | 地点 id |

### 成功响应（HTTP 200）

返回地点完整信息（字段同「获取地点列表」中的 items 元素）。

### 常见错误

| 状态码 | 说明 |
|--------|------|
| 404 | 该 id 的地点不存在 |

---

## 7. 查询地点关联的文学作品

`GET /api/places/{place_id}/literature`

### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| place_id | integer | 地点 id |

### 成功响应（HTTP 200）

```json
{
  "place_id": 1,
  "total": 1,
  "items": [
    {
      "book": {
        "id": 1,
        "title": "伦敦游记",
        "original_title": null,
        "language": null,
        "publication_year": null,
        "description": null,
        "source": null,
        "created_at": "2026-11-03 02:00:00",
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

关联字段说明：

- `relation_type`：`setting`（故事发生地）/ `depiction`（描写地）
- `verification_status`：`verified` / `unverified` / `disputed`

### 常见错误

| 状态码 | 说明 |
|--------|------|
| 404 | 该 id 的地点不存在 |

---

## 8. 个人阅读管理接口

> 接口统一前缀：`/api/reading`

当前项目**尚未实现用户登录系统**。为完成比赛演示，所有阅读记录统一挂在固定的演示用户下（`config.DEMO_USER_ID`，值为 `demo_user`）。

> ⚠️ 这是**比赛演示阶段的临时方案**，不代表完整的账号体系。所有接口都按该演示用户做数据隔离，不会返回或修改其他用户的记录；正式接入登录后需要替换为真实用户标识。

阅读状态取值（与数据库约束一致）：

| 值 | 含义 |
|----|------|
| want_to_read | 想读 |
| reading | 在读 |
| finished | 读完 |

### 8.1 添加一本书到书架

`POST /api/reading`

### 请求体（JSON）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| book_id | integer | 是 | 作品 id，必须真实存在 |
| status | string | 是 | 阅读状态：want_to_read / reading / finished |
| rating | integer | 否 | 评分，1 ~ 5 |
| progress | integer | 否 | 阅读进度，0 ~ 100 |
| started_at | string | 否 | 开始阅读时间 |
| finished_at | string | 否 | 读完时间 |
| note | string | 否 | 个人笔记 |

### 请求示例

```json
{
  "book_id": 1,
  "status": "reading",
  "rating": 4,
  "progress": 35,
  "note": "魔幻现实主义代表作"
}
```

### 成功响应（HTTP 201）

```json
{
  "id": 1,
  "user_id": "demo_user",
  "book_id": 1,
  "book_title": "百年孤独",
  "status": "reading",
  "rating": 4,
  "progress": 35,
  "started_at": null,
  "finished_at": null,
  "note": "魔幻现实主义代表作",
  "created_at": "2026-11-03 10:00:00",
  "updated_at": null
}
```

### 常见错误

| 状态码 | 说明 |
|--------|------|
| 404 | `book_id` 对应的作品不存在 |
| 409 | 该作品已在该用户书架中（同一作品只能有一条记录） |
| 422 | `status` 非法、`rating` 越界、`progress` 越界等 |

---

### 8.2 查看个人书架

`GET /api/reading`

### 查询参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| status | string | 无 | 可选，按阅读状态筛选 |

### 成功响应（HTTP 200）

```json
{
  "total": 1,
  "items": [
    {
      "id": 1,
      "user_id": "demo_user",
      "book_id": 1,
      "book_title": "百年孤独",
      "status": "reading",
      "rating": 4,
      "progress": 35,
      "started_at": null,
      "finished_at": null,
      "note": "魔幻现实主义代表作",
      "created_at": "2026-11-03 10:00:00",
      "updated_at": null
    }
  ]
}
```

---

### 8.3 修改书架记录（部分更新）

`PATCH /api/reading/{record_id}`

请求体字段与「8.1」一致，但**所有字段均可省略**，未提供的字段保持不变。

### 请求示例

```json
{
  "status": "finished",
  "progress": 100,
  "rating": 5
}
```

### 成功响应（HTTP 200）

返回修改后的完整记录。

### 常见错误

| 状态码 | 说明 |
|--------|------|
| 404 | 该 id 的阅读记录不存在（或不属于演示用户） |

---

### 8.4 删除书架记录

`DELETE /api/reading/{record_id}`

### 成功响应（HTTP 204）

无响应体。

### 常见错误

| 状态码 | 说明 |
|--------|------|
| 404 | 该 id 的阅读记录不存在（或不属于演示用户） |

---

### 8.5 个人阅读统计

`GET /api/reading/statistics`

> 统计当前演示用户（`config.DEMO_USER_ID`）的阅读记录数量，口径与 `GET /api/reading` 一致。

### 成功响应（HTTP 200）

```json
{
  "total": 0,
  "want_to_read": 0,
  "reading": 0,
  "finished": 0
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| total | integer | 书架作品总数 |
| want_to_read | integer | 想读作品数 |
| reading | integer | 在读作品数 |
| finished | integer | 已读作品数 |

> 空书架时所有统计数量均为 0。

---

### 8.6 个人文学足迹

`GET /api/reading/footprint`

> 根据当前演示用户「已读」（`status=finished`）的作品，聚合其关联的真实地点作为个人文学足迹。

筛选规则：

- 只统计 `status='finished'` 的阅读记录。
- 只返回真实地点（`is_fictional=0` 且 `place_type<>'fictional'`）。
- 只返回经纬度均有效（均非 `null`）的地点。
- 只依据作品↔地点关系（`book_places`），**不**包含作者出生地/生活地/创作地。
- 同一地点关联多部已读作品时合并，`books` 保留全部关联作品 ID 与书名。
- 不编造经纬度；无坐标地点会被过滤。

### 成功响应（HTTP 200）

```json
{
  "total": 1,
  "items": [
    {
      "place_id": 17,
      "name": "测试城市甲",
      "place_type": "city",
      "latitude": 48.8566,
      "longitude": 2.3522,
      "country": "测试国",
      "region": null,
      "books": [
        {"id": 2, "title": "百年孤独"},
        {"id": 3, "title": "战争与和平"}
      ]
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| total | integer | 足迹地点数 |
| items | array | 足迹地点数组 |

`items` 元素字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| place_id | integer | 地点 id |
| name | string | 地点名 |
| place_type | string | 地点类型（此处均为真实地点） |
| latitude | number | 纬度 |
| longitude | number | 经度 |
| country | string / null | 所属国家 |
| region | string / null | 所属地区 |
| books | array | 该地点关联的已读作品 |

`books` 元素字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | integer | 作品 id |
| title | string | 作品名 |

> ⚠️ 当前数据库所有地点经纬度均为 `null`，因此在补充地点坐标前，该接口在真实数据下会返回空数组（上述示例为测试数据）。

---

## 9. AI Agent 聊天

`POST /api/agent/chat`

> 完整本地地址：`http://localhost:8000/api/agent/chat`
> Content-Type：`application/json`
> 第一版不使用流式输出。

### 请求体（JSON）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message | string | 是 | 用户输入的问题 |

每次请求独立处理，不携带历史消息。

### 请求示例

```json
{
  "message": "帮我介绍一下《百年孤独》"
}
```

### 成功响应（HTTP 200）

```json
{
  "reply": "《百年孤独》是哥伦比亚作家加西亚·马尔克斯创作的长篇小说……"
}
```

字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| reply | string | AI Agent 生成的最终回答 |

> 成功响应字段统一使用 `reply`，不使用 `answer`，且不同时返回两者。

### 错误响应

错误响应采用 FastAPI 的 HTTPException 格式：

```json
{
  "detail": "错误说明"
}
```

| HTTP 状态码 | 含义 | 说明 |
|------|------|------|
| 422 | 请求参数错误 | message 缺失或格式不符合要求 |
| 502 | 上游模型服务错误 | 企业模型 API 调用失败 |
| 500 | 服务器内部错误 | 其他未预期的服务端异常 |

> 实际错误响应以 FastAPI 的异常处理行为为准，不要将所有异常都伪装成 200。

### Agent 数据库工具（只读）

Agent 会按需调用以下只读工具查询数据库后再组织回答，不会直接生成 SQL，也不会执行任意代码：

| 工具名 | 用途 |
|--------|------|
| search_books | 按书名关键词模糊搜索作品 |
| list_books | 列出数据库中的全部作品（用于推荐 / 浏览） |
| search_places | 按地点名关键词模糊搜索地点 |
| get_book_detail | 按作品 ID 查询详情（含作者、地点、流派） |
| get_reading_records | 查询演示用户的阅读记录（可按状态筛选） |
| get_reading_statistics | 统计演示用户的阅读记录（想读 / 在读 / 读完 / 总数） |

> 推荐作品时 Agent 只能基于数据库真实存在的作品，不会虚构书籍。

### 前端交互约定

前端需要实现：

- 区分用户消息和 AI 回复。
- AI 请求过程中显示加载状态。
- 请求过程中防止重复提交。
- 请求失败时向用户显示错误提示。
- 收到成功响应后读取 `reply` 并显示。
- 不需要展示 Agent 内部工具调用过程。
- 不需要流式输出。

> 加载状态、消息展示和防重复提交属于前端交互逻辑，不需要额外增加本次接口字段。

### 第一版明确不支持的功能

- 不支持聊天历史。
- 不支持跨请求上下文记忆。
- 不使用 `conversation_id`。
- 每次请求都是独立问答。

### 后续扩展约定

后续计划支持连续对话，届时可以增加可选字段：

```json
{
  "message": "继续介绍一下这本书",
  "conversation_id": "example-conversation-id"
}
```

- 该字段仅作为未来扩展方案，第一版不实现。
- 后续增加时必须保持向后兼容：旧版只传 `message` 的请求仍然有效。
- `conversation_id` 不应成为第一版必填字段。

---

## 10. 作者接口

> 接口统一前缀：`/api/authors`
> 说明：本模块只做**只读查询**，不写数据库。作者与作品的关联来自 `book_authors` 表，`role` 取值为 `author`（作者）/ `translator`（译者）/ `editor`（编者）。

### 10.1 获取作者列表

`GET /api/authors`

分页返回作者列表，可按姓名关键词模糊搜索，结果按 `id` 升序排列。

### 查询参数

| 参数 | 类型 | 必填 | 默认 | 范围 | 说明 |
|------|------|------|------|------|------|
| keyword | string | 否 | 无 | - | 可选，按作者姓名（`name`）模糊搜索，忽略首尾空格 |
| limit | integer | 否 | 20 | 1 ~ 100 | 每页数量 |
| offset | integer | 否 | 0 | >= 0 | 跳过的条数 |

### 请求示例

```
GET /api/authors?limit=20&offset=0&keyword=马尔克斯
```

### 成功响应（HTTP 200）

```json
{
  "total": 46,
  "items": [
    {
      "id": 1,
      "name": "加夫列尔·加西亚·马尔克斯",
      "birth_year": 1927,
      "death_year": 2014,
      "nationality": "哥伦比亚",
      "bio": "哥伦比亚作家。",
      "created_at": "2026-11-03 07:30:45",
      "updated_at": null
    }
  ]
}
```

分页字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| total | integer | 符合筛选条件的作者总数（不是当前页条数） |
| items | array | 当前页的作者数组 |

`items` 元素字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | integer | 作者 id |
| name | string | 作者姓名 |
| birth_year | integer / null | 出生年份，未录入时为 `null` |
| death_year | integer / null | 去世年份，未录入时为 `null` |
| nationality | string / null | 国籍，未录入时为 `null` |
| bio | string / null | 作者简介，未录入时为 `null` |
| created_at | string | 记录创建时间（`YYYY-MM-DD HH:MM:SS`） |
| updated_at | string / null | 记录更新时间，未更新时为 `null` |

### 常见错误

| 状态码 | 说明 |
|--------|------|
| 422 | `limit` 超出 1 ~ 100，或 `offset` 小于 0 |

---

### 10.2 查询作者详情

`GET /api/authors/{author_id}`

根据 id 查询作者详情（含其关联的全部作品）。

### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| author_id | integer | 作者 id |

### 成功响应（HTTP 200）

```json
{
  "id": 1,
  "name": "加夫列尔·加西亚·马尔克斯",
  "birth_year": 1927,
  "death_year": 2014,
  "nationality": "哥伦比亚",
  "bio": "哥伦比亚作家。",
  "created_at": "2026-11-03 07:30:45",
  "updated_at": null,
  "books": [
    {
      "id": 2,
      "title": "百年孤独",
      "original_title": "Cien años de soledad",
      "language": "西班牙语",
      "publication_year": 1967,
      "role": "author"
    }
  ]
}
```

基本字段（`id`、`name`、`birth_year`、`death_year`、`nationality`、`bio`、`created_at`、`updated_at`）与「10.1 获取作者列表」中 `items` 元素一致，在此之上补充 `books` 字段。

`books` 元素字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | integer | 作品 id |
| title | string | 书名 |
| original_title | string / null | 原语言书名，未录入时为 `null` |
| language | string / null | 原著语言，未录入时为 `null` |
| publication_year | integer / null | 首次出版年份，未录入时为 `null` |
| role | string / null | 该作者在本作品中的角色：`author` / `translator` / `editor` |

- `books[]` 为该作者通过 `book_authors` 关联的全部作品，按作品 id 升序排列。
- 一个作者关联多部作品时全部返回，同一作品不会重复出现。
- 作者未关联任何作品时，`books` 返回 `[]`。

### 常见错误

| 状态码 | 说明 |
|--------|------|
| 404 | 该 id 的作者不存在 |
| 422 | `author_id` 不是整数 |

---

## 附：系统接口（保持原样）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 欢迎信息 |
| GET | `/health` | 健康检查 |
| GET | `/docs` | Swagger 交互式文档 |