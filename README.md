# 书行万里（Literary Atlas）

**读万卷书，行万里路。**

以阅读为起点，以文学为线索，以地理为窗口，探索世界各地的文学作品、作家与文化，让每一次阅读都成为一场跨越地域的精神旅行。

---

## 一、项目介绍

### 1. 项目背景与理念

「书行万里」的灵感来源于中国传统文化中的「读万卷书，行万里路」。

文学作品不仅承载着作者的思想与情感，也与特定的国家、城市、自然环境和历史文化背景密切相关。然而，在传统阅读过程中，作品、作者与地理空间往往是分散的。

本项目尝试将文学内容与真实地理空间相结合，以世界地图为探索入口，让用户在阅读文学作品的同时，了解作品背后的地域文化与地理背景。

用户既可以从一部作品出发，探索它所关联的地点，也可以从一个国家或城市出发，发现当地的文学作品与作家。

### 2. 项目定位

书行万里是一款融合世界文学、地理探索与人工智能技术的交互式文学探索平台。

项目以文学阅读为核心，以地理空间为探索线索，以 AI 智能体为辅助工具，集文学知识探索、个人阅读管理和智能交互于一体。

**项目愿景：让阅读拥有地理坐标，让世界文学触手可及。**

---

## 二、核心功能

### 1. 世界文学地图

- 通过交互式世界地图探索不同国家和地区的文学内容。
- 展示文学作品、作家与真实地理地点之间的关联。
- 从国家、城市等地理位置出发，发现相关文学作品。
- 支持世界文学总览与个人文学足迹地图切换。

### 2. 世界文学作品探索

- 浏览来自不同国家和地区的代表性文学作品。
- 查看作品详情、作者信息及相关文学背景。
- 通过地理位置和文学分类发现作品。
- 以具有代表性的世界文学经典为基础，构建跨文化文学探索内容。

### 3. 个人阅读书架

- 将文学作品加入个人书架。
- 管理想读、在读和已读状态。
- 添加、修改和删除阅读记录。
- 查看个人阅读统计信息。

### 4. 我的文学足迹

- 根据个人阅读记录展示相关文学地点。
- 将阅读经历与作品关联的真实地理空间联系起来。
- 从个人阅读轨迹出发，探索不同国家和地区的文学文化。

### 5. AI 文学探索助手

- 通过自然语言与 AI 智能体进行对话。
- 查询文学作品、作家及相关地点信息。
- 借助 AI 工具访问文学数据库，辅助用户探索作品与地理空间之间的联系。
- 根据已有文学资料提供智能问答与探索建议。

---

## 三、技术架构

项目采用前后端分离架构。

| 模块 | 技术 |
|---|---|
| 前端框架 | Vue 3 |
| 前端构建工具 | Vite |
| 前端开发语言 | JavaScript |
| 后端框架 | Python、FastAPI |
| 后端服务器 | Uvicorn |
| 数据校验 | Pydantic v2 |
| 数据库 | SQLite |
| AI 接口 | OpenAI SDK（兼容 DeepSeek API） |
| 地图展示 | SVG 世界地图及地理数据 |

### 系统组成

- **前端层：** 负责地图展示、文学内容呈现、个人书架、文学足迹及用户交互。
- **后端层：** 提供文学作品、地点、阅读记录及 AI 智能体相关 API。
- **数据层：** 使用 SQLite 存储文学作品、地点及阅读记录。
- **AI 智能体层：** 通过大语言模型和后端工具访问文学数据，为用户提供智能探索服务。

---

## 四、项目目录结构

```text
Literary-Atlas/
│
├── frontend/                     # Vue 前端项目
│   ├── src/                      # 页面、组件及业务逻辑
│   ├── src/assets/               # 地图地理数据（world.geo.json）及地图背景等静态资源
│   ├── .env.example              # 前端环境变量模板
│   └── package.json              # 前端依赖配置
│
├── backend/                      # FastAPI 后端项目
│   ├── agent/                    # AI 智能体相关代码
│   ├── routers/                  # API 路由
│   ├── main.py                   # 后端入口
│   ├── config.py                 # 全局配置
│   ├── database.py               # 数据库连接与结构
│   ├── seed.py                   # 基础数据初始化
│   ├── expansion_data.py         # 文学作品扩充数据
│   ├── import_expansion.py       # 扩充数据导入
│   ├── requirements.txt          # Python 依赖
│   ├── .env.example              # 后端环境变量模板
│   └── README.md                 # 后端使用说明
│
├── docs/                         # 项目文档
│   ├── .gitkeep                  # Git 空目录保留文件
│   ├── API.md                    # 前后端接口文档
│   └── DATA_EXPANSION_PLAN.md    # 文学数据扩充方案
│
├── FRONTEND_HANDOFF.md           # 前后端交接文档
└── README.md                     # 项目总说明
```

---

## 五、运行环境要求

运行项目前，需要准备：

- Windows、macOS 或 Linux 操作系统。
- Python 3.10 或以上版本。
- Node.js 和 npm。
- Git（可选，用于克隆项目）。

后端开发环境使用过 Python 3.14.6，实际运行时请根据依赖安装情况选择兼容版本。

---

## 六、获取项目

通过 Git 克隆项目：

```bash
git clone https://github.com/Zoey-0920/Literary-Atlas.git
```

进入项目目录：

```bash
cd Literary-Atlas
```

也可以在 GitHub 仓库页面点击 Code → Download ZIP，下载并解压项目。

---

## 七、后端安装与配置

### 1. 进入后端目录

```bash
cd backend
```

### 2. 创建 Python 虚拟环境

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\activate
```

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

将 `backend/.env.example` 复制为 `backend/.env`。

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

macOS / Linux：

```bash
cp .env.example .env
```

打开 `.env`，填写自己的 DeepSeek API 配置：

```env
DEEPSEEK_API_KEY=填写自己的API密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

其中，`DEEPSEEK_API_KEY` 需要填写有效的 API 密钥。模型调用可能产生费用，请使用者自行管理密钥和使用额度。

### 5. 初始化数据库

在 `backend/` 目录下，按顺序执行：

```bash
python seed.py
python import_expansion.py
```

两个脚本分别用于初始化基础数据和导入扩充文学数据。扩充数据导入支持重复执行。

数据库文件会在本地自动创建，无需额外安装数据库服务器。

### 6. 启动后端

确保当前仍在 `backend/` 目录，且虚拟环境已经激活：

```bash
uvicorn main:app --reload
```

默认后端地址：

```text
http://127.0.0.1:8000
```

相关接口：

- API 文档：http://127.0.0.1:8000/docs
- ReDoc 文档：http://127.0.0.1:8000/redoc
- 健康检查：http://127.0.0.1:8000/health

---

## 八、前端安装与配置

### 1. 打开新的终端

保持后端服务继续运行，另外打开一个终端，进入项目的前端目录：

```bash
cd Literary-Atlas/frontend
```

### 2. 安装依赖

```bash
npm install
```

### 3. 配置环境变量

将 `frontend/.env.example` 复制为 `frontend/.env`。

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

macOS / Linux：

```bash
cp .env.example .env
```

打开 `frontend/.env`，配置后端 API 地址：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

该地址适用于前后端在同一台电脑上运行、后端使用默认 8000 端口的情况。

### 4. 启动前端

```bash
npm run dev
```

前端默认访问地址：

```text
http://localhost:5173
```

在浏览器中打开该地址，即可进入「书行万里」。

---

## 九、使用说明

1. 启动后端服务。
2. 启动前端服务。
3. 在浏览器中访问 `http://localhost:5173`。
4. 通过世界文学地图探索不同国家和地区的文学作品。
5. 查看作品详情、作者信息及相关文学背景。
6. 使用个人书架管理阅读记录。
7. 查看个人文学足迹。
8. 配置有效的 DeepSeek API Key 后，体验 AI 文学探索助手。

---

## 十、注意事项

### 1. API Key 安全

不要将包含真实 API Key 的 `.env` 文件上传至 GitHub。

项目提供 `.env.example` 作为配置模板，使用者需要自行复制并创建本地 `.env` 文件，填写自己的密钥。

### 2. 数据库说明

项目使用 SQLite，数据库文件由初始化脚本在本地创建。

### 3. 用户系统说明

当前版本尚未实现用户注册和登录，阅读记录统一使用演示用户 `demo_user`。因此，当前版本主要用于项目体验和演示，尚不支持不同用户之间的阅读数据隔离。

### 4. AI 服务说明

AI 助手需要有效的 DeepSeek API Key。未配置有效密钥或网络无法访问模型服务时，AI 对话功能可能无法正常使用。

### 5. 地理数据说明

地图展示以真实地理地点为基础。尚未核实的地点坐标不应被当作准确地理位置使用。

---

## 十一、项目文档

- `backend/README.md`：后端安装、配置、运行及测试说明。
- `docs/API.md`：前后端 API 接口文档。
- `docs/DATA_EXPANSION_PLAN.md`：文学作品数据扩充方案。
- `FRONTEND_HANDOFF.md`：前后端交接文档。

---

## 十二、团队分工

- **成员 A：** 前端开发，负责用户界面、交互设计、地图展示及前端业务逻辑。
- **成员 B：** 后端开发与 AI Agent，负责 API 服务、数据库、文学数据管理及 AI 智能体。

---

**书行万里 · Literary Atlas**

*Read the World. Explore Through Literature.*
