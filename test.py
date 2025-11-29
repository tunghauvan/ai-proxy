"""Test script to call the OpenAI-compatible API"""
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()


def test_chat_completion():
    """Test the chat completion endpoint"""
    # Create OpenAI client pointing to our local server
    client = OpenAI(
        api_key="not-needed",  # Our server doesn't require API key
        base_url="http://localhost:8000/v1",
    )
    
    print("=" * 50)
    print("Testing LangGraph Proxy Server")
    print("=" * 50)
    
    # Test 1: Simple chat completion
    print("\n[Test 1] Simple chat completion:")
    print("-" * 30)
    
    response = client.chat.completions.create(
        model=os.getenv("OLLAMA_API_MODEL"),
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! Can you tell me what 2 + 2 equals?"},
        ],
        temperature=0.7,
    )
    
    print(f"Response ID: {response.id}")
    print(f"Model: {response.model}")
    print(f"Message: {response.choices[0].message.content}")
    print(f"Finish Reason: {response.choices[0].finish_reason}")
    print(f"Usage: {response.usage}")
    
    # Test 2: Multi-turn conversation
    print("\n[Test 2] Multi-turn conversation:")
    print("-" * 30)
    
    response = client.chat.completions.create(
        model=os.getenv("OLLAMA_API_MODEL"),
        messages=[
            {"role": "system", "content": "You are a helpful assistant that speaks concisely."},
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a high-level, interpreted programming language known for its readability and versatility."},
            {"role": "user", "content": "What are its main uses?"},
        ],
        temperature=0.7,
    )
    
    print(f"Response: {response.choices[0].message.content}")
    
    # Test 3: Tool usage - asking for current time
    print("\n[Test 3] Tool usage - What time is it?:")
    print("-" * 30)
    
    response = client.chat.completions.create(
        model=os.getenv("OLLAMA_API_MODEL"),
        messages=[
            {"role": "system", "content": "You are a helpful assistant with access to tools. Use the get_datetime tool when asked about the current time or date."},
            {"role": "user", "content": "What time is it?"},
        ],
        temperature=0.7,
    )
    
    print(f"Response: {response.choices[0].message.content}")
    
    print("\n" + "=" * 50)
    print("All tests completed successfully!")
    print("=" * 50)


def test_list_models():
    """Test the list models endpoint"""
    client = OpenAI(
        api_key="not-needed",
        base_url="http://localhost:8000/v1",
    )
    
    print("\n[Test] List models:")
    print("-" * 30)
    
    models = client.models.list()
    for model in models.data:
        print(f"Model ID: {model.id}")
        print(f"Object: {model.object}")
        print(f"Owned by: {model.owned_by}")


if __name__ == "__main__":
    print("Starting API tests...")
    print(f"Using Ollama model: {os.getenv('OLLAMA_API_MODEL')}")
    print()
    
    try:
        test_list_models()
        test_chat_completion()
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure the server is running:")
        print("  docker-compose up -d")
        print("  # or")
        print("  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
