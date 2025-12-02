"""LangGraph agent using Ollama API with tools and RAG (Qdrant + Remote Embeddings)"""
import os
import hashlib
import json
import traceback
from datetime import datetime
from typing import TypedDict, Annotated, Sequence, Literal, List, Optional, Dict, Any, Callable
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool, Tool, StructuredTool
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
import operator
import httpx
from pydantic import BaseModel, Field, create_model
from langchain_proxy.server.config import get_active_model, get_config_store, get_tool_store, get_kb_store, KnowledgeBase

# RAG Configuration helpers live inside the admin config store
def is_rag_enabled(model_id: Optional[str] = None) -> bool:
    """Expose the RAG toggle so callers can gate RAG endpoints."""
    return get_rag_settings(model_id).enabled


def get_rag_settings(model_id: Optional[str] = None):
    """Return the RAG settings for a specific model or the active model."""
    if model_id:
        model = get_config_store().get_model(model_id)
        if model:
            return model.rag_settings
    return get_active_model().rag_settings


def _get_model_for_request(model_id: Optional[str] = None):
    """Get the model config for a request (by ID or active)."""
    if model_id:
        model = get_config_store().get_model(model_id)
        if model:
            return model
    return get_active_model()

# Qdrant Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# Remote Embedding Configuration
RAG_EMBEDDING_ENGINE = os.getenv("RAG_EMBEDDING_ENGINE", "openai")
RAG_OPENAI_API_BASE_URL = os.getenv("RAG_OPENAI_API_BASE_URL", "https://api.openai.com/v1")
RAG_OPENAI_API_KEY = os.getenv("RAG_OPENAI_API_KEY", "")
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-ada-002")

# Global instances
_vector_store: Optional[QdrantVectorStore] = None
_embeddings: Optional[OpenAIEmbeddings] = None
_qdrant_client: Optional[QdrantClient] = None
_llm_cache: Dict[str, ChatOpenAI] = {}  # Cache LLM clients by config hash


def get_qdrant_client() -> QdrantClient:
    """Get or create Qdrant client"""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    return _qdrant_client


def get_embeddings() -> OpenAIEmbeddings:
    """Get or create embeddings model using remote OpenAI-compatible API"""
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            model=RAG_EMBEDDING_MODEL,
            openai_api_key=RAG_OPENAI_API_KEY,
            openai_api_base=RAG_OPENAI_API_BASE_URL,
            check_embedding_ctx_length=False,  # Disable tokenization, send raw text
        )
    return _embeddings


def ensure_collection_exists(kb_id: Optional[str] = None):
    """Ensure Qdrant collection exists, create if not"""
    client = get_qdrant_client()
    
    # Get collection name from KB or use default
    if kb_id:
        kb = get_kb_store().get_knowledge_base(kb_id)
        if not kb:
            raise ValueError(f"Knowledge base '{kb_id}' not found")
        collection_name = kb.collection
    else:
        # Default collection for backwards compatibility
        collection_name = os.getenv("QDRANT_COLLECTION", "knowledge_base")
    
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    
    if collection_name not in collection_names:
        embeddings = get_embeddings()
        test_embedding = embeddings.embed_query("test")
        embedding_dim = len(test_embedding)
        
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=embedding_dim,
                distance=qdrant_models.Distance.COSINE
            )
        )
        print(f"Created Qdrant collection '{collection_name}' with dimension {embedding_dim}")
    return True


def get_vector_store(kb_id: Optional[str] = None) -> Optional[QdrantVectorStore]:
    """Get or create the vector store for a specific knowledge base"""
    global _vector_store
    
    # Get collection name from KB or use default
    if kb_id:
        kb = get_kb_store().get_knowledge_base(kb_id)
        if not kb:
            return None
        collection_name = kb.collection
    else:
        # Default collection for backwards compatibility
        collection_name = os.getenv("QDRANT_COLLECTION", "knowledge_base")
    
    # Check if we need a different collection than the cached one
    if _vector_store is not None:
        # If the collection changed, we need to create a new store
        try:
            current_collection = _vector_store.collection_name
            if current_collection != collection_name:
                _vector_store = None
        except:
            pass
    
    if _vector_store is None:
        try:
            ensure_collection_exists(kb_id)
            embeddings = get_embeddings()
            _vector_store = QdrantVectorStore(
                client=get_qdrant_client(),
                collection_name=collection_name,
                embedding=embeddings,
            )
            print(f"Connected to Qdrant vector store: {collection_name}")
        except Exception as e:
            print(f"Error connecting to Qdrant: {e}")
            return None
    
    return _vector_store


def retrieve_relevant_context(query: str, k: Optional[int] = None, kb_id: Optional[str] = None) -> List[Document]:
    """Retrieve relevant documents for a query"""
    if k is None:
        # Use default k if no kb_id, or get from model if kb_id not provided
        if kb_id:
            k = 3  # Default for KB-specific queries
        else:
            k = get_rag_settings().top_k
    
    vector_store = get_vector_store(kb_id)
    if vector_store is None:
        return []
    
    try:
        docs = vector_store.similarity_search(query, k=k)
        return docs
    except Exception as e:
        print(f"Error retrieving documents: {e}")
        return []


def format_context(documents: List[Document]) -> str:
    """Format retrieved documents into context string"""
    if not documents:
        return ""
    
    context_parts = []
    for i, doc in enumerate(documents, 1):
        source = doc.metadata.get("source", "unknown")
        context_parts.append(f"[Source {i}: {source}]\n{doc.page_content}")
    
    return "\n\n---\n\n".join(context_parts)


class AgentState(TypedDict):
    """State for the agent graph"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    context: Optional[str]  # Retrieved RAG context
    model_config_id: Optional[str]  # Custom model ID for per-request config
    kb_id: Optional[str]  # Knowledge base ID for per-request KB selection


# Define builtin tools
@tool
def get_datetime() -> str:
    """Get the current date and time. Use this tool when the user asks about the current time or date."""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for relevant information. Use this tool when you need to find specific information from the knowledge base documents."""
    docs = retrieve_relevant_context(query)
    if not docs:
        return "No relevant information found in the knowledge base."
    return format_context(docs)


# Registered builtin tools that can be enabled on each custom model
BUILTIN_TOOLS = {
    get_datetime.name: get_datetime,
    search_knowledge_base.name: search_knowledge_base,
}

# Cache for dynamically created custom tools
_custom_tools_cache: Dict[str, StructuredTool] = {}


def _create_safe_execution_context() -> Dict[str, Any]:
    """Create a safe execution context for custom tool code."""
    import math
    import re as regex
    import json as json_module
    from datetime import datetime as dt, timedelta, date
    
    return {
        # Safe builtins
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "filter": filter,
        "float": float,
        "format": format,
        "int": int,
        "isinstance": isinstance,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "print": print,
        "range": range,
        "reversed": reversed,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "type": type,
        "zip": zip,
        # Safe modules
        "math": math,
        "re": regex,
        "json": json_module,
        "datetime": dt,
        "timedelta": timedelta,
        "date": date,
    }


def _create_dynamic_tool(tool_config) -> Optional[StructuredTool]:
    """Create a LangChain tool from a database tool configuration with Python code."""
    if not tool_config.function_code:
        return None
    
    tool_name = tool_config.name
    tool_description = tool_config.description
    function_code = tool_config.function_code
    parameters = list(tool_config.parameters)  # Make a copy to avoid mutation issues
    
    # If no parameters defined, try to infer from function signature
    if not parameters:
        import ast
        try:
            tree = ast.parse(function_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Found a function, extract parameters
                    for arg in node.args.args:
                        param_name = arg.arg
                        # Try to get type annotation
                        param_type = "string"  # default
                        if arg.annotation:
                            if isinstance(arg.annotation, ast.Name):
                                type_name = arg.annotation.id.lower()
                                if type_name in ("str", "string"):
                                    param_type = "string"
                                elif type_name in ("int", "integer"):
                                    param_type = "integer"
                                elif type_name in ("float", "number"):
                                    param_type = "number"
                                elif type_name in ("bool", "boolean"):
                                    param_type = "boolean"
                                elif type_name in ("list", "array"):
                                    param_type = "array"
                                elif type_name in ("dict", "object"):
                                    param_type = "object"
                        
                        # Create a simple param object
                        class InferredParam:
                            def __init__(self, name, ptype, desc, required, default):
                                self.name = name
                                self.type = ptype
                                self.description = desc
                                self.required = required
                                self.default = default
                        
                        p = InferredParam(param_name, param_type, f"Parameter: {param_name}", True, None)
                        parameters.append(p)
                    break
        except Exception as e:
            print(f"Warning: Could not infer parameters from function code: {e}")
    
    # Debug: print inferred parameters
    if parameters:
        print(f"Tool '{tool_name}' has {len(parameters)} parameters: {[p.name for p in parameters]}")
    
    # Build pydantic model for parameters
    field_definitions = {}
    for param in parameters:
        param_name = param.name
        param_type = param.type
        param_desc = param.description
        param_required = param.required
        param_default = param.default
        
        # Map type string to Python type
        type_mapping = {
            "string": str,
            "number": float,
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        python_type = type_mapping.get(param_type, str)
        
        if param_required:
            field_definitions[param_name] = (python_type, Field(description=param_desc))
        else:
            field_definitions[param_name] = (Optional[python_type], Field(default=param_default, description=param_desc))
    
    # Create dynamic pydantic model for args
    if field_definitions:
        ArgsModel = create_model(f"{tool_name}_args", **field_definitions)
        print(f"Tool '{tool_name}' ArgsModel created with schema: {ArgsModel.model_json_schema()}")
    else:
        ArgsModel = None
        print(f"Tool '{tool_name}' has no ArgsModel (no field_definitions)")
    
    # Build a wrapper function with the correct signature
    # We need to capture the function_code and tool_name in the closure
    param_names = [p.name for p in parameters] if parameters else []
    
    def make_executor(fn_code, t_name, p_names):
        def execute_custom_tool(**kwargs) -> str:
            """Execute the custom tool code."""
            try:
                # Create safe execution context
                safe_globals = _create_safe_execution_context()
                safe_locals = {}
                
                # Execute the function code to define the function
                exec(fn_code, safe_globals, safe_locals)
                
                # Find the main function (should be named same as tool or 'main' or 'run')
                func = None
                for name in [t_name, "main", "run", "execute"]:
                    if name in safe_locals and callable(safe_locals[name]):
                        func = safe_locals[name]
                        break
                
                # If no named function found, look for any callable
                if func is None:
                    for name, obj in safe_locals.items():
                        if callable(obj) and not name.startswith("_"):
                            func = obj
                            break
                
                if func is None:
                    return f"Error: No executable function found in tool code. Define a function named '{t_name}', 'main', 'run', or 'execute'."
                
                # Call the function with the provided kwargs
                result = func(**kwargs)
                
                return str(result) if result is not None else "Tool executed successfully."
                
            except Exception as e:
                import traceback
                return f"Error executing tool: {str(e)}\n{traceback.format_exc()}"
        
        return execute_custom_tool
    
    executor = make_executor(function_code, tool_name, param_names)
    
    # Create the structured tool - use StructuredTool directly to ensure args_schema is respected
    if ArgsModel:
        return StructuredTool(
            func=executor,
            name=tool_name,
            description=tool_description,
            args_schema=ArgsModel,
        )
    else:
        return StructuredTool.from_function(
            func=executor,
            name=tool_name,
            description=tool_description,
        )


def _get_custom_tools() -> Dict[str, StructuredTool]:
    """Get all custom tools with function code, creating them dynamically."""
    global _custom_tools_cache
    
    tool_store = get_tool_store()
    custom_tool_configs = tool_store.get_custom_tools_with_code()
    
    # Create tools for any new configs
    for config in custom_tool_configs:
        if config.name not in _custom_tools_cache:
            tool = _create_dynamic_tool(config)
            if tool:
                _custom_tools_cache[config.name] = tool
                print(f"Registered custom tool: {config.name}")
    
    # Remove any tools that no longer exist
    current_names = {c.name for c in custom_tool_configs}
    to_remove = [name for name in _custom_tools_cache if name not in current_names]
    for name in to_remove:
        del _custom_tools_cache[name]
        print(f"Unregistered custom tool: {name}")
    
    return _custom_tools_cache


def get_all_registered_tools() -> Dict[str, Any]:
    """Get all registered tools (builtin + custom)."""
    all_tools = dict(BUILTIN_TOOLS)
    all_tools.update(_get_custom_tools())
    return all_tools


def get_active_tools(model_id: Optional[str] = None) -> List[Tool]:
    """Return the tool instances selected for a specific model or the active model."""
    model = _get_model_for_request(model_id)
    active_tool_names = model.tool_names
    all_tools = get_all_registered_tools()
    return [all_tools[name] for name in active_tool_names if name in all_tools]


def reload_custom_tools():
    """Force reload of custom tools from database."""
    global _custom_tools_cache
    _custom_tools_cache = {}
    return _get_custom_tools()


def create_ollama_llm():
    """Create an Ollama LLM client using OpenAI-compatible API (default config)"""
    return create_llm_for_model(None)


def create_llm_for_model(model_id: Optional[str] = None) -> ChatOpenAI:
    """Create an LLM client configured for a specific custom model or default.
    
    Uses per-model base_model and model_params if available.
    Caches clients by configuration hash to avoid recreation.
    """
    global _llm_cache
    
    # Get model config
    custom_model = _get_model_for_request(model_id)
    
    # Determine base model
    base_model = custom_model.base_model if custom_model.base_model else os.getenv("OLLAMA_API_MODEL", "gpt-oss:20b-cloud")
    
    # Get model params with safe defaults
    model_params = custom_model.model_params if custom_model.model_params else {}
    temperature = model_params.get("temperature", 0.7)
    max_tokens = model_params.get("max_tokens", None)
    top_p = model_params.get("top_p", None)
    
    # Create cache key from config
    cache_key_data = {
        "base_model": base_model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
    }
    cache_key = hashlib.md5(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()
    
    # Return cached client if available
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]
    
    # Create new client
    base_url = os.getenv("OLLAMA_API_BASE_URL", "http://localhost:11434")
    api_key = os.getenv("OLLAMA_API_KEY", "ollama")
    
    # Ensure base_url ends with /v1 for OpenAI compatibility
    if not base_url.endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"
    
    # Create custom HTTP client with Authorization header
    http_client = httpx.Client(
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=120.0
    )
    
    # Build kwargs for ChatOpenAI
    llm_kwargs: Dict[str, Any] = {
        "model": base_model,
        "api_key": api_key,
        "base_url": base_url,
        "temperature": temperature,
        "http_client": http_client,
    }
    if max_tokens:
        llm_kwargs["max_tokens"] = max_tokens
    if top_p:
        llm_kwargs["top_p"] = top_p
    
    llm = ChatOpenAI(**llm_kwargs)
    
    # Cache and return
    _llm_cache[cache_key] = llm
    return llm


def retrieval_node(state: AgentState) -> dict:
    """Node that retrieves relevant context from the knowledge base"""
    model_id = state.get("model_config_id")
    kb_id = state.get("kb_id")
    
    if not is_rag_enabled(model_id):
        return {"context": None}
    
    messages = state["messages"]
    
    # Get the last human message for retrieval
    last_human_msg = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human_msg = msg.content
            break
    
    if not last_human_msg:
        return {"context": None}
    
    # Retrieve relevant documents using KB-specific settings
    docs = retrieve_relevant_context(last_human_msg, kb_id=kb_id)
    context = format_context(docs)
    
    return {"context": context}


def agent_node(state: AgentState) -> dict:
    """Node that handles chat interactions with tool binding and RAG context"""
    model_id = state.get("model_config_id")
    llm = create_llm_for_model(model_id)
    llm_with_tools = llm.bind_tools(get_active_tools(model_id))
    messages = list(state["messages"])
    
    # If we have RAG context, inject it into the system message
    context = state.get("context")
    if context:
        rag_system_content = f"""You have access to a knowledge base with the following relevant information:

{context}

Use this context to help answer the user's question. If the context is not relevant to the question, you can ignore it."""
        
        # Find existing system message or prepend new one
        has_system = False
        for i, msg in enumerate(messages):
            if isinstance(msg, SystemMessage):
                # Append RAG context to existing system message
                messages[i] = SystemMessage(content=f"{msg.content}\n\n{rag_system_content}")
                has_system = True
                break
        
        if not has_system:
            messages.insert(0, SystemMessage(content=rag_system_content))
    
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def tool_node(state: AgentState) -> dict:
    """Node that executes tools"""
    model_id = state.get("model_config_id")
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_messages = []
    
    # Create a mapping of tool names to tool functions
    active_tools = get_active_tools(model_id)
    tool_map = {t.name: t for t in active_tools}
    
    # Execute each tool call
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        if tool_name in tool_map:
            result = tool_map[tool_name].invoke(tool_args)
            tool_messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"],
                    name=tool_name
                )
            )
    
    return {"messages": tool_messages}


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """Determine if we should continue to tools or end"""
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the LLM made tool calls, route to the tools node
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    # Otherwise, end the conversation
    return "end"


def create_graph():
    """Create the LangGraph workflow with tools and RAG"""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    
    # Set entry point - start with retrieval
    workflow.set_entry_point("retrieval")
    
    # After retrieval, go to agent
    workflow.add_edge("retrieval", "agent")
    
    # Add conditional edge from agent
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    
    # After tools, go back to agent
    workflow.add_edge("tools", "agent")
    
    # Compile and return
    return workflow.compile()


# Create the graph instance
graph = create_graph()


# Utility functions for managing the knowledge base
def reload_knowledge_base(kb_id: Optional[str] = None):
    """Force reload of the vector store connection"""
    global _vector_store
    _vector_store = None
    return get_vector_store(kb_id)


def import_documents(documents: List[Document], kb_id: Optional[str] = None) -> dict:
    """Import documents into the knowledge base via API"""
    vector_store = get_vector_store(kb_id)
    if vector_store is None:
        raise ValueError("Vector store not initialized. Check Qdrant connection.")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    splits = text_splitter.split_documents(documents)
    
    # Add documents to vector store
    vector_store.add_documents(splits)
    
    return {
        "original_documents": len(documents),
        "chunks_created": len(splits)
    }


def import_texts(texts: List[str], metadatas: Optional[List[dict]] = None, kb_id: Optional[str] = None) -> dict:
    """Import raw texts into the knowledge base"""
    vector_store = get_vector_store(kb_id)
    if vector_store is None:
        raise ValueError("Vector store not initialized. Check Qdrant connection.")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    
    # Create documents from texts
    if metadatas is None:
        metadatas = [{"source": f"text_{i}"} for i in range(len(texts))]
    
    documents = [Document(page_content=t, metadata=m) for t, m in zip(texts, metadatas)]
    splits = text_splitter.split_documents(documents)
    
    # Add documents to vector store
    vector_store.add_documents(splits)
    
    return {
        "original_texts": len(texts),
        "chunks_created": len(splits)
    }


def clear_knowledge_base(kb_id: Optional[str] = None) -> dict:
    """Clear all documents from the knowledge base"""
    client = get_qdrant_client()
    
    # Get collection name from KB or use default
    if kb_id:
        kb = get_kb_store().get_knowledge_base(kb_id)
        if not kb:
            raise ValueError(f"Knowledge base '{kb_id}' not found")
        collection_name = kb.collection
    else:
        # Default collection for backwards compatibility
        collection_name = os.getenv("QDRANT_COLLECTION", "knowledge_base")
    
    try:
        client.delete_collection(collection_name=collection_name)
        # Reset global vector store to force re-creation
        global _vector_store
        _vector_store = None
        ensure_collection_exists(kb_id)
        return {"status": "success", "message": f"Collection '{collection_name}' cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_kb_stats(kb_id: Optional[str] = None) -> dict:
    """Get statistics about the knowledge base"""
    # Get collection name from KB or use default
    if kb_id:
        kb = get_kb_store().get_knowledge_base(kb_id)
        if not kb:
            return {"enabled": False, "document_count": 0, "error": f"Knowledge base '{kb_id}' not found"}
        collection_name = kb.collection
    else:
        # Default collection for backwards compatibility
        collection_name = os.getenv("QDRANT_COLLECTION", "knowledge_base")
    
    try:
        client = get_qdrant_client()
        collection_info = client.get_collection(collection_name=collection_name)
        return {
            "enabled": True,
            "collection": collection_name,
            "document_count": collection_info.points_count,
            "status": collection_info.status.value,
            "qdrant_host": QDRANT_HOST,
            "qdrant_port": QDRANT_PORT,
            "embedding_model": RAG_EMBEDDING_MODEL,
        }
    except Exception as e:
        return {"enabled": True, "document_count": 0, "error": str(e)}


def list_kb_documents(kb_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> dict:
    """List documents in the knowledge base"""
    # Get collection name from KB or use default
    if kb_id:
        kb = get_kb_store().get_knowledge_base(kb_id)
        if not kb:
            return {"error": f"Knowledge base '{kb_id}' not found", "documents": []}
        collection_name = kb.collection
    else:
        # Default collection for backwards compatibility
        collection_name = os.getenv("QDRANT_COLLECTION", "knowledge_base")
    
    try:
        client = get_qdrant_client()
        
        # Check if collection exists
        try:
            collection_info = client.get_collection(collection_name=collection_name)
        except Exception:
            return {"error": f"Collection '{collection_name}' not found", "documents": []}
        
        # Query points with payload (metadata)
        points = client.scroll(
            collection_name=collection_name,
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        documents = []
        for point in points[0]:  # points[0] contains the actual points
            payload = point.payload or {}
            documents.append({
                "id": point.id,
                "content": payload.get("page_content", ""),
                "source": payload.get("metadata", {}).get("source", "unknown"),
                "metadata": payload.get("metadata", {})
            })
        
        return {
            "collection": collection_name,
            "total_count": collection_info.points_count,
            "returned_count": len(documents),
            "limit": limit,
            "offset": offset,
            "documents": documents
        }
    except Exception as e:
        return {"error": str(e), "documents": []}
