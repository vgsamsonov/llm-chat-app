from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
import json
from app.database import get_db_session
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import register_user, login_user, refresh_access_token
from app.services.github_oauth_service import exchange_code_for_token, get_github_user, authenticate_or_create
from app.dependencies import get_current_user
from app.models.user import User
from app.config import get_settings, get_redis_client

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()

@router.post("/register", response_model=dict)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db_session)):
    result = await register_user(db, req.username, req.email, req.password)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"message": "User registered successfully", "user": UserResponse.model_validate(result["user"])}

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db_session)):
    redis = get_redis_client()
    result = await login_user(db, redis, req.username, req.password)
    if "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])
    return result

@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: dict, db: AsyncSession = Depends(get_db_session)):
    redis = get_redis_client()
    result = await refresh_access_token(db, redis, req.get("refresh_token", ""))
    if "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])
    return result

@router.get("/github")
async def github_login():
    auth_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={settings.GITHUB_CLIENT_ID}&"
        f"redirect_uri={settings.GITHUB_REDIRECT_URI}&"
        f"scope=user:email"
    )
    return RedirectResponse(url=auth_url)

@router.get("/github/callback")
async def github_callback(code: str = Query(...), db: AsyncSession = Depends(get_db_session)):
    token_data = await exchange_code_for_token(code)
    if "error" in token_data:
        raise HTTPException(status_code=400, detail="GitHub OAuth failed")
    
    github_user = await get_github_user(token_data["access_token"])
    redis = get_redis_client()
    result = await authenticate_or_create(db, redis, github_user)
    
    redirect_url = f"{settings.FRONTEND_URL}/auth/callback?access_token={result['access_token']}&refresh_token={result['refresh_token']}"
    return RedirectResponse(url=redirect_url)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user






