# Technical Documentation - AcmeAI Platform

## System Architecture

### Overview
The AcmeAI Platform uses a microservices architecture deployed on Kubernetes. The main components include:

1. **API Gateway** - Handles authentication, rate limiting, and request routing
2. **LLM Service** - Manages connections to various language models
3. **Vector Store Service** - Handles document embeddings and similarity search
4. **Document Processor** - Processes and chunks documents for indexing
5. **Cache Layer** - Redis-based caching for improved performance

### Data Flow
1. User sends a query through the API
2. API Gateway authenticates and routes the request
3. Query is embedded using the embedding model
4. Vector Store performs similarity search
5. Retrieved documents are sent to LLM Service
6. LLM generates response with context
7. Response is cached and returned to user

## API Reference

### Authentication
All API requests require an API key in the header:
```
Authorization: Bearer YOUR_API_KEY
```

### Endpoints

#### POST /v1/chat/completions
Create a chat completion with optional RAG context.

**Request Body:**
```json
{
  "model": "acme-gpt-4",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is your product?"}
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "use_rag": true
}
```

**Response:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1699000000,
  "model": "acme-gpt-4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Our main product is..."
      },
      "finish_reason": "stop"
    }
  ]
}
```

#### POST /v1/documents
Upload a document to the knowledge base.

**Request:**
- Content-Type: multipart/form-data
- file: The document file (PDF, DOCX, TXT, MD)
- metadata: Optional JSON metadata

#### GET /v1/documents
List all documents in the knowledge base.

#### DELETE /v1/documents/{document_id}
Delete a document from the knowledge base.

### Rate Limits
- Starter: 100 requests/minute
- Professional: 1000 requests/minute
- Enterprise: Custom limits

### Error Codes
- 400: Bad Request - Invalid parameters
- 401: Unauthorized - Invalid or missing API key
- 403: Forbidden - Insufficient permissions
- 429: Too Many Requests - Rate limit exceeded
- 500: Internal Server Error

## SDK Examples

### Python
```python
from acme_ai import AcmeClient

client = AcmeClient(api_key="your-api-key")

response = client.chat.completions.create(
    model="acme-gpt-4",
    messages=[{"role": "user", "content": "Hello!"}],
    use_rag=True
)
print(response.choices[0].message.content)
```

### JavaScript
```javascript
const { AcmeClient } = require('acme-ai');

const client = new AcmeClient({ apiKey: 'your-api-key' });

const response = await client.chat.completions.create({
  model: 'acme-gpt-4',
  messages: [{ role: 'user', content: 'Hello!' }],
  useRag: true
});
console.log(response.choices[0].message.content);
```

## Best Practices

### Optimizing RAG Performance
1. Keep documents focused and well-structured
2. Use meaningful file names and metadata
3. Update documents regularly to keep information current
4. Use specific queries for better retrieval accuracy
5. Consider document chunking strategies based on content type

### Security Recommendations
1. Rotate API keys regularly
2. Use environment variables for sensitive data
3. Enable IP whitelisting for production
4. Review access logs periodically
5. Implement proper error handling to avoid data leaks
