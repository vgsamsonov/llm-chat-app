# app/database.py — SYNC VERSION (psycopg2)
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from sqlalchemy.pool import StaticPool
from app.config import get_settings

settings = get_settings()

# Remove '+psycopg2' from URL for actual connection string
db_url = settings.DATABASE_URL.replace('+psycopg2', '')

# Create sync engine with connection pooling settings for stability
engine = create_engine(
    db_url,
    echo=True,
    pool_pre_ping=True,           # Check connection before using
    pool_recycle=3600,            # Recycle connections after 1 hour
    connect_args={"connect_timeout": 10}  # 10 second timeout
)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()

def get_db_session():
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """Create all tables (use Alembic for migrations instead)"""
    Base.metadata.create_all(bind=engine)

def close_db():
    """Cleanup function"""
    SessionLocal.remove()
    engine.dispose()