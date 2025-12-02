# LangChain Proxy

A powerful proxy server that provides an OpenAI-compatible API for LangChain applications, featuring advanced RAG (Retrieval-Augmented Generation), tool calling, model management, and an intuitive admin interface.

## Features

- 🚀 **OpenAI-Compatible API**: Drop-in replacement for OpenAI API calls
- 🧠 **Advanced RAG**: Built-in knowledge base with Qdrant vector storage
- 🛠️ **Tool Calling**: Extensible tool system for custom functionality
- 📊 **Model Management**: Versioned model configurations with activation controls
- 🎛️ **Admin UI**: Vue.js-based web interface for easy management
- 📈 **Analytics**: Chat logging and performance monitoring
- 🐳 **Docker Ready**: Complete containerized deployment
- 🔧 **CLI Tools**: Command-line interface for all operations

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/tunghauvan/langchain-proxy.git
cd langchain-proxy

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env

# Start all services
docker-compose up -d

# Access the services:
# - API Server: http://localhost:8000
# - Admin UI: http://localhost:3000
# - API Docs: http://localhost:8000/docs
```

### Manual Installation

```bash
# Install Python dependencies
pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
langchain-proxy-server --init-db

# Start the server
langchain-proxy-server
```

## Configuration

Create a `.env` file with the following variables:

```env
# Ollama Configuration
OLLAMA_API_KEY=your_ollama_key
OLLAMA_API_BASE_URL=https://ollama.com
OLLAMA_API_MODEL=gpt-oss:20b-cloud

# LangSmith Monitoring
LANGSMITH_PROJECT=your_project
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_TRACING=true

# RAG Configuration
RAG_EMBEDDING_ENGINE=openai
RAG_OPENAI_API_BASE_URL=https://api.openai.com/v1
RAG_OPENAI_API_KEY=your_openai_key
RAG_EMBEDDING_MODEL=text-embedding-3-small

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/langchain_proxy
```

## Usage

### CLI Commands

```bash
# Model management
lcp models list
lcp models create --name my-model --base-model gpt-4
lcp models activate my-model

# Tool management
lcp tools list
lcp tools create --name calculator --code-file calculator.py

# Knowledge base operations
lcp kb create --name docs --description "Documentation"
lcp kb import document.pdf --kb-id docs
lcp kb search "How to use the API?"

# Chat interface
lcp chat send "Hello, how are you?"
lcp chat interactive --model my-model
```

### API Usage

The server provides OpenAI-compatible endpoints:

```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy"  # Not required for local deployment
)

response = client.chat.completions.create(
    model="default-model",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Admin Interface

Access the web-based admin interface at `http://localhost:3000` to:
- Manage models and versions
- Configure tools
- Upload knowledge base documents
- View chat logs and analytics
- Monitor system performance

## Architecture

```
langchain-proxy/
├── src/server/
│   ├── server/          # FastAPI application
│   │   ├── main.py      # Server entry point
│   │   ├── config.py    # Configuration management
│   │   └── database.py  # Database models
│   ├── core/            # Business logic
│   │   └── graph.py     # LangGraph workflows
│   ├── cli/             # Command-line interface
│   └── routes/          # API route handlers
├── web/                 # Vue.js admin interface
├── tests/               # Test suite
├── config/              # Configuration files
├── data/                # Knowledge base and tools
└── docker-compose.yml   # Container orchestration
```

## Development

### Setting up Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
isort src/

# Type checking
mypy src/
```

### Running Tests

```bash
# Unit tests
pytest tests/test_unit/

# Integration tests
pytest tests/test_integration/

# All tests with coverage
pytest --cov=server
```

### Building Documentation

```bash
# Install docs dependencies
pip install -e ".[docs]"

# Build docs
cd docs && make html
```

## API Reference

### Core Endpoints

- `POST /v1/chat/completions` - Chat completions (OpenAI compatible)
- `GET /v1/models` - List available models
- `POST /v1/admin/models` - Create custom model
- `GET /v1/admin/models` - List custom models
- `POST /v1/admin/tools` - Create custom tool
- `POST /v1/rag/search` - Search knowledge base
- `POST /v1/rag/import/documents` - Import documents

### Model Management

Models support versioning and can be activated/deactivated:

```bash
# Create a new model version
lcp versions create my-model --version 2.0.0 --tool new-tool

# Activate specific version
lcp versions activate my-model 2.0.0
```

### Tool System

Tools are Python functions that can be called during chat:

```python
def calculate(expression: str) -> float:
    """Calculate mathematical expression"""
    return eval(expression)

# Register tool via CLI or API
lcp tools create --name calculator --code-file calculator.py
```

### Knowledge Base

RAG-enabled knowledge base with document upload and search:

```bash
# Create knowledge base
lcp kb create --name docs

# Import documents
lcp kb import *.pdf --kb-id docs

# Search with context
lcp chat send "What does the documentation say?" --kb-id docs
```

## Deployment

### Production Deployment

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy with proper environment
docker-compose -f docker-compose.prod.yml up -d

# Set up reverse proxy (nginx/caddy)
# Configure SSL certificates
# Set up monitoring and logging
```

### Scaling

The application is designed to scale horizontally:
- Stateless API servers
- Shared PostgreSQL database
- Shared Qdrant vector database
- Load balancer for multiple instances

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Code Style

- Use Black for code formatting
- Use isort for import sorting
- Follow PEP 8 guidelines
- Add type hints
- Write comprehensive tests

## License

MIT License - see LICENSE file for details.

## Support

- 📖 [Documentation](https://github.com/tunghauvan/langchain-proxy#readme)
- 🐛 [Issue Tracker](https://github.com/tunghauvan/langchain-proxy/issues)
- 💬 [Discussions](https://github.com/tunghauvan/langchain-proxy/discussions)

## Changelog

### v1.0.0
- Initial release
- OpenAI-compatible API
- RAG with Qdrant
- Tool calling system
- Model versioning
- Admin UI
- Docker deployment
- CLI tools