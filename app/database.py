"""Database models and connection management using SQLAlchemy."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Boolean,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import (
    declarative_base,
    relationship,
    sessionmaker,
    Session,
)

# Database URLs
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://langchain:langchain_secret@localhost:5432/langchain_proxy"
)
DATABASE_URL_SYNC = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://langchain:langchain_secret@localhost:5432/langchain_proxy"
)

# Create engines
async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)
sync_engine = create_engine(DATABASE_URL_SYNC, echo=False, future=True)

# Session factories
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)
SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)

# Base class for models
Base = declarative_base()


class CustomModelDB(Base):
    """Database model for custom model configurations."""
    
    __tablename__ = "custom_models"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(64), nullable=False, unique=True, index=True)
    version = Column(String(20), nullable=False, default="1.0.0")
    enabled = Column(Boolean, nullable=False, default=True)
    base_model = Column(String(255), nullable=True)
    model_params = Column(JSON, nullable=False, default=dict)
    
    # RAG settings stored as JSON
    rag_settings = Column(JSON, nullable=False, default=dict)
    
    # Tool names stored as JSON array
    tool_names = Column(JSON, nullable=False, default=list)
    
    # Active versions stored as JSON array
    active_versions = Column(JSON, nullable=False, default=list)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    versions = relationship(
        "ModelVersionDB",
        back_populates="model",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    def __repr__(self):
        return f"<CustomModelDB(id={self.id}, name={self.name}, version={self.version})>"


class ModelVersionDB(Base):
    """Database model for model version history."""
    
    __tablename__ = "model_versions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(36), ForeignKey("custom_models.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(20), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    base_model = Column(String(255), nullable=True)
    model_params = Column(JSON, nullable=False, default=dict)
    rag_settings = Column(JSON, nullable=False, default=dict)
    tool_names = Column(JSON, nullable=False, default=list)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    model = relationship("CustomModelDB", back_populates="versions")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("model_id", "version", name="uq_model_version"),
        Index("ix_model_versions_model_id", "model_id"),
    )
    
    def __repr__(self):
        return f"<ModelVersionDB(model_id={self.model_id}, version={self.version})>"


class ActiveModelDB(Base):
    """Database model for tracking active models."""
    
    __tablename__ = "active_models"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(36), ForeignKey("custom_models.id", ondelete="CASCADE"), nullable=False, unique=True)
    priority = Column(Integer, nullable=False, default=0)  # Lower = higher priority
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_active_models_priority", "priority"),
    )
    
    def __repr__(self):
        return f"<ActiveModelDB(model_id={self.model_id}, priority={self.priority})>"


class ToolDB(Base):
    """Database model for custom tools with Python function code."""
    
    __tablename__ = "tools"
    
    id = Column(String(64), primary_key=True)
    name = Column(String(64), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(64), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    config = Column(JSON, nullable=False, default=dict)  # Tool-specific configuration
    # Python function code for custom tools
    function_code = Column(Text, nullable=True)  # Python code that defines the tool function
    parameters = Column(JSON, nullable=True)  # JSON schema for function parameters
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ToolDB(id={self.id}, name={self.name})>"


class SettingDB(Base):
    """Database model for key-value settings storage."""
    
    __tablename__ = "settings"
    
    key = Column(String(255), primary_key=True)
    value = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SettingDB(key={self.key})>"


# Database initialization functions
def init_db_sync():
    """Initialize database tables synchronously."""
    Base.metadata.create_all(bind=sync_engine)
    print("Database tables created successfully.")


async def init_db_async():
    """Initialize database tables asynchronously."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully (async).")


def get_sync_session() -> Session:
    """Get a synchronous database session."""
    return SyncSessionLocal()


async def get_async_session():
    """Get an asynchronous database session."""
    async with AsyncSessionLocal() as session:
        yield session


# Helper functions for converting between DB models and Pydantic models
def db_model_to_dict(db_model: CustomModelDB) -> Dict[str, Any]:
    """Convert a CustomModelDB to a dictionary."""
    return {
        "id": db_model.id,
        "name": db_model.name,
        "version": db_model.version,
        "enabled": db_model.enabled,
        "base_model": db_model.base_model,
        "model_params": db_model.model_params or {},
        "rag_settings": db_model.rag_settings or {},
        "tool_names": db_model.tool_names or [],
        "active_versions": db_model.active_versions or [],
        "created_at": db_model.created_at.isoformat() + "Z" if db_model.created_at else None,
        "updated_at": db_model.updated_at.isoformat() + "Z" if db_model.updated_at else None,
        "version_history": {
            v.version: {
                "version": v.version,
                "enabled": v.enabled,
                "base_model": v.base_model,
                "model_params": v.model_params or {},
                "rag_settings": v.rag_settings or {},
                "tool_names": v.tool_names or [],
                "description": v.description,
                "created_at": v.created_at.isoformat() + "Z" if v.created_at else None,
            }
            for v in db_model.versions
        } if db_model.versions else {},
    }


def db_version_to_dict(db_version: ModelVersionDB) -> Dict[str, Any]:
    """Convert a ModelVersionDB to a dictionary."""
    return {
        "version": db_version.version,
        "enabled": db_version.enabled,
        "base_model": db_version.base_model,
        "model_params": db_version.model_params or {},
        "rag_settings": db_version.rag_settings or {},
        "tool_names": db_version.tool_names or [],
        "description": db_version.description,
        "created_at": db_version.created_at.isoformat() + "Z" if db_version.created_at else None,
    }
