# app/main.py — UPDATED STARTUP
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import close_db
from app.routers import auth, chats, messages, llm

settings = get_settings()

app = FastAPI(title="LLM Chat API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    # Database tables should be created via Alembic, not auto-init
    print("Application starting...")
    
    try:
        from app.services.llm_service import llm_service
        llm_service.initialize()
        print("LLM model loaded successfully")
    except FileNotFoundError as e:
        print(f"{e}. LLM features disabled until model is provided.")
    except Exception as e:
        print(f"Could not initialize LLM: {e}")

@app.on_event("shutdown")
async def shutdown():
    from app.database import close_db
    close_db()
    print("Database connections closed")

app.include_router(auth.router)
app.include_router(chats.router)
app.include_router(messages.router)
app.include_router(llm.router)

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}