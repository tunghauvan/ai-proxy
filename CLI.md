# LangChain Proxy CLI Reference

## CLI Structure

The CLI is organized into command groups:

```
lcp [OPTIONS] COMMAND [ARGS]...

Options:
  -u, --url TEXT     Server base URL (default: http://localhost:8000)
  -v, --verbose      Enable verbose output
  --help             Show help message

Commands:
  models     Model management
  tools      Tool management
  kb         Knowledge base management
  chat       Chat interaction
  versions   Model version management
  logs       Chat logs for debugging
  test       Testing commands
  config     Show CLI configuration
  shell      Open Python shell
```

## Model Management

### List Models

```bash
./lcp models list [OPTIONS]

Options:
  --json, -j    Output as JSON
```

**Example:**
```bash
./lcp models list
```

### Get Model Details

```bash
./lcp models get <model-identifier>

# model-identifier can be model ID or name
```

**Examples:**
```bash
./lcp models get default-model
./lcp models get abc123-def456
```

### Create Model

```bash
./lcp models create [OPTIONS]

Options:
  -n, --name TEXT              Model name (required)
  -v, --version TEXT           Model version (default: 1.0.0)
  -b, --base-model TEXT        Base LLM model
  --enable-rag/--disable-rag   Enable RAG (default: enabled)
  -t, --tool TEXT              Tools to enable (can be repeated)
  --temperature FLOAT          Model temperature
  --max-tokens INTEGER         Max tokens
```

**Examples:**
```bash
# Basic model
./lcp models create --name my-gpt4 --base-model gpt-4

# Model with tools and RAG
./lcp models create --name smart-assistant \
  --base-model gpt-4 \
  --tool calculator \
  --tool weather \
  --temperature 0.7

# Model without RAG
./lcp models create --name simple-chat --base-model gpt-3.5-turbo --disable-rag
```

### Update Model

```bash
./lcp models update <model-identifier> [OPTIONS]

Options:
  -n, --name TEXT                    New model name
  -v, --version TEXT                 New version
  --enable-rag/--disable-rag         Enable/disable RAG
  -t, --tool TEXT                    Tools to enable (replaces existing)
  --enabled/--disabled               Enable/disable model
```

**Examples:**
```bash
# Update model name and add tools
./lcp models update default-model --name enhanced-model --tool calculator --tool weather

# Disable a model
./lcp models update my-model --disabled
```

### Delete Model

```bash
./lcp models delete <model-identifier> [OPTIONS]

Options:
  -y, --yes    Skip confirmation
```

**Example:**
```bash
./lcp models delete old-model --yes
```

### Activate/Deactivate Models

```bash
# Activate for client use
./lcp models activate <model-identifier>

# Deactivate
./lcp models deactivate <model-identifier>
```

### Sync Models with Config

```bash
./lcp models sync [OPTIONS]

Options:
  -c, --config-file TEXT    Path to config file (default: config.yaml)
  -d, --dry-run             Show what would be done without making changes
  -x, --delete-missing      Delete models not in config
```

**Examples:**
```bash
# Dry run to see changes
./lcp models sync --dry-run

# Sync and delete models not in config
./lcp models sync --delete-missing

# Use custom config file
./lcp models sync --config-file my-config.yaml
```

## Tool Management

### List Tools

```bash
./lcp tools list [OPTIONS]

Options:
  --json, -j        Output as JSON
  -d, --detailed    Show detailed info
```

**Examples:**
```bash
./lcp tools list
./lcp tools list --detailed
```

### Get Tool Details

```bash
./lcp tools get <tool-id>
```

### Create Custom Tool

```bash
./lcp tools create [OPTIONS]

Options:
  -n, --name TEXT           Tool name (required)
  -d, --description TEXT    Tool description (required)
  -c, --category TEXT       Tool category
  -f, --code-file PATH      Python file with function code
```

**Examples:**
```bash
# Create tool from file
./lcp tools create --name my-calculator --description "Basic calculator" --code-file calculator.py

# Create tool with category
./lcp tools create --name web-scraper --description "Web scraping tool" --category "web" --code-file scraper.py
```

### Delete Tool

```bash
./lcp tools delete <tool-id> [OPTIONS]

Options:
  -y, --yes    Skip confirmation
```

## Knowledge Base Management

### List Knowledge Bases

```bash
./lcp kb list [OPTIONS]

Options:
  --json, -j    Output as JSON
```

### Get Knowledge Base Details

```bash
./lcp kb get <kb-id>
```

### Create Knowledge Base

```bash
./lcp kb create [OPTIONS]

Options:
  -n, --name TEXT           Knowledge base name (required)
  -d, --description TEXT    Description
  -c, --collection TEXT     Qdrant collection name (auto-generated if not provided)
```

**Example:**
```bash
./lcp kb create --name company-docs --description "Company documentation"
```

### Delete Knowledge Base

```bash
./lcp kb delete <kb-id> [OPTIONS]

Options:
  -y, --yes    Skip confirmation
```

### Import Documents

```bash
./lcp kb import <files>... [OPTIONS]

Options:
  -k, --kb-id TEXT    Target knowledge base ID
  -s, --source TEXT   Source name for the documents
```

**Examples:**
```bash
# Import single file
./lcp kb import document.pdf

# Import multiple files
./lcp kb import doc1.txt doc2.md doc3.pdf

# Import to specific knowledge base
./lcp kb import *.txt --kb-id company-docs --source "Q4 Reports"
```

### Search Knowledge Base

```bash
./lcp kb search <query> [OPTIONS]

Options:
  -k, --kb-id TEXT    Knowledge base ID to search
  -n, --top-k INT     Number of results (default: 3)
  -j, --json          Output as JSON
```

**Examples:**
```bash
./lcp kb search "machine learning algorithms"
./lcp kb search "company policies" --kb-id hr-docs --top-k 5
```

### Clear Knowledge Base

```bash
./lcp kb clear [OPTIONS]

Options:
  -k, --kb-id TEXT    Knowledge base ID to clear
  -y, --yes           Skip confirmation
```

### Sync Folder with Knowledge Base

```bash
./lcp kb sync <folder> [OPTIONS]

Options:
  -k, --kb-id TEXT          Target knowledge base ID
  -c, --clear               Clear knowledge base before syncing
  -e, --extensions TEXT     File extensions (default: txt,md,pdf)
  -r, --recursive           Sync recursively
```

**Examples:**
```bash
# Sync current directory
./lcp kb sync .

# Sync with specific extensions
./lcp kb sync docs --extensions txt,md,pdf,docx

# Sync recursively and clear first
./lcp kb sync docs --recursive --clear
```

### Get Knowledge Base Statistics

```bash
./lcp kb stats [OPTIONS]

Options:
  -k, --kb-id TEXT    Specific knowledge base ID
```

### List Documents

```bash
./lcp kb documents [OPTIONS]

Options:
  -k, --kb-id TEXT    Knowledge base ID
  -n, --limit INT     Maximum number of documents (default: 20)
  -o, --offset INT    Offset for pagination
  -j, --json          Output as JSON
```

## Chat Commands

### Send Chat Message

```bash
./lcp chat send <message> [OPTIONS]

Options:
  -m, --model TEXT    Model to use (default: gpt-oss:20b-cloud)
  -s, --system TEXT   System message
  -k, --kb-id TEXT    Knowledge base ID for RAG context
  --stream            Stream the response
```

**Examples:**
```bash
# Simple message
./lcp chat send "Hello, how are you?"

# With specific model and system message
./lcp chat send "Explain quantum physics" --model gpt-4 --system "You are a physics professor"

# With knowledge base context
./lcp chat send "What are our company policies?" --kb-id company-docs

# Streaming response
./lcp chat send "Tell me a long story" --stream
```

### Interactive Chat

```bash
./lcp chat interactive [OPTIONS]

Options:
  -m, --model TEXT    Model to use (default: gpt-oss:20b-cloud)
  -s, --system TEXT   System message
  -k, --kb-id TEXT    Knowledge base ID for RAG context
```

**Example:**
```bash
./lcp chat interactive --model gpt-4 --system "You are a helpful assistant"
```

## Version Management

### List Model Versions

```bash
./lcp versions list <model-id> [OPTIONS]

Options:
  -j, --json    Output as JSON
```

### Create Version

```bash
./lcp versions create <model-id> [OPTIONS]

Options:
  -v, --version TEXT                 New version number (required)
  -d, --description TEXT             Version description
  --enable-rag/--disable-rag         Enable/disable RAG
  -t, --tool TEXT                    Tools to enable
```

**Example:**
```bash
./lcp versions create my-model --version 2.0.0 --description "Added new features" --tool advanced-calculator
```

### Activate/Deactivate Version

```bash
# Activate version
./lcp versions activate <model-id> <version>

# Deactivate version
./lcp versions deactivate <model-id> <version>
```

## Chat Logs & Debugging

### List Chat Logs

```bash
./lcp logs list [OPTIONS]

Options:
  -m, --model TEXT          Filter by model name
  -s, --status TEXT         Filter by status (success, error, pending)
  -l, --limit INT           Number of logs to show (default: 20)
  -o, --offset INT          Offset for pagination
  -j, --json                Output as JSON
```

**Examples:**
```bash
./lcp logs list
./lcp logs list --model gpt-4 --status error --limit 50
```

### Show Log Details

```bash
./lcp logs show <log-id> [OPTIONS]

Options:
  -j, --json    Output as JSON
```

**Example:**
```bash
./lcp logs show abc123-def456
```

### Chat Log Statistics

```bash
./lcp logs stats [OPTIONS]

Options:
  -j, --json    Output as JSON
```

### Delete Chat Log

```bash
./lcp logs delete <log-id> [OPTIONS]

Options:
  -y, --yes    Skip confirmation
```

### Clear Chat Logs

```bash
./lcp logs clear [OPTIONS]

Options:
  -d, --before-days INT    Only delete logs older than this many days
  -y, --yes                Skip confirmation
```

**Examples:**
```bash
# Clear all logs
./lcp logs clear --yes

# Clear logs older than 30 days
./lcp logs clear --before-days 30 --yes
```

## Testing

### Run Tests

```bash
# Run RAG tests
./lcp test rag

# Run tool tests
./lcp test tools

# Run all tests
./lcp test all
```

## Configuration

### Show CLI Configuration

```bash
./lcp config
```