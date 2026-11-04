"""Literary Atlas 后端入口文件。

这是整个后端服务的启动入口，使用 FastAPI 框架。
运行本文件后，即可通过 http://localhost:8000 访问接口。
"""

# 用于实现 FastAPI 的 lifespan 生命周期管理
from contextlib import asynccontextmanager

# 从 fastapi 包中导入 FastAPI 类
from fastapi import FastAPI

# 导入跨域（CORS）中间件，用于允许指定前端来源访问后端接口
from fastapi.middleware.cors import CORSMiddleware

# 导入已有的数据库初始化函数（不重复实现建表逻辑）
from database import init_db

# 导入作品相关接口路由
from routers.books import router as books_router

# 导入地点相关接口路由
from routers.places import router as places_router

# 导入 AI Agent 聊天接口路由
from routers.agent import router as agent_router

# 导入个人阅读记录接口路由
from routers.reading import router as reading_router

# 导入作者相关接口路由
from routers.authors import router as authors_router


# lifespan：FastAPI 推荐的生命周期管理方式
# 在应用启动、正式开始处理请求之前执行初始化
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动阶段：初始化数据库（创建数据表）
    # 若初始化失败会抛出异常，使启动过程明确报错，而不会静默忽略
    init_db()
    yield
    # 关闭阶段：目前无需额外清理资源，直接结束即可


# 创建 FastAPI 应用实例
# title     : 项目名称
# description: 项目描述
# version   : 当前版本号
# lifespan  : 生命周期处理器（启动时初始化数据库）
app = FastAPI(
    title="Literary Atlas API",
    description="World Literature Exploration Agent API",
    version="0.1.0",
    lifespan=lifespan,
)

# 配置跨域（CORS）：只允许明确列出的前端来源，不使用通配符 "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)

# 注册作品接口路由，统一前缀为 /api/books
app.include_router(books_router, prefix="/api/books")

# 注册地点接口路由，统一前缀为 /api/places
app.include_router(places_router, prefix="/api/places")

# 注册 AI Agent 聊天接口路由，统一前缀为 /api/agent
app.include_router(agent_router, prefix="/api/agent")

# 注册个人阅读记录接口路由，统一前缀为 /api/reading
app.include_router(reading_router, prefix="/api/reading")

# 注册作者接口路由，统一前缀为 /api/authors
app.include_router(authors_router, prefix="/api/authors")


# GET / 接口：访问网站根路径时返回欢迎信息
@app.get("/")
def read_root():
    """根路径接口，返回欢迎信息。"""
    return {
        "message": "Welcome to Literary Atlas API",
        "status": "success",
    }


# GET /health 接口：用于健康检查，确认服务是否正常运行
@app.get("/health")
def health_check():
    """健康检查接口，返回服务运行状态。"""
    return {
        "status": "healthy",
        "service": "Literary Atlas API",
    }