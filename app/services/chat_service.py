from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.chat import Chat

async def create_chat(db: AsyncSession, user_id: int, title: str) -> Chat:
    chat = Chat(user_id=user_id, title=title)
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return chat

async def get_user_chats(db: AsyncSession, user_id: int) -> list:
    result = await db.execute(select(Chat).where(Chat.user_id == user_id).order_by(Chat.updated_at.desc()))
    return result.scalars().all()

async def get_chat(db: AsyncSession, chat_id: int, user_id: int) -> Chat:
    result = await db.execute(select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id))
    return result.scalar_one_or_none()