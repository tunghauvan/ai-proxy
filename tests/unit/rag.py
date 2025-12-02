"""RAG-specific tests for the LangGraph Proxy Server (Qdrant + Remote Embeddings)"""
import os
import sys
import time
import requests
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Sample knowledge base documents for testing
SAMPLE_DOCUMENTS = [
    {
        "content": """Acme Corporation - Company Overview

Acme Corporation is a leading technology company founded in 2010.
Our mission is to provide innovative AI solutions for businesses.

Leadership Team:
- CEO: Jane Smith
- CTO: John Doe
- CFO: Sarah Johnson

Headquarters: San Francisco, CA
Employees: 500+
Revenue: $100M annually""",
        "source": "company_info.txt"
    },
    {
        "content": """Acme AI Products - Pricing Plans

Starter Plan: $99/month
- 10,000 API calls
- Basic support
- 1 user

Professional Plan: $499/month  
- 100,000 API calls
- Priority support
- 10 users
- Custom integrations

Enterprise Plan: Contact Sales
- Unlimited API calls
- 24/7 dedicated support
- Unlimited users
- On-premise deployment option""",
        "source": "pricing.txt"
    },
    {
        "content": """Technical Documentation - API Authentication

All API requests require authentication via API key or OAuth2.

API Key Authentication:
Add header: Authorization: Bearer <your-api-key>

OAuth2 Authentication:
1. Register your application
2. Obtain client_id and client_secret
3. Request access token from /oauth/token
4. Use token in Authorization header

Rate Limits:
- Starter: 100 requests/minute
- Professional: 1000 requests/minute
- Enterprise: Custom limits""",
        "source": "technical_docs.md"
    },
    {
        "content": """Frequently Asked Questions (FAQ)

Q: What file formats are supported?
A: We support PDF, DOCX, TXT, MD, JSON, and CSV files.

Q: What is the maximum document size?
A: Maximum document size is 100MB per file.

Q: How long is data retained?
A: Data is retained for 90 days by default. Enterprise plans have configurable retention.

Q: Is my data encrypted?
A: Yes, all data is encrypted at rest and in transit using AES-256 encryption.""",
        "source": "faq.txt"
    }
]


def print_separator(char="-", length=50):
    print(char * length)


def setup_knowledge_base():
    """Clear and import sample documents into the knowledge base"""
    print("\n[Setup] Initializing Knowledge Base:")
    print_separator()
    
    # Create a test knowledge base
    print("  Creating test knowledge base...")
    response = requests.post(
        f"{BASE_URL}/v1/admin/knowledge-bases",
        json={"name": "test_kb", "description": "Test knowledge base for RAG testing"},
        headers={"Content-Type": "application/json"}
    )
    response.raise_for_status()
    kb_data = response.json()
    kb_id = kb_data["id"]
    print(f"  ✓ Created KB '{kb_id}' with collection '{kb_data['collection']}'")
    
    # Clear existing documents
    print("  Clearing existing documents...")
    response = requests.delete(f"{BASE_URL}/v1/rag/clear?kb_id={kb_id}")
    if response.status_code == 200:
        print(f"  ✓ KB cleared: {response.json()}")
    else:
        print(f"  ⚠ Clear response: {response.text}")
    
    time.sleep(1)  # Wait for collection recreation
    
    # Import sample documents
    print("  Importing sample documents...")
    response = requests.post(
        f"{BASE_URL}/v1/rag/import/documents?kb_id={kb_id}",
        json={"documents": SAMPLE_DOCUMENTS},
        headers={"Content-Type": "application/json"}
    )
    response.raise_for_status()
    
    data = response.json()
    print(f"  ✓ Imported {data.get('original_count')} documents -> {data.get('chunks_created')} chunks")
    
    time.sleep(2)  # Wait for indexing
    
    return data, kb_id


def test_rag_stats(kb_id):
    """Test the RAG stats endpoint"""
    print("\n[Test] RAG Stats:")
    print_separator()
    
    response = requests.get(f"{BASE_URL}/v1/rag/stats?kb_id={kb_id}")
    response.raise_for_status()
    
    data = response.json()
    print(f"  RAG Enabled: {data.get('enabled')}")
    print(f"  Document Count: {data.get('document_count')}")
    print(f"  Collection: {data.get('collection')}")
    print(f"  Qdrant: {data.get('qdrant_host')}:{data.get('qdrant_port')}")
    print(f"  Embedding Model: {data.get('embedding_model')}")
    
    assert data.get("enabled") is True, "RAG should be enabled"
    
    return data


def test_rag_search(kb_id):
    """Test the RAG search endpoint"""
    print("\n[Test] RAG Search - Company Info:")
    print_separator()
    
    # Search for company info
    response = requests.post(
        f"{BASE_URL}/v1/rag/search?kb_id={kb_id}",
        json={"query": "What is the pricing for Acme products?", "top_k": 3}
    )
    response.raise_for_status()
    
    data = response.json()
    print(f"  Query: {data.get('query')}")
    print(f"  Results found: {len(data.get('results', []))}")
    
    for i, result in enumerate(data.get("results", []), 1):
        print(f"\n    Result {i}:")
        print(f"      Source: {result.get('source')}")
        print(f"      Content preview: {result.get('content', '')[:100]}...")
    
    assert len(data.get("results", [])) > 0, "Should find relevant documents"
    
    # Verify content relates to pricing
    all_content = " ".join([r.get("content", "").lower() for r in data.get("results", [])])
    assert "pricing" in all_content or "price" in all_content or "$" in all_content, \
        "Results should contain pricing information"
    
    return data


def test_rag_search_technical(kb_id):
    """Test RAG search for technical documentation"""
    print("\n[Test] RAG Search - Technical Docs:")
    print_separator()
    
    response = requests.post(
        f"{BASE_URL}/v1/rag/search?kb_id={kb_id}",
        json={"query": "How do I authenticate API requests?", "top_k": 3}
    )
    response.raise_for_status()
    
    data = response.json()
    print(f"  Query: {data.get('query')}")
    print(f"  Results found: {len(data.get('results', []))}")
    
    for i, result in enumerate(data.get("results", []), 1):
        print(f"\n    Result {i}:")
        print(f"      Source: {result.get('source')}")
        print(f"      Content preview: {result.get('content', '')[:100]}...")
    
    assert len(data.get("results", [])) > 0, "Should find relevant documents"
    
    return data


def test_rag_search_faq(kb_id):
    """Test RAG search for FAQ content"""
    print("\n[Test] RAG Search - FAQ:")
    print_separator()
    
    response = requests.post(
        f"{BASE_URL}/v1/rag/search?kb_id={kb_id}",
        json={"query": "What file formats are supported?", "top_k": 3}
    )
    response.raise_for_status()
    
    data = response.json()
    print(f"  Query: {data.get('query')}")
    print(f"  Results found: {len(data.get('results', []))}")
    
    for i, result in enumerate(data.get("results", []), 1):
        print(f"\n    Result {i}:")
        print(f"      Source: {result.get('source')}")
        print(f"      Content preview: {result.get('content', '')[:100]}...")
    
    assert len(data.get("results", [])) > 0, "Should find relevant documents"
    
    return data


def test_chat_with_rag_context(kb_id):
    """Test chat completion that should use RAG context"""
    print("\n[Test] Chat with RAG Context:")
    print_separator()
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        json={
            "model": os.getenv("OLLAMA_API_MODEL", "gpt-oss:20b-cloud"),
            "messages": [
                {"role": "system", "content": "You are a helpful assistant for Acme Corporation. Answer questions based on the company's knowledge base."},
                {"role": "user", "content": "What pricing plans does Acme offer?"},
            ],
            "temperature": 0.3,
        },
        headers={"X-KB-ID": kb_id, "Content-Type": "application/json"}
    )
    response.raise_for_status()
    
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    print(f"  Response: {content[:500]}...")
    
    # The response should mention pricing info from the KB
    content_lower = content.lower()
    has_pricing_info = any(term in content_lower for term in [
        "starter", "professional", "enterprise", "$99", "$499", "month"
    ])
    
    print(f"\n  Contains pricing info from KB: {has_pricing_info}")
    
    return response


def test_chat_company_info(kb_id):
    """Test chat asking about company information"""
    print("\n[Test] Chat - Company Information:")
    print_separator()
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        json={
            "model": os.getenv("OLLAMA_API_MODEL", "gpt-oss:20b-cloud"),
            "messages": [
                {"role": "system", "content": "You are a helpful assistant for Acme Corporation."},
                {"role": "user", "content": "Who is the CEO of Acme Corporation?"},
            ],
            "temperature": 0.3,
        },
        headers={"X-KB-ID": kb_id, "Content-Type": "application/json"}
    )
    response.raise_for_status()
    
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    print(f"  Response: {content}")
    
    # Should mention Jane Smith (from knowledge base)
    content_lower = content.lower()
    has_ceo_info = "jane" in content_lower or "smith" in content_lower
    print(f"\n  Contains CEO info (Jane Smith): {has_ceo_info}")
    
    return response


def test_chat_technical_question(kb_id):
    """Test chat with technical question from docs"""
    print("\n[Test] Chat - Technical Question:")
    print_separator()
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        json={
            "model": os.getenv("OLLAMA_API_MODEL", "gpt-oss:20b-cloud"),
            "messages": [
                {"role": "system", "content": "You are a technical support assistant for Acme Corporation."},
                {"role": "user", "content": "What is the maximum document size I can upload to AcmeAI?"},
            ],
            "temperature": 0.3,
        },
        headers={"X-KB-ID": kb_id, "Content-Type": "application/json"}
    )
    response.raise_for_status()
    
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    print(f"  Response: {content}")
    
    # Should mention 100MB (from FAQ)
    content_lower = content.lower()
    has_size_info = "100" in content_lower or "mb" in content_lower
    print(f"\n  Contains size info (100MB): {has_size_info}")
    
    return response


def test_rag_reload(kb_id):
    """Test reloading the RAG knowledge base"""
    print("\n[Test] RAG Reload:")
    print_separator()
    
    response = requests.post(f"{BASE_URL}/v1/rag/reload?kb_id={kb_id}")
    response.raise_for_status()
    
    data = response.json()
    print(f"  Status: {data.get('status')}")
    print(f"  Message: {data.get('message')}")
    print(f"  Stats: {data.get('stats')}")
    
    assert data.get("status") == "success", "Reload should succeed"
    
    return data


def run_all_tests():
    """Run all RAG tests"""
    print("=" * 60)
    print("RAG Tests for LangGraph Proxy Server")
    print("Qdrant + Remote Embeddings Integration")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Model: {os.getenv('OLLAMA_API_MODEL', 'gpt-oss:20b-cloud')}")
    
    # Setup: Import sample documents
    try:
        setup_data, kb_id = setup_knowledge_base()
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return False
    
    tests = [
        ("RAG Stats", lambda: test_rag_stats(kb_id)),
        ("RAG Search - Company", lambda: test_rag_search(kb_id)),
        ("RAG Search - Technical", lambda: test_rag_search_technical(kb_id)),
        ("RAG Search - FAQ", lambda: test_rag_search_faq(kb_id)),
        ("Chat with RAG", lambda: test_chat_with_rag_context(kb_id)),
        ("Chat - Company Info", lambda: test_chat_company_info(kb_id)),
        ("Chat - Technical", lambda: test_chat_technical_question(kb_id)),
        ("RAG Reload", lambda: test_rag_reload(kb_id)),
    ]
    
    results = []
    for name, test_fn in tests:
        try:
            test_fn()
            results.append((name, "PASSED", None))
            print(f"\n  ✅ {name}: PASSED")
        except AssertionError as e:
            results.append((name, "FAILED", str(e)))
            print(f"\n  ❌ {name}: FAILED - {e}")
        except Exception as e:
            results.append((name, "ERROR", str(e)))
            print(f"\n  💥 {name}: ERROR - {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for r in results if r[1] == "PASSED")
    failed = sum(1 for r in results if r[1] == "FAILED")
    errors = sum(1 for r in results if r[1] == "ERROR")
    
    print(f"  Total: {len(results)}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Errors: {errors}")
    
    if failed > 0 or errors > 0:
        print("\n  Failed/Error tests:")
        for name, status, msg in results:
            if status != "PASSED":
                print(f"    - {name}: {status} - {msg}")
    
    print("=" * 60)
    return passed == len(results)


if __name__ == "__main__":
    import sys
    
    print("Starting RAG tests...")
    print()
    
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ Connection Error: Could not connect to {BASE_URL}")
        print("\nMake sure the server is running:")
        print("  docker-compose up -d")
        print("  # or")
        print("  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
