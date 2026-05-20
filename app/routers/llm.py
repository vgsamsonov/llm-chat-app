from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
import json
import asyncio
from app.database import get_db_session
from app.services.llm_service import llm_service
from app.services.message_service import create_message, get_chat_messages
from app.services.chat_service import get_chat
from app.dependencies import get_current_user
from app.config import get_settings
from app.models.user import User

router = APIRouter(prefix="/api/chats/{chat_id}/chat", tags=["llm"])
settings = get_settings()

async def get_redis():
    return aioredis.from_url(settings.REDIS_URL)

@router.post("/stream")
async def stream_llm(chat_id: int, request: Request, db: AsyncSession = Depends(get_db_session), user: User = Depends(get_current_user)):
    chat = await get_chat(db, chat_id, user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    body = await request.json()
    user_message = body.get("message", "").strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    await create_message(db, chat_id, "user", user_message)
    
    prompt = f"User: {user_message}\nAssistant:"
    
    async def event_generator():
        assistant_response = ""
        async for token in llm_service.generate_stream(prompt):
            assistant_response += token
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps({'token': token})}\n\n"
            await asyncio.sleep(0)
        
        await create_message(db, chat_id, "assistant", assistant_response)
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")