"""Admin configuration manager for custom models and tool settings with PostgreSQL persistence."""
from __future__ import annotations

import os
import re
import uuid
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload

from langchain_proxy.server.database import (
    CustomModelDB,
    ModelVersionDB,
    ActiveModelDB,
    ToolDB,
    KnowledgeBaseDB,
    get_sync_session,
    init_db_sync,
    db_model_to_dict,
    db_version_to_dict,
)

# Built-in tools that are always available (implemented in code)
BUILTIN_TOOL_NAMES = ["get_datetime", "search_knowledge_base"]

# This will be dynamically populated with builtin + database tools
AVAILABLE_TOOL_NAMES = BUILTIN_TOOL_NAMES.copy()

# Generate a consistent default model ID using hex format
def _generate_hex_id() -> str:
    """Generate an 8-character hex ID."""
    return uuid.uuid4().hex[:8]

# Default IDs (these are fixed values to ensure consistency)
DEFAULT_MODEL_ID = "a1b2c3d4"  # Fixed default model ID in hex format
DEFAULT_KB_ID = "e5f6a7b8"  # Fixed default KB ID in hex format

# Whitelist of allowed model_params keys for safety
ALLOWED_MODEL_PARAMS = ["temperature", "max_tokens", "top_p", "stop", "presence_penalty", "frequency_penalty"]

# Model name validation pattern: lowercase letters, numbers, underscore, hyphen
MODEL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
MODEL_NAME_MIN_LENGTH = 2
MODEL_NAME_MAX_LENGTH = 64

# Version validation pattern: semantic versioning (e.g., 1.0.0, 2.1.3)
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def validate_model_name(name: str) -> str:
    """Validate model name format.
    
    Rules:
    - Must start with a lowercase letter
    - Can contain lowercase letters, numbers, underscores, hyphens
    - Length between 2-64 characters
    """
    if not name:
        raise ValueError("Model name is required.")
    
    name = name.strip().lower()
    
    if len(name) < MODEL_NAME_MIN_LENGTH:
        raise ValueError(f"Model name must be at least {MODEL_NAME_MIN_LENGTH} characters.")
    
    if len(name) > MODEL_NAME_MAX_LENGTH:
        raise ValueError(f"Model name must be at most {MODEL_NAME_MAX_LENGTH} characters.")
    
    if not MODEL_NAME_PATTERN.match(name):
        raise ValueError(
            "Model name must start with a letter and contain only lowercase letters (a-z), "
            "numbers (0-9), underscores (_), and hyphens (-)."
        )
    
    return name


def validate_version(version: str) -> str:
    """Validate semantic version format (e.g., 1.0.0)."""
    if not version:
        raise ValueError("Version is required.")
    
    version = version.strip()
    
    if not VERSION_PATTERN.match(version):
        raise ValueError("Version must follow semantic versioning format (e.g., 1.0.0, 2.1.3).")
    
    return version


def parse_model_identifier(identifier: str) -> Tuple[str, Optional[str]]:
    """Parse a model identifier that may include a version.
    
    Formats:
    - "model-name" -> ("model-name", None)
    - "model-name@1.0.0" -> ("model-name", "1.0.0")
    
    Returns (name, version) tuple.
    """
    if "@" in identifier:
        parts = identifier.split("@", 1)
        return parts[0], parts[1]
    return identifier, None


def compare_versions(v1: str, v2: str) -> int:
    """Compare two semantic versions.
    
    Returns:
    - -1 if v1 < v2
    - 0 if v1 == v2
    - 1 if v1 > v2
    """
    parts1 = [int(x) for x in v1.split(".")]
    parts2 = [int(x) for x in v2.split(".")]
    
    for p1, p2 in zip(parts1, parts2):
        if p1 < p2:
            return -1
        if p1 > p2:
            return 1
    return 0


class RagSettings(BaseModel):
    """RAG-specific settings that can vary per model."""

    enabled: bool = Field(True)
    top_k: int = Field(3, ge=1)
    collection: str = Field(default_factory=lambda: os.getenv("QDRANT_COLLECTION", "knowledge_base"))


class ModelVersionConfig(BaseModel):
    """Configuration for a specific version of a model."""
    
    version: str = Field(..., description="Semantic version (e.g., 1.0.0)")
    enabled: bool = Field(default=True, description="Whether this version is enabled for use")
    rag_settings: RagSettings = Field(default_factory=RagSettings)
    tool_names: List[str] = Field(default_factory=lambda: AVAILABLE_TOOL_NAMES.copy())
    base_model: Optional[str] = Field(default=None, description="Base LLM model identifier")
    model_params: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None, description="Version description/changelog")
    
    @field_validator('version')
    @classmethod
    def validate_version_format(cls, v: str) -> str:
        return validate_version(v)


class CustomModel(BaseModel):
    """Representation of a custom model configuration with version history."""

    id: str
    name: str
    version: str = Field(default="1.0.0", description="Current/latest semantic version")
    enabled: bool = Field(default=True)
    rag_settings: RagSettings = Field(default_factory=RagSettings)
    tool_names: List[str] = Field(default_factory=lambda: AVAILABLE_TOOL_NAMES.copy())
    base_model: Optional[str] = Field(default=None, description="Base LLM model identifier, e.g. 'gpt-oss:20b-cloud'. If None, uses server default.")
    model_params: Dict[str, Any] = Field(default_factory=dict, description="Model parameters like temperature, max_tokens, etc.")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp when model was created")
    updated_at: Optional[str] = Field(default=None, description="ISO timestamp when model was last updated")
    
    # Version history: maps version string to version config
    version_history: Dict[str, ModelVersionConfig] = Field(
        default_factory=dict, 
        description="History of all versions. Key is version string, value is version config."
    )
    # Which versions are currently active/enabled for client use
    active_versions: List[str] = Field(
        default_factory=list,
        description="List of version strings that are active for client use"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        return validate_model_name(v)


def _db_to_pydantic_model(db_model: CustomModelDB) -> CustomModel:
    """Convert a database model to a Pydantic model."""
    version_history = {}
    for v in db_model.versions:
        rag = v.rag_settings or {}
        version_history[v.version] = ModelVersionConfig(
            version=v.version,
            enabled=v.enabled,
            rag_settings=RagSettings(**rag) if rag else RagSettings(),
            tool_names=v.tool_names or AVAILABLE_TOOL_NAMES.copy(),
            base_model=v.base_model,
            model_params=v.model_params or {},
            created_at=v.created_at.isoformat() + "Z" if v.created_at else None,
            description=v.description,
        )
    
    rag_settings = db_model.rag_settings or {}
    
    return CustomModel(
        id=db_model.id,
        name=db_model.name,
        version=db_model.version,
        enabled=db_model.enabled,
        rag_settings=RagSettings(**rag_settings) if rag_settings else RagSettings(),
        tool_names=db_model.tool_names or AVAILABLE_TOOL_NAMES.copy(),
        base_model=db_model.base_model,
        model_params=db_model.model_params or {},
        created_at=db_model.created_at.isoformat() + "Z" if db_model.created_at else None,
        updated_at=db_model.updated_at.isoformat() + "Z" if db_model.updated_at else None,
        version_history=version_history,
        active_versions=db_model.active_versions or [],
    )


class ConfigStore:
    """Persistent store for custom models using PostgreSQL."""

    def __init__(self):
        self._lock = Lock()
        self._initialized = False
        self._initialize()

    def _initialize(self) -> None:
        """Initialize database and ensure default model exists."""
        if self._initialized:
            return
        
        # Initialize database tables
        init_db_sync()
        
        # Ensure at least one model and active model exist
        with get_sync_session() as session:
            # Check if any models exist
            result = session.execute(select(CustomModelDB).limit(1))
            existing_model = result.scalar_one_or_none()
            
            if not existing_model:
                # Create default model
                default_model = self._create_default_model_db(session)
                session.add(default_model)
                session.commit()
                
                # Set as active
                active = ActiveModelDB(model_id=default_model.id, priority=0)
                session.add(active)
                session.commit()
            else:
                # Ensure there's at least one active model
                active_result = session.execute(select(ActiveModelDB).limit(1))
                active_model = active_result.scalar_one_or_none()
                
                if not active_model:
                    # Get first model and make it active
                    active = ActiveModelDB(model_id=existing_model.id, priority=0)
                    session.add(active)
                    session.commit()
        
        self._initialized = True

    def _create_default_model_db(self, session) -> CustomModelDB:
        """Create default model database record."""
        now = datetime.utcnow()
        initial_version = "1.0.0"
        
        db_model = CustomModelDB(
            id=DEFAULT_MODEL_ID,
            name="default-model",
            version=initial_version,
            enabled=True,
            rag_settings={"enabled": True, "top_k": 3, "collection": os.getenv("QDRANT_COLLECTION", "knowledge_base")},
            tool_names=AVAILABLE_TOOL_NAMES.copy(),
            base_model=None,
            model_params={},
            active_versions=[initial_version],
            created_at=now,
            updated_at=now,
        )
        
        # Create initial version
        version_db = ModelVersionDB(
            model_id=DEFAULT_MODEL_ID,
            version=initial_version,
            enabled=True,
            rag_settings={"enabled": True, "top_k": 3, "collection": os.getenv("QDRANT_COLLECTION", "knowledge_base")},
            tool_names=AVAILABLE_TOOL_NAMES.copy(),
            base_model=None,
            model_params={},
            description="Initial version",
            created_at=now,
        )
        
        session.add(db_model)
        session.add(version_db)
        
        return db_model

    def list_models(self) -> List[CustomModel]:
        """List all custom models."""
        with get_sync_session() as session:
            result = session.execute(
                select(CustomModelDB).options(selectinload(CustomModelDB.versions))
            )
            db_models = result.scalars().all()
            return [_db_to_pydantic_model(m) for m in db_models]

    def get_model(self, model_id: str) -> Optional[CustomModel]:
        """Get a model by ID."""
        with get_sync_session() as session:
            result = session.execute(
                select(CustomModelDB)
                .options(selectinload(CustomModelDB.versions))
                .where(CustomModelDB.id == model_id)
            )
            db_model = result.scalar_one_or_none()
            if db_model:
                return _db_to_pydantic_model(db_model)
            return None

    def get_model_by_name(self, name: str) -> Optional[CustomModel]:
        """Find a custom model by its name (case-insensitive)."""
        with get_sync_session() as session:
            result = session.execute(
                select(CustomModelDB)
                .options(selectinload(CustomModelDB.versions))
                .where(CustomModelDB.name.ilike(name))
            )
            db_model = result.scalar_one_or_none()
            if db_model:
                return _db_to_pydantic_model(db_model)
            return None

    def get_model_by_name_and_version(self, name: str, version: str) -> Optional[Tuple[CustomModel, ModelVersionConfig]]:
        """Find a custom model and its specific version config."""
        model = self.get_model_by_name(name)
        if not model:
            return None
        
        if version in model.version_history:
            return (model, model.version_history[version])
        
        if version == model.version:
            config = ModelVersionConfig(
                version=model.version,
                enabled=model.enabled,
                rag_settings=model.rag_settings,
                tool_names=model.tool_names,
                base_model=model.base_model,
                model_params=model.model_params,
                created_at=model.created_at,
            )
            return (model, config)
        
        return None

    def resolve_model_identifier(self, identifier: str) -> Optional[Tuple[CustomModel, Optional[ModelVersionConfig]]]:
        """Resolve a model identifier (with optional version) to model and version config."""
        name, version = parse_model_identifier(identifier)
        model = self.get_model_by_name(name)
        
        if not model:
            model = self.get_model(identifier.split("@")[0] if "@" in identifier else identifier)
            if not model:
                return None
        
        if version:
            result = self.get_model_by_name_and_version(model.name, version)
            if result:
                return result
            return None
        
        return (model, None)

    @property
    def active_model_ids(self) -> List[str]:
        """Get list of active model IDs ordered by priority."""
        with get_sync_session() as session:
            result = session.execute(
                select(ActiveModelDB.model_id).order_by(ActiveModelDB.priority)
            )
            ids = [row[0] for row in result.fetchall()]
            
            if not ids:
                # Fallback: get first available model
                model_result = session.execute(select(CustomModelDB.id).limit(1))
                first_model = model_result.scalar_one_or_none()
                if first_model:
                    return [first_model]
            return ids

    @property
    def active_model_id(self) -> str:
        """Get the primary active model ID."""
        ids = self.active_model_ids
        return ids[0] if ids else DEFAULT_MODEL_ID

    def get_active_model(self) -> CustomModel:
        """Get the primary active model."""
        model = self.get_model(self.active_model_id)
        if model:
            return model
        # Fallback to creating default if something went wrong
        self._initialized = False
        self._initialize()
        return self.get_model(self.active_model_id)

    def create_model(
        self,
        name: str,
        enabled: bool = True,
        rag_settings: Optional[RagSettings] = None,
        tool_names: Optional[List[str]] = None,
        base_model: Optional[str] = None,
        model_params: Optional[Dict[str, Any]] = None,
        version: str = "1.0.0",
        description: Optional[str] = None,
    ) -> CustomModel:
        """Create a new custom model."""
        with self._lock:
            validated_name = validate_model_name(name)
            validated_version = validate_version(version)
            
            # Check for duplicate names
            existing = self.get_model_by_name(validated_name)
            if existing:
                raise ValueError(f"A model with name '{validated_name}' already exists.")
            
            tool_list = tool_names if tool_names is not None else AVAILABLE_TOOL_NAMES.copy()
            validated_tools = [tool for tool in tool_list if tool in AVAILABLE_TOOL_NAMES]
            if not validated_tools:
                raise ValueError("At least one valid tool name is required.")
            
            settings = rag_settings or RagSettings()
            safe_params = {}
            if model_params:
                safe_params = {k: v for k, v in model_params.items() if k in ALLOWED_MODEL_PARAMS}
            
            now = datetime.utcnow()
            model_id = uuid.uuid4().hex[:8]
            
            with get_sync_session() as session:
                db_model = CustomModelDB(
                    id=model_id,
                    name=validated_name,
                    version=validated_version,
                    enabled=enabled,
                    rag_settings=settings.model_dump(),
                    tool_names=validated_tools,
                    base_model=base_model,
                    model_params=safe_params,
                    active_versions=[validated_version],
                    created_at=now,
                    updated_at=now,
                )
                
                version_db = ModelVersionDB(
                    model_id=model_id,
                    version=validated_version,
                    enabled=enabled,
                    rag_settings=settings.model_dump(),
                    tool_names=validated_tools,
                    base_model=base_model,
                    model_params=safe_params,
                    description=description or "Initial version",
                    created_at=now,
                )
                
                session.add(db_model)
                session.add(version_db)
                session.commit()
                session.refresh(db_model)
            
            return self.get_model(model_id)

    def create_model_version(
        self,
        model_id: str,
        version: str,
        enabled: bool = True,
        rag_settings: Optional[RagSettings] = None,
        tool_names: Optional[List[str]] = None,
        base_model: Optional[str] = None,
        model_params: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
    ) -> Tuple[CustomModel, ModelVersionConfig]:
        """Create a new version for an existing model."""
        with self._lock:
            model = self.get_model(model_id)
            if not model:
                raise KeyError(f"Model '{model_id}' does not exist.")
            
            validated_version = validate_version(version)
            
            if validated_version in model.version_history:
                raise ValueError(f"Version '{validated_version}' already exists for model '{model.name}'.")
            
            if compare_versions(validated_version, model.version) <= 0:
                raise ValueError(f"New version '{validated_version}' must be greater than current version '{model.version}'.")
            
            now = datetime.utcnow()
            
            tool_list = tool_names if tool_names is not None else model.tool_names
            validated_tools = [tool for tool in tool_list if tool in AVAILABLE_TOOL_NAMES]
            if not validated_tools:
                raise ValueError("At least one valid tool name is required.")
            
            settings = rag_settings if rag_settings is not None else model.rag_settings
            base = base_model if base_model is not None else model.base_model
            
            safe_params = {}
            if model_params is not None:
                safe_params = {k: v for k, v in model_params.items() if k in ALLOWED_MODEL_PARAMS}
            else:
                safe_params = model.model_params.copy()
            
            with get_sync_session() as session:
                # Create version record
                version_db = ModelVersionDB(
                    model_id=model_id,
                    version=validated_version,
                    enabled=enabled,
                    rag_settings=settings.model_dump() if isinstance(settings, RagSettings) else settings,
                    tool_names=validated_tools,
                    base_model=base,
                    model_params=safe_params,
                    description=description,
                    created_at=now,
                )
                session.add(version_db)
                
                # Update model to point to new version
                db_model = session.execute(
                    select(CustomModelDB).where(CustomModelDB.id == model_id)
                ).scalar_one()
                
                active_versions = db_model.active_versions or []
                if validated_version not in active_versions:
                    active_versions.append(validated_version)
                
                db_model.version = validated_version
                db_model.enabled = enabled
                db_model.rag_settings = settings.model_dump() if isinstance(settings, RagSettings) else settings
                db_model.tool_names = validated_tools
                db_model.base_model = base
                db_model.model_params = safe_params
                db_model.active_versions = active_versions
                db_model.updated_at = now
                
                session.commit()
            
            updated_model = self.get_model(model_id)
            return (updated_model, updated_model.version_history[validated_version])

    def get_version_history(self, model_id: str) -> List[ModelVersionConfig]:
        """Get all versions for a model, sorted by version (newest first)."""
        model = self.get_model(model_id)
        if not model:
            raise KeyError(f"Model '{model_id}' does not exist.")
        
        versions = list(model.version_history.values())
        versions.sort(key=lambda v: [int(x) for x in v.version.split(".")], reverse=True)
        
        return versions

    def get_version(self, model_id: str, version: str) -> ModelVersionConfig:
        """Get a specific version config for a model."""
        model = self.get_model(model_id)
        if not model:
            raise KeyError(f"Model '{model_id}' does not exist.")
        
        validated_version = validate_version(version)
        
        if validated_version not in model.version_history:
            raise KeyError(f"Version '{validated_version}' not found for model '{model.name}'.")
        
        return model.version_history[validated_version]

    def activate_model_version(self, model_id: str, version: str) -> Tuple[CustomModel, ModelVersionConfig]:
        """Activate a specific version for client use."""
        with self._lock:
            model = self.get_model(model_id)
            if not model:
                raise KeyError(f"Model '{model_id}' does not exist.")
            
            validated_version = validate_version(version)
            
            if validated_version not in model.version_history:
                raise KeyError(f"Version '{validated_version}' not found for model '{model.name}'.")
            
            with get_sync_session() as session:
                db_model = session.execute(
                    select(CustomModelDB).where(CustomModelDB.id == model_id)
                ).scalar_one()
                
                active_versions = db_model.active_versions or []
                if validated_version not in active_versions:
                    active_versions.append(validated_version)
                    db_model.active_versions = active_versions
                    db_model.updated_at = datetime.utcnow()
                
                # Update version enabled status
                version_db = session.execute(
                    select(ModelVersionDB)
                    .where(ModelVersionDB.model_id == model_id)
                    .where(ModelVersionDB.version == validated_version)
                ).scalar_one()
                version_db.enabled = True
                
                session.commit()
            
            updated_model = self.get_model(model_id)
            return (updated_model, updated_model.version_history[validated_version])

    def deactivate_model_version(self, model_id: str, version: str) -> Tuple[CustomModel, ModelVersionConfig]:
        """Deactivate a specific version (clients can't use it)."""
        with self._lock:
            model = self.get_model(model_id)
            if not model:
                raise KeyError(f"Model '{model_id}' does not exist.")
            
            validated_version = validate_version(version)
            
            if validated_version not in model.version_history:
                raise KeyError(f"Version '{validated_version}' not found for model '{model.name}'.")
            
            if len(model.active_versions) == 1 and validated_version in model.active_versions:
                raise ValueError("Cannot deactivate the only active version. Activate another version first.")
            
            with get_sync_session() as session:
                db_model = session.execute(
                    select(CustomModelDB).where(CustomModelDB.id == model_id)
                ).scalar_one()
                
                active_versions = db_model.active_versions or []
                if validated_version in active_versions:
                    active_versions.remove(validated_version)
                    db_model.active_versions = active_versions
                    db_model.updated_at = datetime.utcnow()
                
                # Update version enabled status
                version_db = session.execute(
                    select(ModelVersionDB)
                    .where(ModelVersionDB.model_id == model_id)
                    .where(ModelVersionDB.version == validated_version)
                ).scalar_one()
                version_db.enabled = False
                
                session.commit()
            
            updated_model = self.get_model(model_id)
            return (updated_model, updated_model.version_history[validated_version])

    def is_version_active(self, model_id: str, version: str) -> bool:
        """Check if a specific version is active for client use."""
        model = self.get_model(model_id)
        if not model:
            return False
        return version in model.active_versions

    def activate_model(self, model_id: str) -> CustomModel:
        """Activate a model (add to active models list)."""
        with self._lock:
            model = self.get_model(model_id)
            if not model:
                raise KeyError(f"Model '{model_id}' does not exist.")
            
            with get_sync_session() as session:
                # Check if already active
                existing = session.execute(
                    select(ActiveModelDB).where(ActiveModelDB.model_id == model_id)
                ).scalar_one_or_none()
                
                if existing:
                    # Move to highest priority
                    session.execute(delete(ActiveModelDB).where(ActiveModelDB.model_id == model_id))
                    session.commit()
                
                # Get lowest priority number and subtract 1
                min_priority = session.execute(
                    select(ActiveModelDB.priority).order_by(ActiveModelDB.priority).limit(1)
                ).scalar_one_or_none()
                
                new_priority = (min_priority - 1) if min_priority is not None else 0
                
                active = ActiveModelDB(model_id=model_id, priority=new_priority)
                session.add(active)
                session.commit()
            
            return model

    def remove_active_model(self, model_id: str) -> CustomModel:
        """Remove a model from active models list."""
        with self._lock:
            model = self.get_model(model_id)
            if not model:
                raise KeyError(f"Model '{model_id}' does not exist.")
            
            with get_sync_session() as session:
                existing = session.execute(
                    select(ActiveModelDB).where(ActiveModelDB.model_id == model_id)
                ).scalar_one_or_none()
                
                if not existing:
                    raise ValueError(f"Model '{model_id}' is not active.")
                
                # Check if it's the only active model
                count = session.execute(select(ActiveModelDB)).scalars().all()
                if len(count) == 1:
                    raise ValueError("At least one active model must remain.")
                
                session.execute(delete(ActiveModelDB).where(ActiveModelDB.model_id == model_id))
                session.commit()
            
            return model

    def update_model(
        self,
        model_id: str,
        name: Optional[str] = None,
        enabled: Optional[bool] = None,
        rag_settings: Optional[RagSettings] = None,
        tool_names: Optional[List[str]] = None,
        base_model: Optional[str] = None,
        model_params: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None,
    ) -> CustomModel:
        """Update an existing model's fields. Only provided fields are updated."""
        with self._lock:
            model = self.get_model(model_id)
            if not model:
                raise KeyError(f"Model '{model_id}' does not exist.")
            
            with get_sync_session() as session:
                db_model = session.execute(
                    select(CustomModelDB).where(CustomModelDB.id == model_id)
                ).scalar_one()
                
                if name is not None:
                    validated_name = validate_model_name(name)
                    # Check for duplicate names (excluding current model)
                    existing = session.execute(
                        select(CustomModelDB)
                        .where(CustomModelDB.name.ilike(validated_name))
                        .where(CustomModelDB.id != model_id)
                    ).scalar_one_or_none()
                    if existing:
                        raise ValueError(f"A model with name '{validated_name}' already exists.")
                    db_model.name = validated_name
                
                if version is not None:
                    db_model.version = validate_version(version)
                if enabled is not None:
                    db_model.enabled = enabled
                if rag_settings is not None:
                    db_model.rag_settings = rag_settings.model_dump()
                if tool_names is not None:
                    validated_tools = [t for t in tool_names if t in AVAILABLE_TOOL_NAMES]
                    if not validated_tools:
                        raise ValueError("At least one valid tool name is required.")
                    db_model.tool_names = validated_tools
                if base_model is not None:
                    db_model.base_model = base_model if base_model else None
                if model_params is not None:
                    safe_params = {k: v for k, v in model_params.items() if k in ALLOWED_MODEL_PARAMS}
                    db_model.model_params = safe_params
                
                db_model.updated_at = datetime.utcnow()
                session.commit()
            
            return self.get_model(model_id)

    def delete_model(self, model_id: str) -> None:
        """Delete a model by ID. Cannot delete the only active model."""
        with self._lock:
            model = self.get_model(model_id)
            if not model:
                raise KeyError(f"Model '{model_id}' does not exist.")
            
            with get_sync_session() as session:
                # Check if it's the only active model
                active = session.execute(
                    select(ActiveModelDB).where(ActiveModelDB.model_id == model_id)
                ).scalar_one_or_none()
                
                if active:
                    count = len(session.execute(select(ActiveModelDB)).scalars().all())
                    if count == 1:
                        raise ValueError("Cannot delete the only active model. Activate another model first.")
                    # Remove from active models
                    session.execute(delete(ActiveModelDB).where(ActiveModelDB.model_id == model_id))
                
                # Delete the model (versions cascade)
                session.execute(delete(CustomModelDB).where(CustomModelDB.id == model_id))
                session.commit()


# Global config store instance
_config_store: Optional[ConfigStore] = None


def get_config_store() -> ConfigStore:
    """Get or create the global config store."""
    global _config_store
    if _config_store is None:
        _config_store = ConfigStore()
    return _config_store


def get_active_model() -> CustomModel:
    """Get the currently active model."""
    return get_config_store().get_active_model()


# ========== TOOL MANAGEMENT ==========

class ToolParameter(BaseModel):
    """Definition of a tool parameter."""
    name: str
    type: str = "string"  # string, number, boolean, array, object
    description: str = ""
    required: bool = True
    default: Optional[Any] = None


class Tool(BaseModel):
    """Representation of a tool configuration."""
    id: str
    name: str
    description: str
    category: Optional[str] = None
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)
    is_builtin: bool = False  # True if this is a code-implemented tool
    function_code: Optional[str] = None  # Python code for custom tools
    parameters: List[ToolParameter] = Field(default_factory=list)  # Function parameters
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# Built-in tool definitions (these have actual code implementations)
# Using fixed hex IDs for consistency
BUILTIN_TOOLS = {
    "get_datetime": Tool(
        id="c9d0e1f2",  # Fixed hex ID for get_datetime
        name="get_datetime",
        description="Get the current date and time. Use this tool when the user asks about the current time or date.",
        category="Utility",
        enabled=True,
        is_builtin=True,
        created_at="2024-01-01T00:00:00Z"
    ),
    "search_knowledge_base": Tool(
        id="f3a4b5c6",  # Fixed hex ID for search_knowledge_base
        name="search_knowledge_base",
        description="Search the knowledge base for relevant information. Use this tool when you need to find specific information from the knowledge base documents.",
        category="Search",
        enabled=True,
        is_builtin=True,
        created_at="2024-01-01T00:00:00Z"
    ),
}


class ToolStore:
    """Persistent store for tools using PostgreSQL."""

    def __init__(self):
        self._lock = Lock()
        self._initialized = False
        self._initialize()

    def _initialize(self) -> None:
        """Initialize database and sync builtin tools."""
        if self._initialized:
            return
        
        # Initialize database tables
        init_db_sync()
        
        # Sync builtin tools to database
        self._sync_builtin_tools()
        
        # Update AVAILABLE_TOOL_NAMES with database tools
        self._update_available_tools()
        
        self._initialized = True

    def _sync_builtin_tools(self) -> None:
        """Ensure builtin tools exist in database with correct hex IDs."""
        with get_sync_session() as session:
            for tool_name, tool_def in BUILTIN_TOOLS.items():
                existing = session.execute(
                    select(ToolDB).where(ToolDB.name == tool_name)
                ).scalar_one_or_none()
                
                if not existing:
                    # Create builtin tool in database
                    db_tool = ToolDB(
                        id=tool_def.id,
                        name=tool_def.name,
                        description=tool_def.description,
                        category=tool_def.category,
                        enabled=tool_def.enabled,
                        config={"is_builtin": True},
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    session.add(db_tool)
                elif existing.id != tool_def.id:
                    # Update existing tool to use new hex ID
                    existing.id = tool_def.id
                    existing.updated_at = datetime.utcnow()
            session.commit()

    def _update_available_tools(self) -> None:
        """Update AVAILABLE_TOOL_NAMES with all enabled tools from database."""
        global AVAILABLE_TOOL_NAMES
        tools = self.list_tools()
        AVAILABLE_TOOL_NAMES = [t.name for t in tools if t.enabled]

    def list_tools(self) -> List[Tool]:
        """List all tools (builtin + custom)."""
        with get_sync_session() as session:
            result = session.execute(select(ToolDB).order_by(ToolDB.name))
            db_tools = result.scalars().all()
            return [self._db_to_pydantic(t) for t in db_tools]

    def get_tool(self, tool_id: str) -> Optional[Tool]:
        """Get a tool by ID or name."""
        with get_sync_session() as session:
            result = session.execute(
                select(ToolDB).where(
                    (ToolDB.id == tool_id) | (ToolDB.name == tool_id)
                )
            )
            db_tool = result.scalar_one_or_none()
            if db_tool:
                return self._db_to_pydantic(db_tool)
            return None

    def create_tool(
        self,
        name: str,
        description: str,
        category: Optional[str] = None,
        enabled: bool = True,
        config: Optional[Dict[str, Any]] = None,
        function_code: Optional[str] = None,
        parameters: Optional[List[Dict[str, Any]]] = None,
    ) -> Tool:
        """Create a new custom tool."""
        with self._lock:
            # Validate name
            if not name or not re.match(r'^[a-z][a-z0-9_-]*$', name):
                raise ValueError(
                    "Tool name must start with a letter and contain only lowercase letters, "
                    "numbers, underscores, and hyphens."
                )
            
            # Check for duplicates
            existing = self.get_tool(name)
            if existing:
                raise ValueError(f"Tool '{name}' already exists.")
            
            # Validate function code if provided
            if function_code:
                self._validate_function_code(function_code, name)
            
            tool_id = uuid.uuid4().hex[:8]  # Use hex format for tool ID
            now = datetime.utcnow()
            
            with get_sync_session() as session:
                db_tool = ToolDB(
                    id=tool_id,
                    name=name,
                    description=description,
                    category=category,
                    enabled=enabled,
                    config=config or {},
                    function_code=function_code,
                    parameters=parameters,
                    created_at=now,
                    updated_at=now,
                )
                session.add(db_tool)
                session.commit()
                session.refresh(db_tool)
            
            # Update available tools list
            self._update_available_tools()
            
            return self.get_tool(tool_id)

    def update_tool(
        self,
        tool_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        enabled: Optional[bool] = None,
        config: Optional[Dict[str, Any]] = None,
        function_code: Optional[str] = None,
        parameters: Optional[List[Dict[str, Any]]] = None,
    ) -> Tool:
        """Update an existing tool."""
        with self._lock:
            tool = self.get_tool(tool_id)
            if not tool:
                raise KeyError(f"Tool '{tool_id}' not found.")
            
            # Prevent renaming builtin tools
            if tool.is_builtin and name and name != tool.name:
                raise ValueError("Cannot rename builtin tools.")
            
            # Prevent modifying function code of builtin tools
            if tool.is_builtin and function_code is not None:
                raise ValueError("Cannot modify function code of builtin tools.")
            
            # Validate new name if provided
            if name and not re.match(r'^[a-z][a-z0-9_-]*$', name):
                raise ValueError(
                    "Tool name must start with a letter and contain only lowercase letters, "
                    "numbers, underscores, and hyphens."
                )
            
            # Check for duplicate name
            if name and name != tool.name:
                existing = self.get_tool(name)
                if existing:
                    raise ValueError(f"Tool '{name}' already exists.")
            
            # Validate function code if provided
            if function_code:
                self._validate_function_code(function_code, name or tool.name)
            
            with get_sync_session() as session:
                db_tool = session.execute(
                    select(ToolDB).where(ToolDB.id == tool.id)
                ).scalar_one()
                
                if name is not None:
                    db_tool.name = name
                    # Note: ID remains unchanged (hex format, not tied to name)
                if description is not None:
                    db_tool.description = description
                if category is not None:
                    db_tool.category = category
                if enabled is not None:
                    db_tool.enabled = enabled
                if config is not None:
                    db_tool.config = config
                if function_code is not None:
                    db_tool.function_code = function_code
                if parameters is not None:
                    db_tool.parameters = parameters
                
                db_tool.updated_at = datetime.utcnow()
                session.commit()
            
            # Update available tools list
            self._update_available_tools()
            
            return self.get_tool(tool_id)  # Use original ID since it doesn't change

    def delete_tool(self, tool_id: str) -> None:
        """Delete a tool by ID."""
        with self._lock:
            tool = self.get_tool(tool_id)
            if not tool:
                raise KeyError(f"Tool '{tool_id}' not found.")
            
            # Prevent deleting builtin tools
            if tool.is_builtin:
                raise ValueError("Cannot delete builtin tools.")
            
            with get_sync_session() as session:
                session.execute(
                    delete(ToolDB).where(ToolDB.id == tool.id)
                )
                session.commit()
            
            # Update available tools list
            self._update_available_tools()

    def _db_to_pydantic(self, db_tool: ToolDB) -> Tool:
        """Convert database model to Pydantic model."""
        config = db_tool.config or {}
        
        # Parse parameters from JSON
        params = []
        if db_tool.parameters:
            for p in db_tool.parameters:
                params.append(ToolParameter(
                    name=p.get("name", ""),
                    type=p.get("type", "string"),
                    description=p.get("description", ""),
                    required=p.get("required", True),
                    default=p.get("default"),
                ))
        
        return Tool(
            id=db_tool.id,
            name=db_tool.name,
            description=db_tool.description or "",
            category=db_tool.category,
            enabled=db_tool.enabled,
            config=config,
            is_builtin=config.get("is_builtin", False),
            function_code=db_tool.function_code,
            parameters=params,
            created_at=db_tool.created_at.isoformat() + "Z" if db_tool.created_at else None,
            updated_at=db_tool.updated_at.isoformat() + "Z" if db_tool.updated_at else None,
        )

    def _validate_function_code(self, code: str, tool_name: str) -> None:
        """Validate Python function code for safety and correctness."""
        if not code or not code.strip():
            raise ValueError("Function code cannot be empty.")
        
        # Basic syntax check by compiling
        try:
            compile(code, f"<tool:{tool_name}>", "exec")
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax in function code: {e}")
        
        # Security: Check for dangerous imports/operations
        dangerous_patterns = [
            "import os", "from os", "import sys", "from sys",
            "import subprocess", "from subprocess",
            "__import__", "exec(", "eval(",
            "open(", "file(",
            "import shutil", "from shutil",
            "import socket", "from socket",
        ]
        
        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in code_lower:
                raise ValueError(
                    f"Function code contains potentially dangerous operation: '{pattern}'. "
                    "For security, system-level operations are not allowed."
                )

    def get_custom_tools_with_code(self) -> List[Tool]:
        """Get all custom tools that have function code defined."""
        tools = self.list_tools()
        return [t for t in tools if t.function_code and not t.is_builtin and t.enabled]


# Global tool store instance
_tool_store: Optional[ToolStore] = None


def get_tool_store() -> ToolStore:
    """Get or create the global tool store."""
    global _tool_store
    if _tool_store is None:
        _tool_store = ToolStore()
    return _tool_store


# ========== KNOWLEDGE BASE MANAGEMENT ==========

class KnowledgeBase(BaseModel):
    """Representation of a knowledge base."""
    id: str
    name: str
    description: Optional[str] = None
    collection: str
    embedding_model: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class KnowledgeBaseStore:
    """Persistent store for knowledge bases using PostgreSQL."""

    def __init__(self):
        self._lock = Lock()
        self._initialized = False
        self._initialize()

    def _initialize(self) -> None:
        """Initialize database and ensure default knowledge base exists."""
        if self._initialized:
            return
        
        # Initialize database tables
        init_db_sync()
        
        # Ensure at least one knowledge base exists and migrate old IDs
        with get_sync_session() as session:
            result = session.execute(select(KnowledgeBaseDB).limit(1))
            existing_kb = result.scalar_one_or_none()
            
            if not existing_kb:
                # Create default knowledge base
                default_kb = self._create_default_kb_db(session)
                session.add(default_kb)
                session.commit()
            elif existing_kb.id == "default_kb":
                # Migrate old default KB ID to new hex format
                existing_kb.id = DEFAULT_KB_ID
                existing_kb.updated_at = datetime.utcnow()
                session.commit()
        
        self._initialized = True

    def _create_default_kb_db(self, session) -> KnowledgeBaseDB:
        """Create default knowledge base database record."""
        now = datetime.utcnow()
        default_collection = os.getenv("QDRANT_COLLECTION", "knowledge_base")
        
        db_kb = KnowledgeBaseDB(
            id=DEFAULT_KB_ID,  # Use hex format ID
            name="Default Knowledge Base",
            description="Default knowledge base for general use",
            collection=default_collection,
            embedding_model=None,
            created_at=now,
            updated_at=now,
        )
        
        return db_kb

    def list_knowledge_bases(self) -> List[KnowledgeBase]:
        """List all knowledge bases."""
        with get_sync_session() as session:
            result = session.execute(select(KnowledgeBaseDB).order_by(KnowledgeBaseDB.name))
            db_kbs = result.scalars().all()
            return [self._db_to_pydantic(kb) for kb in db_kbs]

    def get_knowledge_base(self, kb_id: str) -> Optional[KnowledgeBase]:
        """Get a knowledge base by ID or name."""
        with get_sync_session() as session:
            result = session.execute(
                select(KnowledgeBaseDB).where(
                    (KnowledgeBaseDB.id == kb_id) | (KnowledgeBaseDB.name == kb_id)
                )
            )
            db_kb = result.scalar_one_or_none()
            if db_kb:
                return self._db_to_pydantic(db_kb)
            return None

    def create_knowledge_base(
        self,
        name: str,
        description: Optional[str] = None,
        collection: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ) -> KnowledgeBase:
        """Create a new knowledge base."""
        with self._lock:
            # Validate name
            if not name or not re.match(r'^[a-z][a-z0-9_-]*$', name):
                raise ValueError(
                    "Knowledge base name must start with a letter and contain only lowercase letters, "
                    "numbers, underscores, and hyphens."
                )
            
            # Check for duplicates
            existing = self.get_knowledge_base(name)
            if existing:
                raise ValueError(f"Knowledge base '{name}' already exists.")
            
            kb_id = uuid.uuid4().hex[:8]  # Use hex format for KB ID
            now = datetime.utcnow()
            
            # Generate collection name if not provided
            if not collection:
                collection = f"kb_{kb_id.replace('-', '_')}"
            
            # Check collection uniqueness
            with get_sync_session() as session:
                existing_coll = session.execute(
                    select(KnowledgeBaseDB).where(KnowledgeBaseDB.collection == collection)
                ).scalar_one_or_none()
                if existing_coll:
                    raise ValueError(f"Collection '{collection}' is already used by another knowledge base.")
            
            with get_sync_session() as session:
                db_kb = KnowledgeBaseDB(
                    id=kb_id,
                    name=name,
                    description=description,
                    collection=collection,
                    embedding_model=embedding_model,
                    created_at=now,
                    updated_at=now,
                )
                session.add(db_kb)
                session.commit()
                session.refresh(db_kb)
            
            return self.get_knowledge_base(kb_id)

    def update_knowledge_base(
        self,
        kb_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        collection: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ) -> KnowledgeBase:
        """Update an existing knowledge base."""
        with self._lock:
            kb = self.get_knowledge_base(kb_id)
            if not kb:
                raise KeyError(f"Knowledge base '{kb_id}' not found.")
            
            # Validate new name if provided
            if name and not re.match(r'^[a-z][a-z0-9_-]*$', name):
                raise ValueError(
                    "Knowledge base name must start with a letter and contain only lowercase letters, "
                    "numbers, underscores, and hyphens."
                )
            
            # Check for duplicate name
            if name and name != kb.name:
                existing = self.get_knowledge_base(name)
                if existing:
                    raise ValueError(f"Knowledge base '{name}' already exists.")
            
            # Check collection uniqueness if changing
            if collection and collection != kb.collection:
                with get_sync_session() as session:
                    existing_coll = session.execute(
                        select(KnowledgeBaseDB).where(KnowledgeBaseDB.collection == collection)
                    ).scalar_one_or_none()
                    if existing_coll:
                        raise ValueError(f"Collection '{collection}' is already used by another knowledge base.")
            
            with get_sync_session() as session:
                db_kb = session.execute(
                    select(KnowledgeBaseDB).where(KnowledgeBaseDB.id == kb.id)
                ).scalar_one()
                
                if name is not None:
                    db_kb.name = name
                if description is not None:
                    db_kb.description = description
                if collection is not None:
                    db_kb.collection = collection
                if embedding_model is not None:
                    db_kb.embedding_model = embedding_model
                
                db_kb.updated_at = datetime.utcnow()
                session.commit()
            
            return self.get_knowledge_base(kb.id)

    def delete_knowledge_base(self, kb_id: str) -> None:
        """Delete a knowledge base by ID."""
        with self._lock:
            kb = self.get_knowledge_base(kb_id)
            if not kb:
                raise KeyError(f"Knowledge base '{kb_id}' not found.")
            
            # Prevent deleting the default KB
            if kb.id == DEFAULT_KB_ID:
                raise ValueError("Cannot delete the default knowledge base.")
            
            with get_sync_session() as session:
                session.execute(
                    delete(KnowledgeBaseDB).where(KnowledgeBaseDB.id == kb.id)
                )
                session.commit()

    def _db_to_pydantic(self, db_kb: KnowledgeBaseDB) -> KnowledgeBase:
        """Convert database model to Pydantic model."""
        return KnowledgeBase(
            id=db_kb.id,
            name=db_kb.name,
            description=db_kb.description,
            collection=db_kb.collection,
            embedding_model=db_kb.embedding_model,
            created_at=db_kb.created_at.isoformat() + "Z" if db_kb.created_at else None,
            updated_at=db_kb.updated_at.isoformat() + "Z" if db_kb.updated_at else None,
        )


# Global knowledge base store instance
_kb_store: Optional[KnowledgeBaseStore] = None


def get_kb_store() -> KnowledgeBaseStore:
    """Get or create the global knowledge base store."""
    global _kb_store
    if _kb_store is None:
        _kb_store = KnowledgeBaseStore()
    return _kb_store
