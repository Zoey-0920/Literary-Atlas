# Literary Atlas 后端

World Literature Exploration Agent（世界文学探索智能体）的 FastAPI 后端服务，提供作品（books）、地点（places）、AI 智能体（agent）、个人阅读记录（reading）四组接口，数据存储于本地 SQLite。

## 技术栈

- Python 3.10+（本项目在 Python 3.14.6 上开发验证）
- FastAPI + Uvicorn（Web 框架与 ASGI 服务器）
- Pydantic v2（请求校验与响应模型）
- SQLite（Python 标准库 `sqlite3`，无需额外数据库服务）
- OpenAI SDK（连接 DeepSeek 兼容接口）
- python-dotenv（读取 `.env` 环境变量）

## 目录结构

```
backend/
├─ main.py                 # FastAPI 入口，注册四组路由，启动时自动建表
├─ config.py               # 全局配置（当前为演示用户 demo_user）
├─ database.py             # 建表 schema 与数据库连接
├─ seed.py                 # 第一版 6 部作品种子数据导入
├─ expansion_data.py       # 50 部作品扩充数据（纯数据）
├─ import_expansion.py     # 扩充数据导入（幂等、事务化）
├─ agent/                  # AI 智能体（LLM 客户端、工具、服务编排）
├─ routers/                # 作品 / 地点 / 智能体 / 阅读记录 四组路由
├─ docs/                   # 数据扩充方案文档
├─ test_*.py               # 独立测试脚本
├─ requirements.txt        # 依赖清单
└─ .env.example            # 环境变量模板
```

## 快速开始

### 1. Python 版本

要求 Python 3.10 及以上。

### 2. 创建并激活虚拟环境

Windows（PowerShell）：

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
```

macOS / Linux：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制 `.env.example` 为 `.env`，再填入真实值：

```powershell
# Windows
Copy-Item .env.example .env
```

```bash
# macOS / Linux
cp .env.example .env
```

`.env` 中的环境变量用途：

| 变量 | 是否必填 | 说明 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | 必填 | DeepSeek API 密钥，Agent 调用真实模型所需 |
| `DEEPSEEK_BASE_URL` | 可选 | API 基础地址，默认 `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 可选 | 模型名称，默认 `deepseek-chat` |

### 5. 初始化数据库并导入基础数据

数据库文件为 `backend/literary_atlas.db`（首次运行自动创建）。基础数据可完全由脚本重建，无需手动准备数据库文件。

在 `backend/` 目录下**按顺序**执行：

```bash
python seed.py               # 建表 + 导入第一版 6 部作品种子数据
python import_expansion.py   # 扩充到 50 部作品（幂等、事务化）
```

两个脚本均可重复执行（幂等，不会产生重复数据）。

### 6. 启动服务

```bash
uvicorn main:app --reload
```

服务默认监听 `http://localhost:8000`。

### 7. 访问 API 文档

- Swagger UI：<http://localhost:8000/docs>
- ReDoc：<http://localhost:8000/redoc>
- 健康检查：<http://localhost:8000/health>

## 接口概览

| 前缀 | 说明 |
| --- | --- |
| `/`、`/health` | 欢迎信息与健康检查 |
| `/api/books` | 作品列表 / 详情 / 修改 |
| `/api/places` | 地点列表 / 详情 / 关联作品 |
| `/api/reading` | 个人阅读记录（书架）增删改查与统计、足迹 |
| `/api/agent` | AI 智能体对话 |

完整接口参数与响应以 Swagger UI（`/docs`）为准。

## Agent 模型配置

Agent 通过 `.env` 中的 `DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL` 配置所调用的模型，默认使用 DeepSeek 官方 `deepseek-chat`。调用真实模型需要有效的 `DEEPSEEK_API_KEY`，**并可能产生费用**，请自备密钥并注意用量。

## 运行测试

测试为独立脚本，均使用临时 SQLite 数据库隔离，不会污染正式数据库。在 `backend/` 目录下直接运行：

```bash
python test_api.py
python test_seed.py
python test_import_expansion.py
python test_reading.py
python test_reading_tools.py
python test_agent_tools.py
```

以下测试会调用真实 DeepSeek 模型，需要有效的 `DEEPSEEK_API_KEY`，且可能产生费用：

```bash
python test_deepseek.py
python test_tool_calling.py
python test_agent_api.py
python test_agent_service.py
```

## 重要注意事项

- **不要提交真实 `.env`**：`.env` 含真实 API 密钥，已在 `backend/.gitignore` 中排除。
- **数据库无需随源码分发**：`literary_atlas.db` 可通过 `seed.py` + `import_expansion.py` 完整重建。
- **未实现用户登录**：当前阅读记录统一使用演示用户 `demo_user`（见 `config.py`），是比赛演示阶段的临时方案。
- **地点坐标待核实**：当前所有地点的经纬度均为空（未编造），后续核实后再补充。
- 数据扩充来源参见 `docs/DATA_EXPANSION_PLAN.md`。
