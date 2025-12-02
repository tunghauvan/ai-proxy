"""FastAPI server with OpenAI-compatible API endpoints"""
import os
import uuid
import time
import re
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, AsyncGenerator, Any, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, AIMessageChunk

# Load environment variables
load_dotenv()

# Set up logging
import os
try:
    # Create logs directory if it doesn't exist
    os.makedirs('/app/logs', exist_ok=True)
    
    # Create a custom logger
    logger = logging.getLogger('langchain_proxy')
    logger.setLevel(logging.INFO)
    
    # Create file handler
    file_handler = logging.FileHandler('/app/logs/app.log')
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Test the logger
    logger.info("Logging system initialized successfully")
    print("Logging configured successfully")
except Exception as e:
    print(f"Failed to configure logging: {e}")
    import traceback
    traceback.print_exc()

# Set up LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGSMITH_TRACING", "true")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "open-chat-model")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")

DEFAULT_MODEL = os.getenv("OLLAMA_API_MODEL", "gpt-oss:20b-cloud")

from app.config import AVAILABLE_TOOL_NAMES, CustomModel, RagSettings, ModelVersionConfig, get_config_store, parse_model_identifier, get_tool_store, Tool, get_kb_store, KnowledgeBase
from app.database import init_db_sync
from app.graph import (
    graph,
    create_ollama_llm,
    create_llm_for_model,
    get_active_tools,
    get_kb_stats,
    list_kb_documents,
    is_rag_enabled,
    reload_knowledge_base,
    retrieve_relevant_context,
    format_context,
    import_texts,
    import_documents,
    clear_knowledge_base,
)
from langchain_core.documents import Document


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    logger.info("Starting LangGraph Proxy Server...")
    logger.info(f"Using model: {DEFAULT_MODEL}")
    logger.info(f"LangSmith Project: {os.getenv('LANGSMITH_PROJECT')}")
    
    # Initialize PostgreSQL database
    logger.info("Initializing PostgreSQL database...")
    try:
        init_db_sync()
        logger.info("Database initialized successfully.")
        
        # Initialize config store (creates default model if needed)
        store = get_config_store()
        active_model = store.get_active_model()
        logger.info(f"Active model: {active_model.name} (v{active_model.version})")
        
        # Initialize tool store (syncs builtin tools to database)
        tool_store = get_tool_store()
        tools = tool_store.list_tools()
        logger.info(f"Available tools: {len(tools)} ({len([t for t in tools if t.is_builtin])} builtin)")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.warning("The server will continue but some features may not work correctly.")
    
    # Initialize RAG
    if is_rag_enabled():
        kb_stats = get_kb_stats()
        logger.info(f"RAG enabled with {kb_stats.get('document_count', 0)} documents")
    else:
        logger.info("RAG is disabled according to the active custom model configuration.")
    
    yield
    logger.info("Shutting down LangGraph Proxy Server...")


app = FastAPI(
    title="LangGraph Proxy Server",
    description="OpenAI-compatible API server using LangGraph with Ollama",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# OpenAI-compatible models
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = Field(default=DEFAULT_MODEL)
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Usage


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "ollama"


class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


# Streaming response models (OpenAI compatible)
class ChatCompletionChunkDelta(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None


class ChatCompletionChunkChoice(BaseModel):
    index: int
    delta: ChatCompletionChunkDelta
    finish_reason: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionChunkChoice]


class CustomModelCreateRequest(BaseModel):
    name: str = Field(..., description="Model name (a-z, 0-9, _, -). Must start with letter.")
    version: Optional[str] = Field(default="1.0.0", description="Semantic version (e.g., 1.0.0)")
    enabled: Optional[bool] = True
    rag_settings: Optional[RagSettings] = None
    tool_names: Optional[List[str]] = None
    base_model: Optional[str] = None
    model_params: Optional[dict] = None


class CustomModelUpdateRequest(BaseModel):
    """Request to update an existing custom model. All fields optional."""
    name: Optional[str] = Field(None, description="Model name (a-z, 0-9, _, -). Must start with letter.")
    version: Optional[str] = Field(None, description="Semantic version (e.g., 1.0.0)")
    enabled: Optional[bool] = None
    rag_settings: Optional[RagSettings] = None
    tool_names: Optional[List[str]] = None
    base_model: Optional[str] = None
    model_params: Optional[dict] = None


class CreateVersionRequest(BaseModel):
    """Request to create a new version for a model."""
    version: str = Field(..., description="Semantic version (e.g., 2.0.0). Must be greater than current version.")
    enabled: Optional[bool] = True
    rag_settings: Optional[RagSettings] = None
    tool_names: Optional[List[str]] = None
    base_model: Optional[str] = None
    model_params: Optional[dict] = None
    description: Optional[str] = Field(None, description="Version description/changelog")


class VersionResponse(BaseModel):
    """Response for a model version."""
    version: str
    enabled: bool
    rag_settings: RagSettings
    tool_names: List[str]
    base_model: Optional[str]
    model_params: dict
    created_at: Optional[str]
    description: Optional[str]
    active: bool  # Whether this version is active for client use


class CustomModelResponse(BaseModel):
    id: str
    name: str
    version: str
    enabled: bool
    rag_settings: RagSettings
    tool_names: List[str]
    base_model: Optional[str]
    model_params: dict
    active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    active_versions: List[str] = []  # List of active version strings
    version_count: int = 0  # Total number of versions


class ToolParameterRequest(BaseModel):
    name: str = Field(..., description="Parameter name")
    type: str = Field(default="string", description="Parameter type: string, number, boolean, array, object")
    description: str = Field(default="", description="Parameter description")
    required: bool = Field(default=True, description="Whether this parameter is required")
    default: Optional[Any] = Field(None, description="Default value if not required")


class ToolCreateRequest(BaseModel):
    name: str = Field(..., description="Tool name (a-z, 0-9, _, -). Must start with letter.")
    description: str = Field(..., description="Description of what the tool does")
    category: Optional[str] = Field(None, description="Tool category")
    enabled: Optional[bool] = True
    function_code: Optional[str] = Field(None, description="Python function code for the tool")
    parameters: Optional[List[ToolParameterRequest]] = Field(None, description="Function parameters")


class ToolUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Tool name (a-z, 0-9, _, -). Must start with letter.")
    description: Optional[str] = Field(None, description="Description of what the tool does")
    category: Optional[str] = Field(None, description="Tool category")
    enabled: Optional[bool] = None
    function_code: Optional[str] = Field(None, description="Python function code for the tool")
    parameters: Optional[List[ToolParameterRequest]] = Field(None, description="Function parameters")


class ToolParameterResponse(BaseModel):
    name: str
    type: str
    description: str
    required: bool
    default: Optional[Any] = None


class ToolResponse(BaseModel):
    id: str
    name: str
    description: str
    category: Optional[str]
    enabled: bool
    is_builtin: bool = False
    function_code: Optional[str] = None
    parameters: List[ToolParameterResponse] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ToolListResponse(BaseModel):
    tools: List[str]


class KnowledgeBaseCreateRequest(BaseModel):
    name: str = Field(..., description="Knowledge base name (a-z, 0-9, _, -). Must start with letter.")
    description: Optional[str] = Field(None, description="Optional description")
    collection: Optional[str] = Field(None, description="Qdrant collection name (auto-generated if not provided)")
    embedding_model: Optional[str] = Field(None, description="Optional embedding model override")


class KnowledgeBaseUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Knowledge base name")
    description: Optional[str] = Field(None, description="Optional description")
    collection: Optional[str] = Field(None, description="Qdrant collection name")
    embedding_model: Optional[str] = Field(None, description="Optional embedding model override")


class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    collection: str
    embedding_model: Optional[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


def _build_model_response(model: CustomModel, active_model_ids: list[str]) -> CustomModelResponse:
    active_set = set(active_model_ids)
    return CustomModelResponse(
        id=model.id,
        name=model.name,
        version=model.version,
        enabled=model.enabled,
        rag_settings=model.rag_settings,
        tool_names=model.tool_names,
        base_model=model.base_model,
        model_params=model.model_params,
        active=model.id in active_set,
        created_at=model.created_at,
        updated_at=model.updated_at,
        active_versions=model.active_versions,
        version_count=len(model.version_history),
    )


def _build_version_response(version_config: ModelVersionConfig, active_versions: List[str]) -> VersionResponse:
    return VersionResponse(
        version=version_config.version,
        enabled=version_config.enabled,
        rag_settings=version_config.rag_settings,
        tool_names=version_config.tool_names,
        base_model=version_config.base_model,
        model_params=version_config.model_params,
        created_at=version_config.created_at,
        description=version_config.description,
        active=version_config.version in active_versions,
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "LangGraph Proxy Server is running", "status": "ok"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


# ========== KNOWLEDGE BASE MANAGEMENT ENDPOINTS ==========

@app.get("/v1/admin/knowledge-bases", response_model=List[KnowledgeBaseResponse])
async def list_admin_knowledge_bases():
    """List all knowledge bases"""
    kb_store = get_kb_store()
    kbs = kb_store.list_knowledge_bases()
    return [
        KnowledgeBaseResponse(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            collection=kb.collection,
            embedding_model=kb.embedding_model,
            created_at=kb.created_at,
            updated_at=kb.updated_at
        )
        for kb in kbs
    ]


@app.post("/v1/admin/knowledge-bases", response_model=KnowledgeBaseResponse, status_code=201)
async def create_admin_knowledge_base(request: KnowledgeBaseCreateRequest):
    """Create a new knowledge base"""
    kb_store = get_kb_store()
    try:
        kb = kb_store.create_knowledge_base(
            name=request.name,
            description=request.description,
            collection=request.collection,
            embedding_model=request.embedding_model,
        )
        return KnowledgeBaseResponse(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            collection=kb.collection,
            embedding_model=kb.embedding_model,
            created_at=kb.created_at,
            updated_at=kb.updated_at
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/v1/admin/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_admin_knowledge_base(kb_id: str):
    """Get a knowledge base by ID"""
    kb_store = get_kb_store()
    kb = kb_store.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_id}' not found")
    
    return KnowledgeBaseResponse(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        collection=kb.collection,
        embedding_model=kb.embedding_model,
        created_at=kb.created_at,
        updated_at=kb.updated_at
    )


@app.put("/v1/admin/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_admin_knowledge_base(kb_id: str, request: KnowledgeBaseUpdateRequest):
    """Update a knowledge base"""
    kb_store = get_kb_store()
    try:
        kb = kb_store.update_knowledge_base(
            kb_id=kb_id,
            name=request.name,
            description=request.description,
            collection=request.collection,
            embedding_model=request.embedding_model,
        )
        return KnowledgeBaseResponse(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            collection=kb.collection,
            embedding_model=kb.embedding_model,
            created_at=kb.created_at,
            updated_at=kb.updated_at
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/v1/admin/knowledge-bases/{kb_id}", status_code=204)
async def delete_admin_knowledge_base(kb_id: str):
    """Delete a knowledge base"""
    kb_store = get_kb_store()
    try:
        kb_store.delete_knowledge_base(kb_id)
        return None
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/v1/rag/stats")
async def rag_stats(kb_id: Optional[str] = None):
    """Get RAG knowledge base statistics"""
    return get_kb_stats(kb_id)


@app.get("/v1/rag/documents")
async def rag_documents(kb_id: Optional[str] = None, limit: int = 50, offset: int = 0):
    """List documents in the knowledge base"""
    return list_kb_documents(kb_id, limit, offset)


@app.get("/v1/admin/models", response_model=List[CustomModelResponse])
async def list_admin_models():
    """List the saved custom models"""
    store = get_config_store()
    active_ids = store.active_model_ids
    return [_build_model_response(m, active_ids) for m in store.list_models()]


@app.post("/v1/admin/models", response_model=CustomModelResponse, status_code=201)
async def create_admin_model(request: CustomModelCreateRequest):
    """Create a new custom model configuration"""
    store = get_config_store()
    try:
        model = store.create_model(
            name=request.name,
            enabled=request.enabled if request.enabled is not None else True,
            rag_settings=request.rag_settings,
            tool_names=request.tool_names,
            base_model=request.base_model,
            model_params=request.model_params,
            version=request.version or "1.0.0",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _build_model_response(model, store.active_model_ids)


@app.post("/v1/admin/models/{model_id}/activate", response_model=CustomModelResponse)
async def activate_admin_model(model_id: str):
    """Activate a saved custom model"""
    store = get_config_store()
    try:
        model = store.activate_model(model_id)
        reload_knowledge_base()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _build_model_response(model, store.active_model_ids)


@app.post("/v1/admin/models/{model_id}/deactivate", response_model=CustomModelResponse)
async def deactivate_admin_model(model_id: str):
    """Deactivate a saved custom model"""
    store = get_config_store()
    try:
        model = store.remove_active_model(model_id)
        reload_knowledge_base()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _build_model_response(model, store.active_model_ids)


@app.get("/v1/admin/models/{model_id}", response_model=CustomModelResponse)
async def get_admin_model(model_id: str):
    """Get a single custom model by ID"""
    store = get_config_store()
    model = store.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")
    return _build_model_response(model, store.active_model_ids)


@app.put("/v1/admin/models/{model_id}", response_model=CustomModelResponse)
async def update_admin_model(model_id: str, request: CustomModelUpdateRequest):
    """Update an existing custom model"""
    store = get_config_store()
    try:
        model = store.update_model(
            model_id=model_id,
            name=request.name,
            version=request.version,
            enabled=request.enabled,
            rag_settings=request.rag_settings,
            tool_names=request.tool_names,
            base_model=request.base_model,
            model_params=request.model_params,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _build_model_response(model, store.active_model_ids)


@app.delete("/v1/admin/models/{model_id}", status_code=204)
async def delete_admin_model(model_id: str):
    """Delete a custom model by ID"""
    store = get_config_store()
    try:
        store.delete_model(model_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return None


# ========== VERSION MANAGEMENT ENDPOINTS ==========

@app.get("/v1/admin/models/{model_id}/versions", response_model=List[VersionResponse])
async def list_model_versions(model_id: str):
    """List all versions of a model"""
    store = get_config_store()
    try:
        versions = store.get_version_history(model_id)
        model = store.get_model(model_id)
        return [_build_version_response(v, model.active_versions) for v in versions]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/v1/admin/models/{model_id}/versions", response_model=VersionResponse, status_code=201)
async def create_model_version(model_id: str, request: CreateVersionRequest):
    """Create a new version for a model"""
    store = get_config_store()
    try:
        model, version_config = store.create_model_version(
            model_id=model_id,
            version=request.version,
            enabled=request.enabled if request.enabled is not None else True,
            rag_settings=request.rag_settings,
            tool_names=request.tool_names,
            base_model=request.base_model,
            model_params=request.model_params,
            description=request.description,
        )
        return _build_version_response(version_config, model.active_versions)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/v1/admin/models/{model_id}/versions/{version}", response_model=VersionResponse)
async def get_model_version(model_id: str, version: str):
    """Get a specific version of a model"""
    store = get_config_store()
    try:
        version_config = store.get_version(model_id, version)
        model = store.get_model(model_id)
        return _build_version_response(version_config, model.active_versions)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/v1/admin/models/{model_id}/versions/{version}/activate", response_model=VersionResponse)
async def activate_model_version(model_id: str, version: str):
    """Activate a specific version for client use"""
    store = get_config_store()
    try:
        model, version_config = store.activate_model_version(model_id, version)
        reload_knowledge_base()
        return _build_version_response(version_config, model.active_versions)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/v1/admin/models/{model_id}/versions/{version}/deactivate", response_model=VersionResponse)
async def deactivate_model_version(model_id: str, version: str):
    """Deactivate a specific version (clients can't use it)"""
    store = get_config_store()
    try:
        model, version_config = store.deactivate_model_version(model_id, version)
        reload_knowledge_base()
        return _build_version_response(version_config, model.active_versions)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/v1/admin/tools", response_model=ToolListResponse)
async def list_admin_tools():
    """Return the tool names that can be assigned to custom models"""
    tool_store = get_tool_store()
    tools = tool_store.list_tools()
    return ToolListResponse(tools=[t.name for t in tools if t.enabled])


@app.get("/v1/admin/tools/detailed", response_model=List[ToolResponse])
async def list_admin_tools_detailed():
    """Return detailed information about available tools"""
    tool_store = get_tool_store()
    tools = tool_store.list_tools()
    return [
        ToolResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            category=t.category,
            enabled=t.enabled,
            is_builtin=t.is_builtin,
            function_code=t.function_code,
            parameters=[
                ToolParameterResponse(
                    name=p.name,
                    type=p.type,
                    description=p.description,
                    required=p.required,
                    default=p.default
                ) for p in t.parameters
            ],
            created_at=t.created_at,
            updated_at=t.updated_at
        )
        for t in tools
    ]


@app.post("/v1/admin/tools", response_model=ToolResponse, status_code=201)
async def create_admin_tool(request: ToolCreateRequest):
    """Create a new tool with optional Python function code"""
    tool_store = get_tool_store()
    try:
        # Convert parameters to dict format for storage
        params = None
        if request.parameters:
            params = [p.model_dump() for p in request.parameters]
        
        tool = tool_store.create_tool(
            name=request.name,
            description=request.description,
            category=request.category,
            enabled=request.enabled if request.enabled is not None else True,
            function_code=request.function_code,
            parameters=params,
        )
        return ToolResponse(
            id=tool.id,
            name=tool.name,
            description=tool.description,
            category=tool.category,
            enabled=tool.enabled,
            is_builtin=tool.is_builtin,
            function_code=tool.function_code,
            parameters=[
                ToolParameterResponse(
                    name=p.name,
                    type=p.type,
                    description=p.description,
                    required=p.required,
                    default=p.default
                ) for p in tool.parameters
            ],
            created_at=tool.created_at,
            updated_at=tool.updated_at
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/v1/admin/tools/{tool_id}", response_model=ToolResponse)
async def get_admin_tool(tool_id: str):
    """Get a specific tool by ID"""
    tool_store = get_tool_store()
    tool = tool_store.get_tool(tool_id)
    
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found")
    
    return ToolResponse(
        id=tool.id,
        name=tool.name,
        description=tool.description,
        category=tool.category,
        enabled=tool.enabled,
        is_builtin=tool.is_builtin,
        function_code=tool.function_code,
        parameters=[
            ToolParameterResponse(
                name=p.name,
                type=p.type,
                description=p.description,
                required=p.required,
                default=p.default
            ) for p in tool.parameters
        ],
        created_at=tool.created_at,
        updated_at=tool.updated_at
    )


@app.put("/v1/admin/tools/{tool_id}", response_model=ToolResponse)
async def update_admin_tool(tool_id: str, request: ToolUpdateRequest):
    """Update an existing tool"""
    tool_store = get_tool_store()
    try:
        # Convert parameters to dict format for storage
        params = None
        if request.parameters:
            params = [p.model_dump() for p in request.parameters]
        
        tool = tool_store.update_tool(
            tool_id=tool_id,
            name=request.name,
            description=request.description,
            category=request.category,
            enabled=request.enabled,
            function_code=request.function_code,
            parameters=params,
        )
        return ToolResponse(
            id=tool.id,
            name=tool.name,
            description=tool.description,
            category=tool.category,
            enabled=tool.enabled,
            is_builtin=tool.is_builtin,
            function_code=tool.function_code,
            parameters=[
                ToolParameterResponse(
                    name=p.name,
                    type=p.type,
                    description=p.description,
                    required=p.required,
                    default=p.default
                ) for p in tool.parameters
            ],
            created_at=tool.created_at,
            updated_at=tool.updated_at
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/v1/admin/tools/{tool_id}", status_code=204)
async def delete_admin_tool(tool_id: str):
    """Delete a tool by ID"""
    tool_store = get_tool_store()
    try:
        tool_store.delete_tool(tool_id)
        return None
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/v1/rag/reload")
async def rag_reload(kb_id: Optional[str] = None):
    """Reload the RAG knowledge base"""
    try:
        reload_knowledge_base(kb_id)
        return {"status": "success", "message": "Knowledge base reloaded", "stats": get_kb_stats(kb_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 3


class SearchResult(BaseModel):
    content: str
    source: str
    score: Optional[float] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str


@app.post("/v1/rag/search")
async def rag_search(request: SearchRequest, kb_id: Optional[str] = None):
    """Search the knowledge base directly"""
    try:
        docs = retrieve_relevant_context(request.query, k=request.top_k, kb_id=kb_id)
        results = [
            SearchResult(
                content=doc.page_content,
                source=doc.metadata.get("source", "unknown"),
            )
            for doc in docs
        ]
        return SearchResponse(results=results, query=request.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ImportTextRequest(BaseModel):
    texts: List[str]
    sources: Optional[List[str]] = None


class ImportDocumentRequest(BaseModel):
    content: str
    source: str


class ImportBatchRequest(BaseModel):
    documents: List[ImportDocumentRequest]


class ImportResponse(BaseModel):
    status: str
    original_count: int
    chunks_created: int


@app.post("/v1/rag/import/texts")
async def rag_import_texts(request: ImportTextRequest, kb_id: Optional[str] = None):
    """Import raw texts into the knowledge base"""
    try:
        metadatas = None
        if request.sources:
            metadatas = [{"source": s} for s in request.sources]
        result = import_texts(request.texts, metadatas, kb_id)
        return ImportResponse(
            status="success",
            original_count=result["original_texts"],
            chunks_created=result["chunks_created"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/rag/import/documents")
async def rag_import_documents(request: ImportBatchRequest, kb_id: Optional[str] = None):
    """Import documents into the knowledge base"""
    try:
        docs = [
            Document(page_content=d.content, metadata={"source": d.source})
            for d in request.documents
        ]
        result = import_documents(docs, kb_id)
        return ImportResponse(
            status="success",
            original_count=result["original_documents"],
            chunks_created=result["chunks_created"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/v1/rag/clear")
async def rag_clear(kb_id: Optional[str] = None):
    """Clear all documents from the knowledge base"""
    try:
        result = clear_knowledge_base(kb_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/models")
async def list_models():
    """List available models - OpenAI compatible"""
    store = get_config_store()
    active_models = [store.get_model(mid) for mid in store.active_model_ids if store.get_model(mid)]
    
    model_infos = []
    for model in active_models:
        if model.active_versions:
            # If multiple active versions, list each as name@version
            for version in model.active_versions:
                model_infos.append(ModelInfo(
                    id=f"{model.name}@{version}",
                    created=int(time.time()),
                ))
        else:
            # If no active versions specified, just use the model name
            model_infos.append(ModelInfo(
                id=model.name,
                created=int(time.time()),
            ))
    
    # If no active custom models, fall back to default
    if not model_infos:
        model_infos = [ModelInfo(
            id=DEFAULT_MODEL,
            created=int(time.time()),
        )]
    
    return ModelListResponse(data=model_infos)


def ensure_rag_enabled():
    if not is_rag_enabled():
        raise HTTPException(
            status_code=503,
            detail="RAG features are disabled for the active model. Activate a model with RAG enabled via /v1/admin/models.",
        )


def _resolve_model_config(request_model: str) -> Optional[str]:
    """Resolve model identifier to model config ID.
    
    Returns the model config ID if found, None otherwise.
    Raises HTTPException if model is disabled or version is not active.
    """
    store = get_config_store()
    
    # Parse model identifier (may include version)
    model_name, requested_version = parse_model_identifier(request_model)
    
    # Try to resolve the model
    result = store.resolve_model_identifier(request_model)
    
    if result:
        model, version_config = result
        
        # Check if model is enabled
        if not model.enabled:
            raise HTTPException(status_code=400, detail=f"Model '{model_name}' is disabled.")
        
        # If a specific version was requested, verify it's active
        if requested_version and version_config:
            if requested_version not in model.active_versions:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Version '{requested_version}' of model '{model_name}' is not active. "
                           f"Active versions: {', '.join(model.active_versions)}"
                )
        
        return model.id
    else:
        # Check if it's a direct model ID (without version)
        direct_model = store.get_model(model_name)
        if direct_model:
            if not direct_model.enabled:
                raise HTTPException(status_code=400, detail=f"Model '{model_name}' is disabled.")
            return direct_model.id
    
    # Otherwise, use default LLM (no custom model config)
    return None


def _convert_messages_to_langchain(messages: List[ChatMessage]) -> list:
    """Convert OpenAI-format messages to LangChain messages."""
    langchain_messages = []
    for msg in messages:
        if msg.role == "system":
            langchain_messages.append(SystemMessage(content=msg.content))
        elif msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))
    return langchain_messages


async def _stream_chat_response(
    request: ChatCompletionRequest,
    model_config_id: Optional[str],
    langchain_messages: list,
    kb_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Generate SSE stream for chat completions using LangGraph streaming."""
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(time.time())
    
    # Send initial chunk with role
    initial_chunk = ChatCompletionChunk(
        id=chat_id,
        created=created,
        model=request.model,
        choices=[
            ChatCompletionChunkChoice(
                index=0,
                delta=ChatCompletionChunkDelta(role="assistant"),
                finish_reason=None,
            )
        ],
    )
    yield f"data: {initial_chunk.model_dump_json()}\n\n"
    
    # Stream from the graph
    try:
        async for event in graph.astream_events(
            {"messages": langchain_messages, "model_config_id": model_config_id, "kb_id": kb_id},
            version="v2",
        ):
            kind = event.get("event")
            
            # Handle streaming tokens from the LLM
            if kind == "on_chat_model_stream":
                chunk_data = event.get("data", {})
                chunk = chunk_data.get("chunk")
                
                if chunk and hasattr(chunk, "content") and chunk.content:
                    content = chunk.content
                    # Handle both string content and list content
                    if isinstance(content, list):
                        # Extract text from content blocks
                        text_parts = []
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text_parts.append(block.get("text", ""))
                            elif isinstance(block, str):
                                text_parts.append(block)
                        content = "".join(text_parts)
                    
                    if content:
                        stream_chunk = ChatCompletionChunk(
                            id=chat_id,
                            created=created,
                            model=request.model,
                            choices=[
                                ChatCompletionChunkChoice(
                                    index=0,
                                    delta=ChatCompletionChunkDelta(content=content),
                                    finish_reason=None,
                                )
                            ],
                        )
                        yield f"data: {stream_chunk.model_dump_json()}\n\n"
        
        # Send final chunk with finish_reason
        final_chunk = ChatCompletionChunk(
            id=chat_id,
            created=created,
            model=request.model,
            choices=[
                ChatCompletionChunkChoice(
                    index=0,
                    delta=ChatCompletionChunkDelta(),
                    finish_reason="stop",
                )
            ],
        )
        yield f"data: {final_chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        # Send error in stream format
        error_chunk = {
            "error": {
                "message": str(e),
                "type": "server_error",
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, kb_id: Optional[str] = None, x_kb_id: Optional[str] = Header(None, alias="X-KB-ID")):
    """Chat completions endpoint - OpenAI compatible
    
    Supports model identifiers in formats:
    - "model-name" - uses the latest active version
    - "model-name@1.0.0" - uses a specific version
    
    Supports streaming when stream=true is set in the request.
    
    KB selection can be specified via:
    - kb_id query parameter
    - X-KB-ID header
    """
    # Use header value if query param not provided
    if kb_id is None and x_kb_id is not None:
        kb_id = x_kb_id
        
    try:
        # Resolve model configuration
        model_config_id = _resolve_model_config(request.model)
        
        # Convert messages to LangChain format
        langchain_messages = _convert_messages_to_langchain(request.messages)
        
        # Handle streaming request
        if request.stream:
            return StreamingResponse(
                _stream_chat_response(request, model_config_id, langchain_messages, kb_id),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        
        # Non-streaming request - use regular invoke
        result = graph.invoke({
            "messages": langchain_messages,
            "model_config_id": model_config_id,
            "kb_id": kb_id
        })
        
        # Get the last AI message
        response_message = result["messages"][-1]
        response_content = response_message.content
        
        # Calculate approximate token counts
        prompt_tokens = sum(len(msg.content.split()) for msg in request.messages)
        completion_tokens = len(response_content.split())
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=response_content),
                    finish_reason="stop",
                )
            ],
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
