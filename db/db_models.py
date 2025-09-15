from sqlalchemy import Column, String, Enum, ForeignKey, DateTime, Text, Boolean, Integer, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
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
    pin_code = Column(String(4), nullable=True)  # PIN for anonymous students
    pin_reset_required = Column(Boolean, default=False)  # Flag to force PIN reset

    # Relationships
    owned_classes = relationship("Class", back_populates="owner")
    class_memberships = relationship("ClassMember", back_populates="user")

# Class model
class Class(Base):
    __tablename__ = "class"

    id = Column(String(36), primary_key=True)  # UUID
    name = Column(String(100), nullable=False)
    subject = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    passphrase = Column(String(12), unique=True, nullable=False)  # Easy to type passphrase
    owner_id = Column(String(64), ForeignKey("user.user_id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="owned_classes")
    members = relationship("ClassMember", back_populates="class_obj", cascade="all, delete-orphan")

class ClassMember(Base):
    __tablename__ = "class_member"

    id = Column(String(36), primary_key=True)  # UUID
    class_id = Column(String(36), ForeignKey("class.id"), nullable=False)
    user_id = Column(String(64), ForeignKey("user.user_id"), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    class_obj = relationship("Class", back_populates="members")
    user = relationship("User", back_populates="class_memberships")
class Device(Base):
    __tablename__ = "device"
    mac_addr = Column(String(12), primary_key=True)

    # Relationship to Data
    data_entries = relationship("Data", back_populates="device_obj", cascade="all, delete-orphan")
class Data(Base):
    __tablename__ = "data"
    
    entry_id = Column(Integer, autoincrement=True, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    type = Column(String(32), nullable=False)
    value = Column(Float, nullable=False)
    mac_addr = Column(String(6), ForeignKey("device.mac_addr"), nullable=False)

    # Relationship
    device_obj = relationship("Device", back_populates="data_entries")