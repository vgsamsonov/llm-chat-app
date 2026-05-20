from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.message import Message

async def create_message(db: AsyncSession, chat_id: int, role: str, content: str) -> Message:
    msg = Message(chat_id=chat_id, role=role, content=content)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg

async def get_chat_messages(db: AsyncSession, chat_id: int) -> list:
    result = await db.execute(select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.asc()))
    return result.scalars().all()