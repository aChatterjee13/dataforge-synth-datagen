from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Enum as SQLEnum, Boolean
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime, timezone
import enum
import os

SQLALCHEMY_DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./dataforge.db')

connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

class JobStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    synthetic_path = Column(String, nullable=True)
    status = Column(SQLEnum(JobStatusEnum), default=JobStatusEnum.PENDING)
    progress = Column(Float, default=0.0)
    message = Column(String, default="Job created")
    error = Column(Text, nullable=True)

    # Metadata
    rows_original = Column(Integer)
    columns = Column(Integer)
    rows_generated = Column(Integer, nullable=True)

    # Configuration
    model_type = Column(String)
    epochs = Column(Integer)
    batch_size = Column(Integer)
    num_rows = Column(Integer)
    config_json = Column(Text, nullable=True)  # Store full config including ml_target_variables

    # Privacy configuration
    privacy_enabled = Column(Boolean, default=False)
    privacy_epsilon = Column(Float, nullable=True)
    privacy_delta = Column(Float, nullable=True)
    privacy_mechanism = Column(String, nullable=True)

    # Validation metrics
    quality_score = Column(Float, nullable=True)
    privacy_score = Column(Float, nullable=True)
    correlation_score = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)


class Preset(Base):
    """Configuration presets for generation (Feature 5)"""
    __tablename__ = "presets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    config_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class APIKey(Base):
    """API keys for webhook/API-first mode (Feature 8)"""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key_hash = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used = Column(DateTime, nullable=True)


# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
