from sqlalchemy import Column, String, Enum, Integer
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

class Class(Base):
    __tablename__ = "class"
    class_id = Column(Integer, primary_key=True, nullable=False)
    class_name = Column(String(64), nullable=False)
    class_owner = Column(String(64), nullable=False)
    class_description = Column(String(255))  # Just a text field, not unique or PK

class Tag(Base):
    __tablename__ = "tag"
    tag_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    tag_name = Column(String(32), nullable=False)
    class_id = Column(Integer, nullable=False)