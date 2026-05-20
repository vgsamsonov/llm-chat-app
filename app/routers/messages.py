from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_session
from app.schemas.message import MessageCreate, MessageResponse
from app.services.message_service import create_message, get_chat_messages
from app.services.chat_service import get_chat
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/chats/{chat_id}/messages", tags=["messages"])

@router.post("", response_model=MessageResponse)
async def add_message(chat_id: int, msg_data: MessageCreate, db: AsyncSession = Depends(get_db_session), user: User = Depends(get_current_user)):
    chat = await get_chat(db, chat_id, user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    msg = await create_message(db, chat_id, "user", msg_data.content)
    return msg

@router.get("", response_model=list[MessageResponse])
async def list_messages(chat_id: int, db: AsyncSession = Depends(get_db_session), user: User = Depends(get_current_user)):
    chat = await get_chat(db, chat_id, user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return await get_chat_messages(db, chat_id)