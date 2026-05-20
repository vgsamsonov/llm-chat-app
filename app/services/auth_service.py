from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.config import get_settings
import redis.asyncio as aioredis
import json

settings = get_settings()

async def register_user(db: AsyncSession, username: str, email: str, password: str) -> dict:
    existing = await db.execute(select(User).where((User.username == username) | (User.email == email)))
    if existing.scalar_one_or_none():
        return {"error": "Username or email already exists"}
    
    hashed = hash_password(password)
    new_user = User(username=username, email=email, hashed_password=hashed)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"user": new_user}

async def login_user(db: AsyncSession, redis: aioredis.Redis, username: str, password: str) -> dict:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        return {"error": "Invalid credentials"}
    
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    await redis.setex(
        f"refresh_token:{refresh_token}",
        settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        json.dumps({"user_id": user.id})
    )
    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

async def refresh_access_token(db: AsyncSession, redis: aioredis.Redis, refresh_token: str) -> dict:
    session_data = await redis.get(f"refresh_token:{refresh_token}")
    if not session_data:
        return {"error": "Invalid or expired refresh token"}
    
    payload = json.loads(session_data)
    result = await db.execute(select(User).where(User.id == int(payload["user_id"])))
    user = result.scalar_one_or_none()
    if not user:
        return {"error": "User not found"}
    
    await redis.delete(f"refresh_token:{refresh_token}")
    
    new_access = create_access_token({"sub": str(user.id)})
    new_refresh = create_refresh_token({"sub": str(user.id)})
    
    await redis.setex(
        f"refresh_token:{new_refresh}",
        settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        json.dumps({"user_id": user.id})
    )
    
    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}