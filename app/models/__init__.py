from sqlalchemy.orm import declarative_base

Base = declarative_base()

from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message