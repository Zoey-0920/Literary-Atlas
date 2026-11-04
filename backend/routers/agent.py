"""AI Agent 聊天接口。

POST /api/agent/chat

按已确认的 docs/API.md 约定实现：
- 请求：{"message": "..."}，message 非空且非纯空格。
- 成功：{"reply": "..."}（统一使用 reply，不使用 answer）。
- 参数错误：422；模型服务异常：502；其他异常：500。
"""

from fastapi import APIRouter, HTTPException
from openai import APIError
from pydantic import BaseModel, field_validator

from agent.agent_service import chat_with_agent

router = APIRouter()


class AgentChatRequest(BaseModel):
    """AI Agent 聊天请求体。"""

    message: str

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        """message 不能为空字符串或纯空格。"""
        if not v or not v.strip():
            raise ValueError("message 不能为空或全为空格")
        return v


class AgentChatResponse(BaseModel):
    """AI Agent 聊天成功响应体。"""

    reply: str


@router.post("/chat", response_model=AgentChatResponse)
async def chat(request: AgentChatRequest) -> AgentChatResponse:
    """处理一次 AI Agent 聊天请求，返回模型最终回答。"""
    try:
        reply = await chat_with_agent(request.message)
    except APIError:
        # 上游模型服务调用失败
        raise HTTPException(status_code=502, detail="上游模型服务调用失败")
    except Exception:
        # 其他未预期异常：不向前端泄露 API Key、堆栈等敏感信息
        raise HTTPException(status_code=500, detail="服务器内部错误")

    return AgentChatResponse(reply=reply)
