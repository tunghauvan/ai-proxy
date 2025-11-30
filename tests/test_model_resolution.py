"""Tests for model name resolution in chat completions endpoint."""

from __future__ import annotations

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def print_separator(char="-", length=50):
    print(char * length)


def test_list_models():
    """Test listing available custom models."""
    print("\n[Test] List Custom Models:")
    print_separator()
    
    response = requests.get(f"{BASE_URL}/v1/admin/models")
    response.raise_for_status()
    
    models = response.json()
    print(f"  Found {len(models)} models:")
    for m in models:
        active_marker = " (active)" if m.get("active") else ""
        print(f"    - {m['name']} (id: {m['id'][:8]}...){active_marker}")
        print(f"      RAG: {m['rag_settings']['enabled']}, Tools: {m['tool_names']}")
    
    assert len(models) > 0, "Should have at least one model"
    return models


def test_chat_with_model_name():
    """Test chat completion with custom model name in 'model' field."""
    print("\n[Test] Chat with Custom Model Name:")
    print_separator()
    
    # First, get available models
    response = requests.get(f"{BASE_URL}/v1/admin/models")
    response.raise_for_status()
    models = response.json()
    
    if not models:
        print("  ⚠ No models found, skipping test")
        return None
    
    # Use the first model's name
    model_name = models[0]["name"]
    print(f"  Using model: {model_name}")
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": "Hello, what time is it?"}
        ],
        "temperature": 0.7
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=120
    )
    response.raise_for_status()
    
    result = response.json()
    print(f"  Response ID: {result['id']}")
    print(f"  Model in response: {result['model']}")
    print(f"  Content preview: {result['choices'][0]['message']['content'][:100]}...")
    
    assert result["model"] == model_name, f"Response model should match request model"
    assert result["choices"][0]["message"]["role"] == "assistant"
    
    return result


def test_chat_with_different_models():
    """Test that different model names use their specific configurations."""
    print("\n[Test] Chat with Different Models:")
    print_separator()
    
    # Get available models
    response = requests.get(f"{BASE_URL}/v1/admin/models")
    response.raise_for_status()
    models = response.json()
    
    if len(models) < 2:
        print("  ⚠ Need at least 2 models to test model switching")
        return None
    
    results = []
    for model in models[:2]:  # Test first 2 models
        model_name = model["name"]
        print(f"\n  Testing model: {model_name}")
        print(f"    RAG: {model['rag_settings']['enabled']}")
        print(f"    Tools: {model['tool_names']}")
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": "What is 2+2?"}
            ],
            "temperature": 0.3
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        response.raise_for_status()
        
        result = response.json()
        print(f"    Response: {result['choices'][0]['message']['content'][:80]}...")
        results.append((model_name, result))
    
    return results


def test_chat_with_unknown_model():
    """Test that unknown model names still work (uses default LLM)."""
    print("\n[Test] Chat with Unknown Model Name:")
    print_separator()
    
    payload = {
        "model": "nonexistent-model-xyz",
        "messages": [
            {"role": "user", "content": "Say hello"}
        ],
        "temperature": 0.7
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=120
    )
    
    # Should not fail - unknown models use default config
    response.raise_for_status()
    
    result = response.json()
    print(f"  Model in request: nonexistent-model-xyz")
    print(f"  Model in response: {result['model']}")
    print(f"  Content: {result['choices'][0]['message']['content'][:100]}...")
    
    # The response should still work
    assert result["choices"][0]["message"]["role"] == "assistant"
    
    return result


def test_model_name_case_insensitive():
    """Test that model name lookup is case-insensitive."""
    print("\n[Test] Model Name Case Insensitivity:")
    print_separator()
    
    # Get first model
    response = requests.get(f"{BASE_URL}/v1/admin/models")
    response.raise_for_status()
    models = response.json()
    
    if not models:
        print("  ⚠ No models found, skipping test")
        return None
    
    original_name = models[0]["name"]
    
    # Test with different case variations
    test_names = [
        original_name.upper(),
        original_name.lower(),
        original_name.title(),
    ]
    
    for name in test_names:
        if name == original_name:
            continue  # Skip if case variation is same
        
        print(f"  Testing: '{name}' (original: '{original_name}')")
        
        payload = {
            "model": name,
            "messages": [
                {"role": "user", "content": "Hi"}
            ],
            "temperature": 0.7
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        response.raise_for_status()
        
        result = response.json()
        print(f"    Response OK: {len(result['choices'][0]['message']['content'])} chars")
    
    return True


def test_chat_with_model_id():
    """Test chat completion using model ID instead of name."""
    print("\n[Test] Chat with Model ID:")
    print_separator()
    
    # Get first model
    response = requests.get(f"{BASE_URL}/v1/admin/models")
    response.raise_for_status()
    models = response.json()
    
    if not models:
        print("  ⚠ No models found, skipping test")
        return None
    
    model_id = models[0]["id"]
    print(f"  Using model ID: {model_id}")
    
    payload = {
        "model": model_id,
        "messages": [
            {"role": "user", "content": "What is the current date?"}
        ],
        "temperature": 0.7
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=120
    )
    response.raise_for_status()
    
    result = response.json()
    print(f"  Model in response: {result['model']}")
    print(f"  Content preview: {result['choices'][0]['message']['content'][:100]}...")
    
    return result


def run_all_tests():
    """Run all model resolution tests."""
    print("=" * 60)
    print("Model Resolution Tests for LangGraph Proxy Server")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    
    tests = [
        ("List Models", test_list_models),
        ("Chat with Model Name", test_chat_with_model_name),
        ("Chat with Different Models", test_chat_with_different_models),
        ("Chat with Unknown Model", test_chat_with_unknown_model),
        ("Model Name Case Insensitive", test_model_name_case_insensitive),
        ("Chat with Model ID", test_chat_with_model_id),
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
    print("Starting model resolution tests...")
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
        import traceback
        traceback.print_exc()
        sys.exit(1)
