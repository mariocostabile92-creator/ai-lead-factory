from fastapi import APIRouter

from backend.api.routes import assistant, chat, conversations, health, leads

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(assistant.router, prefix="/assistant", tags=["assistant"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
api_router.include_router(conversations.router, prefix="/chat/history", tags=["chat"])
