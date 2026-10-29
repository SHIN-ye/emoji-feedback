from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import declarative_base
Base=declarative_base()
def now(): return datetime.now(timezone.utc).replace(tzinfo=None)
class User(Base):
    __tablename__='users'
    id=Column(Integer,primary_key=True)
    username=Column(String(50),unique=True,nullable=False)
    password_hash=Column(String(256),nullable=False)
    role=Column(String(16),nullable=False)
    email=Column(String(254),default='')
    status=Column(String(16),default='active',nullable=False)
    created_at=Column(DateTime,default=now,nullable=False)
    __table_args__=(CheckConstraint("role IN ('student','teacher','admin')"),CheckConstraint("status IN ('active','disabled')"))
class Course(Base):
    __tablename__='courses'
    id=Column(Integer,primary_key=True)
    name=Column(String(120),nullable=False)
    teacher_id=Column(Integer,ForeignKey('users.id'),nullable=False)
class ClassSession(Base):
    __tablename__='class_sessions'
    id=Column(Integer,primary_key=True)
    course_id=Column(Integer,ForeignKey('courses.id'),nullable=False)
    class_name=Column(String(80),nullable=False)
    room=Column(String(80),default='')
    start_time=Column(DateTime,nullable=False)
    end_time=Column(DateTime,nullable=False)
    __table_args__=(CheckConstraint('end_time > start_time'),)
class ScheduleUser(Base):
    __tablename__='schedule_users'
    id=Column(Integer,primary_key=True)
    session_id=Column(Integer,ForeignKey('class_sessions.id'),nullable=False)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False)
    scheduled_at=Column(DateTime,default=now,nullable=False)
    __table_args__=(UniqueConstraint('session_id','user_id'),)
class EmojiRecord(Base):
    __tablename__='emoji_records'
    id=Column(Integer,primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=True)
    session_id=Column(Integer,ForeignKey('class_sessions.id'),nullable=False,index=True)
    emoji=Column(String(20),nullable=False)
    timestamp=Column(DateTime,default=now,nullable=False,index=True)
    source=Column(String(10),nullable=False)
    confidence=Column(Float,nullable=True)
    device_id=Column(String(100),default='')
    event_id=Column(String(100),unique=True,nullable=True)
    __table_args__=(CheckConstraint("emoji IN ('happy','neutral','sad','angry','surprise','fear','disgust')"),CheckConstraint("source IN ('MANUAL','AI')"),CheckConstraint("source != 'AI' OR (confidence IS NOT NULL AND confidence >= 0 AND confidence <= 1)"))
class AuthSession(Base):
    __tablename__='auth_sessions'
    token_hash=Column(String(64),primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False)
    expires_at=Column(DateTime,nullable=False)
class AuditLog(Base):
    __tablename__='audit_logs'
    id=Column(Integer,primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=True)
    action=Column(String(120),nullable=False)
    timestamp=Column(DateTime,default=now,nullable=False)
