from sqlalchemy import Column, String, Enum, ForeignKey, DateTime, Text, Boolean, UniqueConstraint, Integer, Numeric, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.init_engine import Base
import enum
import secrets
import string

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
    school = Column(String(255), nullable=True)  # School name for teachers
    pin_code = Column(String(4), nullable=True)  # PIN for anonymous students
    pin_reset_required = Column(Boolean, default=False)  # Flag to force PIN reset

    # Relationships
    owned_classes = relationship("Class", back_populates="owner")
    class_memberships = relationship("ClassMember", back_populates="user")

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
    class_id = Column(String(36), ForeignKey("class.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(64), ForeignKey("user.user_id"), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    class_obj = relationship("Class", back_populates="members")
    user = relationship("User", back_populates="class_memberships")

def generate_passphrase(length=8):
    """Generate an easy-to-type unique passphrase"""
    # Use only letters and numbers, avoiding confusing characters
    alphabet = string.ascii_uppercase + string.digits
    # Remove confusing characters: 0, O, 1, I, L
    alphabet = alphabet.replace('0', '').replace('O', '').replace('1', '').replace('I', '').replace('L', '')

    while True:
        passphrase = ''.join(secrets.choice(alphabet) for _ in range(length))
        # Ensure it's not all the same character
        if len(set(passphrase)) > 1:
            return passphrase

def generate_pin_code():
    """Generate a 4-digit PIN code"""
    return ''.join(secrets.choice(string.digits) for _ in range(4))

class AnonymousStudent(Base):
    __tablename__ = "anonymous_students"

    student_id = Column(String(255), primary_key=True)
    class_id = Column(String(36), ForeignKey("class.id", ondelete="CASCADE"), nullable=False)
    first_name = Column(String(50), nullable=False)
    pin_code = Column(String(4), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    class_obj = relationship("Class", backref="anonymous_students")

    # Ensure unique combination of class_id and first_name
    __table_args__ = (
        UniqueConstraint('class_id', 'first_name', name='unique_name_per_classroom'),
    )

class Device(Base):
    __tablename__ = "devices"

    id = Column(String(36), primary_key=True)  # UUID
    mac_address = Column(String(17), unique=True, nullable=False)
    nickname = Column(String(50), nullable=False)
    user_id = Column(String(64), ForeignKey("user.user_id"), nullable=False)
    is_active = Column(Boolean, default=False)
    battery_level = Column(Integer, default=0)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="devices")
    assignments = relationship("DeviceAssignment", back_populates="device", cascade="all, delete-orphan")
    data = relationship("DeviceData", back_populates="device", cascade="all, delete-orphan")

    # Ensure unique nickname per user
    __table_args__ = (
        UniqueConstraint('user_id', 'nickname', name='unique_nickname_per_user'),
    )

class DeviceAssignment(Base):
    __tablename__ = "device_assignments"

    id = Column(String(36), primary_key=True)  # UUID
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=False)
    classroom_id = Column(String(36), ForeignKey("class.id", ondelete="CASCADE"), nullable=False)
    assignment_type = Column(String(20), nullable=False)  # 'unassigned', 'student', 'group'
    assignment_id = Column(String(36), nullable=True)  # student_id or group_id
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    device = relationship("Device", back_populates="assignments")
    classroom = relationship("Class", backref="device_assignments")

    # Ensure one assignment per device per classroom
    __table_args__ = (
        UniqueConstraint('device_id', 'classroom_id', name='unique_device_classroom_assignment'),
    )

class Group(Base):
    __tablename__ = "groups"

    id = Column(String(36), primary_key=True)  # UUID
    classroom_id = Column(String(36), ForeignKey("class.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    icon = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    classroom = relationship("Class", backref="groups")
    memberships = relationship("GroupMembership", back_populates="group", cascade="all, delete-orphan")

class GroupMembership(Base):
    __tablename__ = "group_memberships"

    id = Column(String(36), primary_key=True)  # UUID
    group_id = Column(String(36), ForeignKey("groups.id"), nullable=False)
    student_id = Column(String(255), nullable=False)  # Can be user_id or anonymous student_id
    student_type = Column(String(20), nullable=False)  # 'registered' or 'anonymous'
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    group = relationship("Group", back_populates="memberships")

    # Ensure one group per student
    __table_args__ = (
        UniqueConstraint('student_id', 'student_type', name='unique_student_group'),
    )

class DeviceData(Base):
    __tablename__ = "device_data"

    id = Column(String(36), primary_key=True)  # UUID
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    temperature = Column(Numeric(5, 2), nullable=True)  # Temperature in Celsius
    humidity = Column(Numeric(5, 2), nullable=True)    # Humidity percentage
    light = Column(Numeric(8, 2), nullable=True)       # Light level in lux
    sound = Column(Numeric(5, 2), nullable=True)       # Sound level in dB
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    device = relationship("Device", back_populates="data")

    # Index for efficient querying
    __table_args__ = (
        Index('idx_device_timestamp', 'device_id', 'timestamp'),
    )