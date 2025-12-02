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


class KnowledgeBaseDB(Base):
    """Database model for knowledge bases."""
    
    __tablename__ = "knowledge_bases"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(64), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    collection = Column(String(255), nullable=False, unique=True)  # Qdrant collection name
    embedding_model = Column(String(255), nullable=True)  # Optional per-KB embedding model
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<KnowledgeBaseDB(id={self.id}, name={self.name}, collection={self.collection})>"


class SettingDB(Base):
    """Database model for key-value settings storage."""
    
    __tablename__ = "settings"
    
    key = Column(String(255), primary_key=True)
    value = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SettingDB(key={self.key})>"


class ChatLogDB(Base):
    """Database model for chat interaction logs - useful for debugging and analytics."""
    
    __tablename__ = "chat_logs"
    
    id = Column(String(36), primary_key=True)  # UUID
    chat_id = Column(String(64), nullable=False, index=True)  # OpenAI-style chat ID (chatcmpl-xxx)
    model_name = Column(String(255), nullable=False, index=True)  # Model used
    model_config_id = Column(String(36), nullable=True)  # Custom model config ID if any
    kb_id = Column(String(36), nullable=True)  # Knowledge base ID if used
    
    # Request details
    request_messages = Column(JSON, nullable=False)  # Original request messages
    system_message = Column(Text, nullable=True)  # System message if any
    user_message = Column(Text, nullable=True)  # Last user message
    
    # Response details
    response_content = Column(Text, nullable=True)  # Final response content
    response_messages = Column(JSON, nullable=True)  # All response messages including tool calls
    
    # Tool usage
    tools_used = Column(JSON, nullable=True)  # List of tools that were called
    tool_calls = Column(JSON, nullable=True)  # Detailed tool call information
    
    # RAG context
    rag_context = Column(Text, nullable=True)  # Retrieved RAG context if any
    rag_documents = Column(JSON, nullable=True)  # Document sources used
    
    # Metrics
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    
    # Status and errors
    status = Column(String(20), nullable=False, default="success")  # success, error, timeout
    error_message = Column(Text, nullable=True)
    error_type = Column(String(100), nullable=True)
    
    # Stream info
    is_stream = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("ix_chat_logs_created_at_desc", created_at.desc()),
        Index("ix_chat_logs_model_created", model_name, created_at.desc()),
        Index("ix_chat_logs_status", status),
    )
    
    def __repr__(self):
        return f"<ChatLogDB(id={self.id}, chat_id={self.chat_id}, model={self.model_name})>"


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


class ChatLogService:
    """Service for managing chat logs."""
    
    @staticmethod
    def create_log(
        chat_id: str,
        model_name: str,
        request_messages: List[Dict[str, Any]],
        is_stream: bool = False,
        model_config_id: Optional[str] = None,
        kb_id: Optional[str] = None,
        system_message: Optional[str] = None,
        user_message: Optional[str] = None,
    ) -> ChatLogDB:
        """Create a new chat log entry."""
        import uuid
        log = ChatLogDB(
            id=str(uuid.uuid4()),
            chat_id=chat_id,
            model_name=model_name,
            model_config_id=model_config_id,
            kb_id=kb_id,
            request_messages=request_messages,
            system_message=system_message,
            user_message=user_message,
            is_stream=is_stream,
            status="pending",
        )
        session = get_sync_session()
        try:
            session.add(log)
            session.commit()
            session.refresh(log)
            return log
        finally:
            session.close()
    
    @staticmethod
    def update_log(
        log_id: str,
        response_content: Optional[str] = None,
        response_messages: Optional[List[Dict[str, Any]]] = None,
        tools_used: Optional[List[str]] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        rag_context: Optional[str] = None,
        rag_documents: Optional[List[Dict[str, Any]]] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        latency_ms: Optional[int] = None,
        status: Optional[str] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
    ) -> Optional[ChatLogDB]:
        """Update an existing chat log entry."""
        session = get_sync_session()
        try:
            log = session.query(ChatLogDB).filter(ChatLogDB.id == log_id).first()
            if not log:
                return None
            
            if response_content is not None:
                log.response_content = response_content
            if response_messages is not None:
                log.response_messages = response_messages
            if tools_used is not None:
                log.tools_used = tools_used
            if tool_calls is not None:
                log.tool_calls = tool_calls
            if rag_context is not None:
                log.rag_context = rag_context
            if rag_documents is not None:
                log.rag_documents = rag_documents
            if prompt_tokens is not None:
                log.prompt_tokens = prompt_tokens
            if completion_tokens is not None:
                log.completion_tokens = completion_tokens
            if total_tokens is not None:
                log.total_tokens = total_tokens
            if latency_ms is not None:
                log.latency_ms = latency_ms
            if status is not None:
                log.status = status
            if error_message is not None:
                log.error_message = error_message
            if error_type is not None:
                log.error_type = error_type
            
            session.commit()
            session.refresh(log)
            return log
        finally:
            session.close()
    
    @staticmethod
    def get_log(log_id: str) -> Optional[ChatLogDB]:
        """Get a chat log by ID."""
        session = get_sync_session()
        try:
            return session.query(ChatLogDB).filter(ChatLogDB.id == log_id).first()
        finally:
            session.close()
    
    @staticmethod
    def get_log_by_chat_id(chat_id: str) -> Optional[ChatLogDB]:
        """Get a chat log by chat completion ID."""
        session = get_sync_session()
        try:
            return session.query(ChatLogDB).filter(ChatLogDB.chat_id == chat_id).first()
        finally:
            session.close()
    
    @staticmethod
    def list_logs(
        model_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ChatLogDB]:
        """List chat logs with optional filters."""
        session = get_sync_session()
        try:
            query = session.query(ChatLogDB)
            if model_name:
                query = query.filter(ChatLogDB.model_name == model_name)
            if status:
                query = query.filter(ChatLogDB.status == status)
            query = query.order_by(ChatLogDB.created_at.desc())
            query = query.offset(offset).limit(limit)
            return query.all()
        finally:
            session.close()
    
    @staticmethod
    def delete_log(log_id: str) -> bool:
        """Delete a chat log by ID."""
        session = get_sync_session()
        try:
            log = session.query(ChatLogDB).filter(ChatLogDB.id == log_id).first()
            if not log:
                return False
            session.delete(log)
            session.commit()
            return True
        finally:
            session.close()
    
    @staticmethod
    def clear_logs(before_date: Optional[datetime] = None) -> int:
        """Clear chat logs, optionally before a specific date."""
        session = get_sync_session()
        try:
            query = session.query(ChatLogDB)
            if before_date:
                query = query.filter(ChatLogDB.created_at < before_date)
            count = query.delete()
            session.commit()
            return count
        finally:
            session.close()
    
    @staticmethod
    def log_to_dict(log: ChatLogDB) -> Dict[str, Any]:
        """Convert a ChatLogDB to a dictionary."""
        return {
            "id": log.id,
            "chat_id": log.chat_id,
            "model_name": log.model_name,
            "model_config_id": log.model_config_id,
            "kb_id": log.kb_id,
            "request_messages": log.request_messages,
            "system_message": log.system_message,
            "user_message": log.user_message,
            "response_content": log.response_content,
            "response_messages": log.response_messages,
            "tools_used": log.tools_used,
            "tool_calls": log.tool_calls,
            "rag_context": log.rag_context,
            "rag_documents": log.rag_documents,
            "prompt_tokens": log.prompt_tokens,
            "completion_tokens": log.completion_tokens,
            "total_tokens": log.total_tokens,
            "latency_ms": log.latency_ms,
            "status": log.status,
            "error_message": log.error_message,
            "error_type": log.error_type,
            "is_stream": log.is_stream,
            "created_at": log.created_at.isoformat() + "Z" if log.created_at else None,
        }
