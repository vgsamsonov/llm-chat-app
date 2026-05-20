import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.security import create_access_token, create_refresh_token
from app.config import get_settings
import redis.asyncio as aioredis
import json

settings = get_settings()

async def exchange_code_for_token(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            }
        )
        return resp.json()

async def get_github_user(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        )
        return resp.json()

async def authenticate_or_create(db: AsyncSession, redis: aioredis.Redis, github_data: dict) -> dict:
    github_id = str(github_data["id"])
    result = await db.execute(select(User).where(User.github_id == github_id))
    user = result.scalar_one_or_none()
    
    if not user:
        username = github_data.get("login", f"github_user_{github_id}")
        email = github_data.get("email")
        user = User(username=username, email=email, github_id=github_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    await redis.setex(
        f"refresh_token:{refresh_token}",
        settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        json.dumps({"user_id": user.id})
    )
    
    return {"user": user, "access_token": access_token, "refresh_token": refresh_token}