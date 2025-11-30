"""Admin configuration manager for custom models and tool settings."""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator

CONFIG_PATH = Path(os.getenv("ADMIN_CONFIG_PATH", "config/custom_models.json"))
AVAILABLE_TOOL_NAMES = ["get_datetime", "search_knowledge_base"]
DEFAULT_MODEL_ID = "default"

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


class ConfigStore:
    """Persistent store for custom models and the active configuration."""

    def __init__(self, path: Path = CONFIG_PATH):
        self._path = path
        self._lock = Lock()
        self._models: Dict[str, CustomModel] = {}
        self._active_model_ids: List[str] = []
        self._load()

    def _load(self) -> None:
        raw = {}
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text())
            except json.JSONDecodeError:
                raw = {}
        models = raw.get("models", {})
        for model_id, model_data in models.items():
            payload = dict(model_data)
            payload["id"] = model_id
            # Migration: ensure version_history and active_versions exist
            if "version_history" not in payload:
                payload["version_history"] = {}
            if "active_versions" not in payload:
                payload["active_versions"] = [payload.get("version", "1.0.0")]
            self._models[model_id] = CustomModel.parse_obj(payload)

        raw_active_ids = raw.get("active_model_ids")
        raw_fallback_id = raw.get("active_model_id")
        if not self._models:
            default = self._create_default_model()
            self._models = {default.id: default}
            self._active_model_ids = [default.id]
        else:
            if raw_active_ids:
                filtered_ids = [mid for mid in raw_active_ids if mid in self._models]
            elif raw_fallback_id and raw_fallback_id in self._models:
                filtered_ids = [raw_fallback_id]
            else:
                filtered_ids = []
            if not filtered_ids:
                filtered_ids = [next(iter(self._models))]
            self._active_model_ids = filtered_ids
        self._save()

    def _create_default_model(self) -> CustomModel:
        now = datetime.utcnow().isoformat() + "Z"
        initial_version = "1.0.0"
        initial_config = ModelVersionConfig(
            version=initial_version,
            enabled=True,
            rag_settings=RagSettings(),
            tool_names=AVAILABLE_TOOL_NAMES.copy(),
            base_model=None,
            model_params={},
            created_at=now,
            description="Initial version",
        )
        return CustomModel(
            id=DEFAULT_MODEL_ID,
            name="default-model",
            version=initial_version,
            enabled=True,
            rag_settings=RagSettings(),
            tool_names=AVAILABLE_TOOL_NAMES.copy(),
            base_model=None,
            model_params={},
            created_at=now,
            updated_at=now,
            version_history={initial_version: initial_config},
            active_versions=[initial_version],
        )

    def _ensure_path(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _save(self) -> None:
        self._ensure_path()
        payload = {
            "active_model_id": self.active_model_id,
            "active_model_ids": self._active_model_ids,
            "models": {m.id: m.model_dump() for m in self._models.values()},
        }
        self._path.write_text(json.dumps(payload, indent=2))

    def list_models(self) -> List[CustomModel]:
        return list(self._models.values())

    def get_model(self, model_id: str) -> Optional[CustomModel]:
        return self._models.get(model_id)

    def get_model_by_name(self, name: str) -> Optional[CustomModel]:
        """Find a custom model by its name (case-insensitive)."""
        for model in self._models.values():
            if model.name.lower() == name.lower():
                return model
        return None

    def get_model_by_name_and_version(self, name: str, version: str) -> Optional[Tuple[CustomModel, ModelVersionConfig]]:
        """Find a custom model and its specific version config.
        
        Returns (model, version_config) tuple if found, None otherwise.
        """
        model = self.get_model_by_name(name)
        if not model:
            return None
        
        # Check if the requested version exists in history
        if version in model.version_history:
            return (model, model.version_history[version])
        
        # If version matches current and not in history, create a config from current
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
        """Resolve a model identifier (with optional version) to model and version config.
        
        Supports formats:
        - "model-name" -> returns latest active version
        - "model-name@1.0.0" -> returns specific version
        
        Returns (model, version_config) where version_config is None for latest.
        """
        name, version = parse_model_identifier(identifier)
        model = self.get_model_by_name(name)
        
        if not model:
            # Try by ID
            model = self.get_model(identifier.split("@")[0] if "@" in identifier else identifier)
            if not model:
                return None
        
        if version:
            # Specific version requested
            result = self.get_model_by_name_and_version(model.name, version)
            if result:
                return result
            return None
        
        # Return model with no specific version (use current config)
        return (model, None)

    @property
    def active_model_ids(self) -> List[str]:
        self._ensure_primary_active()
        return list(self._active_model_ids)

    @property
    def active_model_id(self) -> str:
        self._ensure_primary_active()
        return self._active_model_ids[0]

    def _ensure_primary_active(self) -> None:
        if not self._active_model_ids and self._models:
            self._active_model_ids = [next(iter(self._models))]

    def get_active_model(self) -> CustomModel:
        active_id = self.active_model_id
        return self._models[active_id]

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
        with self._lock:
            # Validate name format
            validated_name = validate_model_name(name)
            validated_version = validate_version(version)
            
            # Check for duplicate names
            for existing in self._models.values():
                if existing.name.lower() == validated_name.lower():
                    raise ValueError(f"A model with name '{validated_name}' already exists.")
            
            tool_list = tool_names if tool_names is not None else self.get_active_model().tool_names
            validated_tools = [tool for tool in tool_list if tool in AVAILABLE_TOOL_NAMES]
            if not validated_tools:
                raise ValueError("At least one valid tool name is required.")
            settings = rag_settings or self.get_active_model().rag_settings
            # Filter model_params to allowed keys only
            safe_params = {}
            if model_params:
                safe_params = {k: v for k, v in model_params.items() if k in ALLOWED_MODEL_PARAMS}
            
            now = datetime.utcnow().isoformat() + "Z"
            model_id = str(uuid.uuid4())
            
            # Create initial version config
            initial_version_config = ModelVersionConfig(
                version=validated_version,
                enabled=enabled,
                rag_settings=settings,
                tool_names=validated_tools,
                base_model=base_model,
                model_params=safe_params,
                created_at=now,
                description=description or "Initial version",
            )
            
            model = CustomModel(
                id=model_id,
                name=validated_name,
                version=validated_version,
                enabled=enabled,
                rag_settings=settings,
                tool_names=validated_tools,
                base_model=base_model,
                model_params=safe_params,
                created_at=now,
                updated_at=now,
                version_history={validated_version: initial_version_config},
                active_versions=[validated_version],
            )
            self._models[model_id] = model
            self._save()
            return model

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
        """Create a new version for an existing model.
        
        The new version becomes the current version of the model.
        Returns (model, version_config) tuple.
        """
        with self._lock:
            if model_id not in self._models:
                raise KeyError(f"Model '{model_id}' does not exist.")
            
            model = self._models[model_id]
            validated_version = validate_version(version)
            
            # Check if version already exists
            if validated_version in model.version_history:
                raise ValueError(f"Version '{validated_version}' already exists for model '{model.name}'.")
            
            # Version must be greater than current version
            if compare_versions(validated_version, model.version) <= 0:
                raise ValueError(f"New version '{validated_version}' must be greater than current version '{model.version}'.")
            
            now = datetime.utcnow().isoformat() + "Z"
            
            # Use provided values or inherit from current model config
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
            
            # Create version config
            version_config = ModelVersionConfig(
                version=validated_version,
                enabled=enabled,
                rag_settings=settings,
                tool_names=validated_tools,
                base_model=base,
                model_params=safe_params,
                created_at=now,
                description=description,
            )
            
            # Update model
            model.version_history[validated_version] = version_config
            model.version = validated_version
            model.enabled = enabled
            model.rag_settings = settings
            model.tool_names = validated_tools
            model.base_model = base
            model.model_params = safe_params
            model.updated_at = now
            
            # Activate the new version by default
            if validated_version not in model.active_versions:
                model.active_versions.append(validated_version)
            
            self._models[model_id] = model
            self._save()
            return (model, version_config)

    def get_version_history(self, model_id: str) -> List[ModelVersionConfig]:
        """Get all versions for a model, sorted by version (newest first)."""
        if model_id not in self._models:
            raise KeyError(f"Model '{model_id}' does not exist.")
        
        model = self._models[model_id]
        versions = list(model.version_history.values())
        
        # Sort by version (newest first)
        versions.sort(key=lambda v: [int(x) for x in v.version.split(".")], reverse=True)
        
        return versions

    def get_version(self, model_id: str, version: str) -> ModelVersionConfig:
        """Get a specific version config for a model."""
        if model_id not in self._models:
            raise KeyError(f"Model '{model_id}' does not exist.")
        
        model = self._models[model_id]
        validated_version = validate_version(version)
        
        if validated_version not in model.version_history:
            raise KeyError(f"Version '{validated_version}' not found for model '{model.name}'.")
        
        return model.version_history[validated_version]

    def activate_model_version(self, model_id: str, version: str) -> Tuple[CustomModel, ModelVersionConfig]:
        """Activate a specific version for client use."""
        with self._lock:
            if model_id not in self._models:
                raise KeyError(f"Model '{model_id}' does not exist.")
            
            model = self._models[model_id]
            validated_version = validate_version(version)
            
            if validated_version not in model.version_history:
                raise KeyError(f"Version '{validated_version}' not found for model '{model.name}'.")
            
            version_config = model.version_history[validated_version]
            
            if validated_version not in model.active_versions:
                model.active_versions.append(validated_version)
            
            version_config.enabled = True
            model.version_history[validated_version] = version_config
            model.updated_at = datetime.utcnow().isoformat() + "Z"
            
            self._models[model_id] = model
            self._save()
            return (model, version_config)

    def deactivate_model_version(self, model_id: str, version: str) -> Tuple[CustomModel, ModelVersionConfig]:
        """Deactivate a specific version (clients can't use it)."""
        with self._lock:
            if model_id not in self._models:
                raise KeyError(f"Model '{model_id}' does not exist.")
            
            model = self._models[model_id]
            validated_version = validate_version(version)
            
            if validated_version not in model.version_history:
                raise KeyError(f"Version '{validated_version}' not found for model '{model.name}'.")
            
            # Ensure at least one version remains active
            if len(model.active_versions) == 1 and validated_version in model.active_versions:
                raise ValueError("Cannot deactivate the only active version. Activate another version first.")
            
            version_config = model.version_history[validated_version]
            
            if validated_version in model.active_versions:
                model.active_versions.remove(validated_version)
            
            version_config.enabled = False
            model.version_history[validated_version] = version_config
            model.updated_at = datetime.utcnow().isoformat() + "Z"
            
            self._models[model_id] = model
            self._save()
            return (model, version_config)

    def is_version_active(self, model_id: str, version: str) -> bool:
        """Check if a specific version is active for client use."""
        if model_id not in self._models:
            return False
        model = self._models[model_id]
        return version in model.active_versions

    def activate_model(self, model_id: str) -> CustomModel:
        with self._lock:
            if model_id not in self._models:
                raise KeyError(f"Model '{model_id}' does not exist.")
            if model_id in self._active_model_ids:
                self._active_model_ids.remove(model_id)
            self._active_model_ids.insert(0, model_id)
            self._save()
            return self._models[model_id]

    def remove_active_model(self, model_id: str) -> CustomModel:
        with self._lock:
            if model_id not in self._models:
                raise KeyError(f"Model '{model_id}' does not exist.")
            if model_id not in self._active_model_ids:
                raise ValueError(f"Model '{model_id}' is not active.")
            if len(self._active_model_ids) == 1:
                raise ValueError("At least one active model must remain.")
            self._active_model_ids.remove(model_id)
            self._save()
            return self._models[model_id]

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
            if model_id not in self._models:
                raise KeyError(f"Model '{model_id}' does not exist.")
            model = self._models[model_id]
            
            if name is not None:
                validated_name = validate_model_name(name)
                # Check for duplicate names (excluding current model)
                for mid, existing in self._models.items():
                    if mid != model_id and existing.name.lower() == validated_name.lower():
                        raise ValueError(f"A model with name '{validated_name}' already exists.")
                model.name = validated_name
            
            if version is not None:
                validated_version = validate_version(version)
                model.version = validated_version
            if enabled is not None:
                model.enabled = enabled
            if rag_settings is not None:
                model.rag_settings = rag_settings
            if tool_names is not None:
                validated_tools = [t for t in tool_names if t in AVAILABLE_TOOL_NAMES]
                if not validated_tools:
                    raise ValueError("At least one valid tool name is required.")
                model.tool_names = validated_tools
            if base_model is not None:
                model.base_model = base_model if base_model else None
            if model_params is not None:
                # Filter to allowed keys only
                safe_params = {k: v for k, v in model_params.items() if k in ALLOWED_MODEL_PARAMS}
                model.model_params = safe_params
            
            # Update timestamp
            model.updated_at = datetime.utcnow().isoformat() + "Z"
            
            self._models[model_id] = model
            self._save()
            return model

    def delete_model(self, model_id: str) -> None:
        """Delete a model by ID. Cannot delete the only active model."""
        with self._lock:
            if model_id not in self._models:
                raise KeyError(f"Model '{model_id}' does not exist.")
            if model_id in self._active_model_ids:
                if len(self._active_model_ids) == 1:
                    raise ValueError("Cannot delete the only active model. Activate another model first.")
                self._active_model_ids.remove(model_id)
            del self._models[model_id]
            self._save()


_config_store = ConfigStore()


def get_config_store() -> ConfigStore:
    return _config_store


def get_active_model() -> CustomModel:
    return _config_store.get_active_model()
