"""LangGraph agent using Ollama API with tools and RAG (Qdrant + Remote Embeddings)"""
import os
from datetime import datetime
from typing import TypedDict, Annotated, Sequence, Literal, List, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
import operator
import httpx

# RAG Configuration
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))

def is_rag_enabled() -> bool:
    """Expose the RAG toggle so callers can gate RAG endpoints."""
    return RAG_ENABLED

# Qdrant Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "knowledge_base")

# Remote Embedding Configuration
RAG_EMBEDDING_ENGINE = os.getenv("RAG_EMBEDDING_ENGINE", "openai")
RAG_OPENAI_API_BASE_URL = os.getenv("RAG_OPENAI_API_BASE_URL", "https://api.openai.com/v1")
RAG_OPENAI_API_KEY = os.getenv("RAG_OPENAI_API_KEY", "")
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-ada-002")

# Global instances
_vector_store: Optional[QdrantVectorStore] = None
_embeddings: Optional[OpenAIEmbeddings] = None
_qdrant_client: Optional[QdrantClient] = None


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


def ensure_collection_exists():
    """Ensure Qdrant collection exists, create if not"""
    client = get_qdrant_client()
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    
    if QDRANT_COLLECTION not in collection_names:
        # Get embedding dimension by creating a test embedding
        embeddings = get_embeddings()
        test_embedding = embeddings.embed_query("test")
        embedding_dim = len(test_embedding)
        
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=qdrant_models.VectorParams(
                size=embedding_dim,
                distance=qdrant_models.Distance.COSINE
            )
        )
        print(f"Created Qdrant collection '{QDRANT_COLLECTION}' with dimension {embedding_dim}")
    return True


def get_vector_store() -> Optional[QdrantVectorStore]:
    """Get or create the vector store"""
    global _vector_store
    
    if not RAG_ENABLED:
        return None
    
    if _vector_store is None:
        try:
            ensure_collection_exists()
            embeddings = get_embeddings()
            _vector_store = QdrantVectorStore(
                client=get_qdrant_client(),
                collection_name=QDRANT_COLLECTION,
                embedding=embeddings,
            )
            print(f"Connected to Qdrant vector store: {QDRANT_COLLECTION}")
        except Exception as e:
            print(f"Error connecting to Qdrant: {e}")
            return None
    
    return _vector_store


def retrieve_relevant_context(query: str, k: int = None) -> List[Document]:
    """Retrieve relevant documents for a query"""
    if k is None:
        k = RAG_TOP_K
    
    vector_store = get_vector_store()
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


# Define tools
@tool
def get_datetime() -> str:
    """Get the current date and time. Use this tool when the user asks about the current time or date."""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for relevant information. Use this tool when you need to find specific information from the knowledge base documents."""
    docs = retrieve_relevant_context(query, k=RAG_TOP_K)
    if not docs:
        return "No relevant information found in the knowledge base."
    return format_context(docs)


# List of available tools
tools = [get_datetime, search_knowledge_base]


def create_ollama_llm():
    """Create an Ollama LLM client using OpenAI-compatible API"""
    base_url = os.getenv("OLLAMA_API_BASE_URL", "http://localhost:11434")
    api_key = os.getenv("OLLAMA_API_KEY", "ollama")
    
    # Ensure base_url ends with /v1 for OpenAI compatibility
    if not base_url.endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"
    
    # Create custom HTTP client with Authorization header for Ollama Cloud
    http_client = httpx.Client(
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=120.0
    )
    
    return ChatOpenAI(
        model=os.getenv("OLLAMA_API_MODEL", "gpt-oss:20b-cloud"),
        api_key=api_key,
        base_url=base_url,
        temperature=0.7,
        http_client=http_client,
    )


def retrieval_node(state: AgentState) -> dict:
    """Node that retrieves relevant context from the knowledge base"""
    if not RAG_ENABLED:
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
    
    # Retrieve relevant documents
    docs = retrieve_relevant_context(last_human_msg)
    context = format_context(docs)
    
    return {"context": context}


def agent_node(state: AgentState) -> dict:
    """Node that handles chat interactions with tool binding and RAG context"""
    llm = create_ollama_llm()
    llm_with_tools = llm.bind_tools(tools)
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
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_messages = []
    
    # Create a mapping of tool names to tool functions
    tool_map = {t.name: t for t in tools}
    
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
def reload_knowledge_base():
    """Force reload of the vector store connection"""
    global _vector_store
    _vector_store = None
    return get_vector_store()


def import_documents(documents: List[Document]) -> dict:
    """Import documents into the knowledge base via API"""
    vector_store = get_vector_store()
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


def import_texts(texts: List[str], metadatas: Optional[List[dict]] = None) -> dict:
    """Import raw texts into the knowledge base"""
    vector_store = get_vector_store()
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


def clear_knowledge_base() -> dict:
    """Clear all documents from the knowledge base"""
    client = get_qdrant_client()
    try:
        client.delete_collection(collection_name=QDRANT_COLLECTION)
        # Reset global vector store to force re-creation
        global _vector_store
        _vector_store = None
        ensure_collection_exists()
        return {"status": "success", "message": f"Collection '{QDRANT_COLLECTION}' cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_kb_stats() -> dict:
    """Get statistics about the knowledge base"""
    if not RAG_ENABLED:
        return {"enabled": False, "document_count": 0}
    
    try:
        client = get_qdrant_client()
        collection_info = client.get_collection(collection_name=QDRANT_COLLECTION)
        return {
            "enabled": True,
            "collection": QDRANT_COLLECTION,
            "document_count": collection_info.points_count,
            "status": collection_info.status.value,
            "qdrant_host": QDRANT_HOST,
            "qdrant_port": QDRANT_PORT,
            "embedding_model": RAG_EMBEDDING_MODEL,
        }
    except Exception as e:
        return {"enabled": True, "document_count": 0, "error": str(e)}
