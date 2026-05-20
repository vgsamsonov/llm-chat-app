from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_session
from app.schemas.chat import ChatCreate, ChatResponse
from app.services.chat_service import create_chat, get_user_chats, get_chat
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/chats", tags=["chats"])

@router.post("", response_model=ChatResponse)
async def create_new_chat(chat_data: ChatCreate, db: AsyncSession = Depends(get_db_session), user: User = Depends(get_current_user)):
    chat = await create_chat(db, user.id, chat_data.title)
    return chat

@router.get("", response_model=list[ChatResponse])
async def list_chats(db: AsyncSession = Depends(get_db_session), user: User = Depends(get_current_user)):
    return await get_user_chats(db, user.id)

@router.get("/{chat_id}", response_model=ChatResponse)
async def get_single_chat(chat_id: int, db: AsyncSession = Depends(get_db_session), user: User = Depends(get_current_user)):
    chat = await get_chat(db, chat_id, user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat