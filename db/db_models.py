from sqlalchemy import Column, String, Enum
from db.init_engine import Base
import enum

class UserType(str, enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"

class User(Base):
    __tablename__ = "user"

    user_id = Column(String(64), primary_key=True, unique=True)  # Can be email or username
    first_name = Column(String(32), nullable=False)
    last_name = Column(String(32), nullable=False)
    password = Column(String(255), nullable=False)
    user_type = Column(Enum(UserType), nullable=False)