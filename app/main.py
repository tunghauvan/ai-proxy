"""FastAPI server with OpenAI-compatible API endpoints"""
import os
import uuid
import time
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

# Load environment variables
load_dotenv()

# Set up LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGSMITH_TRACING", "true")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "open-chat-model")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")

DEFAULT_MODEL = os.getenv("OLLAMA_API_MODEL", "gpt-oss:20b-cloud")

from app.config import AVAILABLE_TOOL_NAMES, CustomModel, RagSettings, ModelVersionConfig, get_config_store, parse_model_identifier
from app.graph import (
    graph,
    create_ollama_llm,
    get_kb_stats,
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
    print("Starting LangGraph Proxy Server...")
    print(f"Using model: {DEFAULT_MODEL}")
    print(f"LangSmith Project: {os.getenv('LANGSMITH_PROJECT')}")
    
    # Initialize RAG
    if is_rag_enabled():
        kb_stats = get_kb_stats()
        print(f"RAG enabled with {kb_stats.get('document_count', 0)} documents")
    else:
        print("RAG is disabled according to the active custom model configuration.")
    
    yield
    print("Shutting down LangGraph Proxy Server...")


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


class ToolListResponse(BaseModel):
    tools: List[str]


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


@app.get("/v1/rag/stats")
async def rag_stats():
    """Get RAG knowledge base statistics"""
    if not is_rag_enabled():
        return {
            "enabled": False,
            "document_count": 0,
            "message": "RAG is disabled for the active model. Enable a model with RAG turned on via /v1/admin/models.",
        }
    return get_kb_stats()


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
    return ToolListResponse(tools=AVAILABLE_TOOL_NAMES)


@app.post("/v1/rag/reload")
async def rag_reload():
    """Reload the RAG knowledge base"""
    try:
        ensure_rag_enabled()
        reload_knowledge_base()
        return {"status": "success", "message": "Knowledge base reloaded", "stats": get_kb_stats()}
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
async def rag_search(request: SearchRequest):
    """Search the knowledge base directly"""
    try:
        ensure_rag_enabled()
        docs = retrieve_relevant_context(request.query, k=request.top_k)
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
async def rag_import_texts(request: ImportTextRequest):
    """Import raw texts into the knowledge base"""
    try:
        ensure_rag_enabled()
        metadatas = None
        if request.sources:
            metadatas = [{"source": s} for s in request.sources]
        result = import_texts(request.texts, metadatas)
        return ImportResponse(
            status="success",
            original_count=result["original_texts"],
            chunks_created=result["chunks_created"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/rag/import/documents")
async def rag_import_documents(request: ImportBatchRequest):
    """Import documents into the knowledge base"""
    try:
        ensure_rag_enabled()
        docs = [
            Document(page_content=d.content, metadata={"source": d.source})
            for d in request.documents
        ]
        result = import_documents(docs)
        return ImportResponse(
            status="success",
            original_count=result["original_documents"],
            chunks_created=result["chunks_created"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/v1/rag/clear")
async def rag_clear():
    """Clear all documents from the knowledge base"""
    try:
        ensure_rag_enabled()
        result = clear_knowledge_base()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/models")
async def list_models():
    """List available models - OpenAI compatible"""
    return ModelListResponse(
        data=[
            ModelInfo(
                id=DEFAULT_MODEL,
                created=int(time.time()),
            )
        ]
    )


def ensure_rag_enabled():
    if not is_rag_enabled():
        raise HTTPException(
            status_code=503,
            detail="RAG features are disabled for the active model. Activate a model with RAG enabled via /v1/admin/models.",
        )


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """Chat completions endpoint - OpenAI compatible
    
    Supports model identifiers in formats:
    - "model-name" - uses the latest active version
    - "model-name@1.0.0" - uses a specific version
    """
    try:
        # Check if request.model matches a custom model name (with optional version)
        model_config_id = None
        store = get_config_store()
        
        # Parse model identifier (may include version)
        model_name, requested_version = parse_model_identifier(request.model)
        
        # Try to resolve the model
        result = store.resolve_model_identifier(request.model)
        
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
            
            model_config_id = model.id
        else:
            # Check if it's a direct model ID (without version)
            direct_model = store.get_model(model_name)
            if direct_model:
                if not direct_model.enabled:
                    raise HTTPException(status_code=400, detail=f"Model '{model_name}' is disabled.")
                model_config_id = direct_model.id
            # Otherwise, use default LLM (no custom model config)
        
        # Convert OpenAI messages to LangChain messages
        langchain_messages = []
        for msg in request.messages:
            if msg.role == "system":
                langchain_messages.append(SystemMessage(content=msg.content))
            elif msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                from langchain_core.messages import AIMessage
                langchain_messages.append(AIMessage(content=msg.content))
        
        # Run the graph with model_config_id for per-request settings
        result = graph.invoke({
            "messages": langchain_messages,
            "model_config_id": model_config_id
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
