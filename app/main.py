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
        print("RAG is disabled (set RAG_ENABLED=true to enable)")
    
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
            "message": "RAG is disabled (RAG_ENABLED=false). Enable it to see stats.",
        }
    return get_kb_stats()


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
            detail="RAG features are disabled (RAG_ENABLED=false). Set RAG_ENABLED=true to enable.",
        )


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """Chat completions endpoint - OpenAI compatible"""
    try:
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
        
        # Run the graph
        result = graph.invoke({"messages": langchain_messages})
        
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
