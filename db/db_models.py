from sqlalchemy import Column, String, Float, Integer
from db.init_engine import Base

class student(Base):
    __tablename__ = 'student'
    user_name = Column(String(32), primary_key=True, unique=True)
    first_name = Column(String(32), nullable=False)
    last_name = Column(String(32), nullable=False)
    password = Column(String(255), nullable=False)

class teacher(Base):
    __tablename__ = 'teacher'
    email = Column(String(64), primary_key=True, unique=True)
    first_name = Column(String(32), nullable=False)
    last_name = Column(String(32), nullable=False)
    password = Column(String(255), nullable=False)