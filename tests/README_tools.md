# Tool Testing Script

This test script (`tests/test_tools.py`) validates the tool creation and usage functionality in the LangChain proxy system.

## What it tests:

1. **Tool Management API**
   - List available tools
   - List detailed tool information
   - Create tool metadata (note: this is metadata only, actual tools need code implementation)

2. **Model Management with Tools**
   - Create models configured with tools
   - Activate models
   - List models

3. **Tool Usage in Chat**
   - Test datetime tool functionality
   - Test knowledge base search tool
   - Verify tool calling works in chat completions

## Running the tests:

```bash
# Make sure the server is running
docker-compose up -d

# Run the tests
python3 tests/test_tools.py
```

## Expected Output:

The script should show all tests passing, demonstrating that:
- Tools can be managed via the admin API
- Models can be configured with tools
- Tools are functional in chat completions

## Important Notes:

- **Tool Creation**: The admin API allows creating tool metadata, but functional tools must be implemented in `app/graph.py`
- **Existing Tools**: The system comes with `get_datetime` and `search_knowledge_base` tools
- **Model Requirements**: Models must have at least one tool configured

## Adding New Tools:

To add functional tools:

1. Define the tool function in `app/graph.py` with `@tool` decorator
2. Add to `REGISTERED_TOOLS` dictionary
3. Add name to `AVAILABLE_TOOL_NAMES` in `app/config.py`
4. Restart the server

Example:
```python
@tool
def calculator(expression: str) -> str:
    """Calculate mathematical expressions."""
    try:
        result = eval(expression, {"__builtins__": {}})
        return str(result)
    except Exception as e:
        return f"Error: {e}"

REGISTERED_TOOLS = {
    get_datetime.name: get_datetime,
    search_knowledge_base.name: search_knowledge_base,
    calculator.name: calculator,  # Add new tool
}
```</content>
<parameter name="filePath">/Users/vantunghau/interspace/langchain-proxy/tests/README_tools.md