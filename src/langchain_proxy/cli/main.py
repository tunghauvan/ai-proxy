#!/usr/bin/env python3
"""CLI tool for managing the LangChain Proxy Server"""
import os
import sys
import json
import subprocess
from typing import Optional, List
from pathlib import Path

import click
import requests
from dotenv import load_dotenv
import yaml

# Load environment variables
load_dotenv()

# Default configuration
DEFAULT_BASE_URL = os.getenv("LANGCHAIN_PROXY_URL", "http://localhost:8000")
DEFAULT_MODEL = os.getenv("OLLAMA_API_MODEL", "gpt-oss:20b-cloud")


class Config:
    """CLI Configuration"""
    def __init__(self):
        self.base_url = DEFAULT_BASE_URL
        self.verbose = False


pass_config = click.make_pass_decorator(Config, ensure=True)


def print_json(data, indent=2):
    """Pretty print JSON data"""
    click.echo(json.dumps(data, indent=indent, default=str))


def print_table(headers: List[str], rows: List[List[str]], max_width: int = 50):
    """Print a simple table"""
    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            cell_str = str(cell) if cell is not None else ""
            if len(cell_str) > max_width:
                cell_str = cell_str[:max_width-3] + "..."
            widths[i] = max(widths[i], len(cell_str))
    
    # Print header
    header_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    click.echo(header_line)
    click.echo("-" * len(header_line))
    
    # Print rows
    for row in rows:
        row_cells = []
        for i, cell in enumerate(row):
            cell_str = str(cell) if cell is not None else ""
            if len(cell_str) > max_width:
                cell_str = cell_str[:max_width-3] + "..."
            row_cells.append(cell_str.ljust(widths[i]))
        click.echo(" | ".join(row_cells))


def api_request(method: str, endpoint: str, base_url: str, **kwargs):
    """Make an API request and handle errors"""
    url = f"{base_url}{endpoint}"
    try:
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        if response.status_code == 204:
            return None
        return response.json()
    except requests.exceptions.ConnectionError:
        click.echo(f"Error: Cannot connect to {base_url}", err=True)
        click.echo("Make sure the server is running.", err=True)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        try:
            error_detail = e.response.json().get("detail", str(e))
        except:
            error_detail = str(e)
        click.echo(f"Error: {error_detail}", err=True)
        sys.exit(1)


def api_request_optional(method: str, endpoint: str, base_url: str, **kwargs):
    """Make an API request that doesn't exit on 404 errors"""
    url = f"{base_url}{endpoint}"
    try:
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        if response.status_code == 204:
            return None
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None  # Return None for 404s instead of exiting
        try:
            error_detail = e.response.json().get("detail", str(e))
        except:
            error_detail = str(e)
        click.echo(f"Error: {error_detail}", err=True)
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        click.echo(f"Error: Cannot connect to {base_url}", err=True)
        click.echo("Make sure the server is running.", err=True)
        sys.exit(1)


# ==================== MAIN CLI GROUP ====================

@click.group()
@click.option("--url", "-u", default=DEFAULT_BASE_URL, help="Server base URL")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@pass_config
def cli(config, url, verbose):
    """LangChain Proxy CLI - Manage models, tools, knowledge bases, and more."""
    config.base_url = url
    config.verbose = verbose


# ==================== MODEL COMMANDS ====================

@cli.group()
def models():
    """Model management commands"""
    pass

@cli.group()
def models():
    """Model management commands"""
    pass


@models.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@pass_config
def models_list(config, output_json):
    """List all custom models"""
    data = api_request("GET", "/v1/admin/models", config.base_url)
    
    if output_json:
        print_json(data)
    else:
        if not data:
            click.echo("No models found.")
            return
        
        headers = ["ID", "Name", "Version", "Enabled", "Active", "RAG", "Tools"]
        rows = []
        for m in data:
            rag_enabled = m.get("rag_settings", {}).get("enabled", False)
            tools = ", ".join(m.get("tool_names", [])[:3])
            if len(m.get("tool_names", [])) > 3:
                tools += "..."
            # Only truncate very long IDs
            model_id = m["id"]
            if len(model_id) > 20:
                model_id = model_id[:17] + "..."
            rows.append([
                model_id,
                m["name"],
                m["version"],
                "✓" if m["enabled"] else "✗",
                "✓" if m["active"] else "✗",
                "✓" if rag_enabled else "✗",
                tools or "-"
            ])
        print_table(headers, rows)


@models.command("get")
@click.argument("model_identifier")
@pass_config
def models_get(config, model_identifier):
    """Get details of a specific model (by ID or name)"""
    # Resolve identifier to ID
    model_id = resolve_model_identifier(config, model_identifier)
    if not model_id:
        return
    
    data = api_request("GET", f"/v1/admin/models/{model_id}", config.base_url)
    print_json(data)


@models.command("create")
@click.option("--name", "-n", required=True, help="Model name")
@click.option("--version", "-v", default="1.0.0", help="Model version")
@click.option("--base-model", "-b", help="Base LLM model to use")
@click.option("--enable-rag/--disable-rag", default=True, help="Enable RAG")
@click.option("--tool", "-t", multiple=True, help="Tools to enable (can be repeated)")
@click.option("--temperature", type=float, help="Model temperature")
@click.option("--max-tokens", type=int, help="Max tokens")
@pass_config
def models_create(config, name, version, base_model, enable_rag, tool, temperature, max_tokens):
    """Create a new custom model"""
    payload = {
        "name": name,
        "version": version,
        "enabled": True,
        "rag_settings": {"enabled": enable_rag},
        "tool_names": list(tool) if tool else [],
    }
    
    if base_model:
        payload["base_model"] = base_model
    
    model_params = {}
    if temperature is not None:
        model_params["temperature"] = temperature
    if max_tokens is not None:
        model_params["max_tokens"] = max_tokens
    if model_params:
        payload["model_params"] = model_params
    
    data = api_request("POST", "/v1/admin/models", config.base_url, json=payload)
    click.echo(f"✅ Model '{name}' created successfully!")
    if config.verbose:
        print_json(data)


@models.command("update")
@click.argument("model_identifier")
@click.option("--name", "-n", help="New model name")
@click.option("--version", "-v", help="New version")
@click.option("--enable-rag/--disable-rag", default=None, help="Enable/disable RAG")
@click.option("--tool", "-t", multiple=True, help="Tools to enable (replaces existing)")
@click.option("--enabled/--disabled", default=None, help="Enable/disable model")
@pass_config
def models_update(config, model_identifier, name, version, enable_rag, tool, enabled):
    """Update an existing model (by ID or name)"""
    # Resolve identifier to ID
    model_id = resolve_model_identifier(config, model_identifier)
    if not model_id:
        return
    
    payload = {}
    
    if name:
        payload["name"] = name
    if version:
        payload["version"] = version
    if enabled is not None:
        payload["enabled"] = enabled
    if enable_rag is not None:
        payload["rag_settings"] = {"enabled": enable_rag}
    if tool:
        payload["tool_names"] = list(tool)
    
    if not payload:
        click.echo("No updates specified.")
        return
    
    data = api_request("PUT", f"/v1/admin/models/{model_id}", config.base_url, json=payload)
    click.echo(f"✅ Model updated successfully!")
    if config.verbose:
        print_json(data)


@models.command("delete")
@click.argument("model_identifier")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@pass_config
def models_delete(config, model_identifier, yes):
    """Delete a model (by ID or name)"""
    # Resolve identifier to ID
    model_id = resolve_model_identifier(config, model_identifier)
    if not model_id:
        return
    
    if not yes:
        click.confirm(f"Are you sure you want to delete model '{model_identifier}'?", abort=True)
    
    api_request("DELETE", f"/v1/admin/models/{model_id}", config.base_url)
    click.echo(f"✅ Model '{model_identifier}' deleted successfully!")


@models.command("activate")
@click.argument("model_identifier")
@pass_config
def models_activate(config, model_identifier):
    """Activate a model for client use (by ID or name)"""
    # Resolve identifier to ID
    model_id = resolve_model_identifier(config, model_identifier)
    if not model_id:
        return
    
    data = api_request("POST", f"/v1/admin/models/{model_id}/activate", config.base_url)
    click.echo(f"✅ Model '{model_identifier}' activated!")


@models.command("deactivate")
@click.argument("model_identifier")
@pass_config
def models_deactivate(config, model_identifier):
    """Deactivate a model (by ID or name)"""
    # Resolve identifier to ID
    model_id = resolve_model_identifier(config, model_identifier)
    if not model_id:
        return
    
    data = api_request("POST", f"/v1/admin/models/{model_id}/deactivate", config.base_url)
    click.echo(f"✅ Model '{model_identifier}' deactivated!")


@models.command("sync")
@click.option("--config-file", "-c", default="config.yaml", help="Path to config file")
@click.option("--dry-run", "-d", is_flag=True, help="Show what would be done without making changes")
@click.option("--delete-missing", "-x", is_flag=True, help="Delete models not in config")
@pass_config
def models_sync(config, config_file, dry_run, delete_missing):
    """Sync models with configuration file"""
    config_path = Path(config_file)
    if not config_path.exists():
        click.echo(f"Error: Config file '{config_file}' not found.")
        sys.exit(1)
    
    try:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
    except Exception as e:
        click.echo(f"Error reading config file: {e}")
        sys.exit(1)
    
    if "models" not in config_data:
        click.echo("Error: No 'models' section found in config file.")
        sys.exit(1)
    
    config_models = config_data["models"]
    if not isinstance(config_models, list):
        click.echo("Error: 'models' section should be a list.")
        sys.exit(1)
    
    # Get existing models
    try:
        existing_models = api_request("GET", "/v1/admin/models", config.base_url)
    except:
        existing_models = []
    
    # Create lookup by name
    existing_by_name = {m["name"]: m for m in existing_models}
    
    created = 0
    updated = 0
    deleted = 0
    
    # Process config models
    for model_config in config_models:
        name = model_config.get("name")
        if not name:
            click.echo(f"Warning: Skipping model without name: {model_config}")
            continue
        
        if name in existing_by_name:
            # Update existing model
            model_id = existing_by_name[name]["id"]
            payload = {}
            
            # Check what needs updating
            existing = existing_by_name[name]
            
            if model_config.get("version") != existing.get("version"):
                payload["version"] = model_config.get("version", "1.0.0")
            
            if model_config.get("enabled", True) != existing.get("enabled"):
                payload["enabled"] = model_config.get("enabled", True)
            
            config_rag = model_config.get("rag_settings", {})
            existing_rag = existing.get("rag_settings", {})
            if config_rag.get("enabled", False) != existing_rag.get("enabled", False):
                payload["rag_settings"] = {"enabled": config_rag.get("enabled", False)}
            
            config_tools = model_config.get("tool_names", [])
            existing_tools = existing.get("tool_names", [])
            if set(config_tools) != set(existing_tools):
                payload["tool_names"] = config_tools
            
            if model_config.get("base_model") != existing.get("base_model"):
                payload["base_model"] = model_config.get("base_model")
            
            if model_config.get("model_params") != existing.get("model_params"):
                payload["model_params"] = model_config.get("model_params", {})
            
            if payload:
                if dry_run:
                    click.echo(f"Would update model '{name}': {payload}")
                else:
                    try:
                        api_request("PUT", f"/v1/admin/models/{model_id}", config.base_url, json=payload)
                        click.echo(f"✅ Updated model '{name}'")
                        updated += 1
                    except Exception as e:
                        click.echo(f"Error updating model '{name}': {e}")
            else:
                if dry_run:
                    click.echo(f"Model '{name}' is already up to date")
        else:
            # Create new model
            payload = {
                "name": name,
                "version": model_config.get("version", "1.0.0"),
                "enabled": model_config.get("enabled", True),
                "rag_settings": model_config.get("rag_settings", {"enabled": False}),
                "tool_names": model_config.get("tool_names", []),
            }
            
            if model_config.get("base_model"):
                payload["base_model"] = model_config["base_model"]
            
            if model_config.get("model_params"):
                payload["model_params"] = model_config["model_params"]
            
            if dry_run:
                click.echo(f"Would create model '{name}': {payload}")
            else:
                try:
                    api_request("POST", "/v1/admin/models", config.base_url, json=payload)
                    click.echo(f"✅ Created model '{name}'")
                    created += 1
                except Exception as e:
                    click.echo(f"Error creating model '{name}': {e}")
    
    # Handle deletion of models not in config
    if delete_missing:
        config_names = {m.get("name") for m in config_models if m.get("name")}
        for existing in existing_models:
            if existing["name"] not in config_names:
                if dry_run:
                    click.echo(f"Would delete model '{existing['name']}'")
                else:
                    try:
                        api_request("DELETE", f"/v1/admin/models/{existing['id']}", config.base_url)
                        click.echo(f"✅ Deleted model '{existing['name']}'")
                        deleted += 1
                    except Exception as e:
                        click.echo(f"Error deleting model '{existing['name']}': {e}")
    
    if dry_run:
        click.echo(f"\nDry run complete. Would create: {created}, update: {updated}, delete: {deleted}")
    else:
        click.echo(f"\n✅ Sync complete. Created: {created}, Updated: {updated}, Deleted: {deleted}")


def resolve_model_identifier(config, identifier):
    """Resolve a model identifier (name or ID) to an ID"""
    # First try to get by ID
    data = api_request_optional("GET", f"/v1/admin/models/{identifier}", config.base_url)
    if data is not None:
        return identifier  # It was an ID
    
    # Try to find by name
    models = api_request_optional("GET", "/v1/admin/models", config.base_url)
    if models is not None:
        for model in models:
            if model["name"] == identifier:
                return model["id"]
    
    click.echo(f"Model '{identifier}' not found (tried both ID and name).")
    return None


# ==================== TOOL COMMANDS ====================

@cli.group()
def tools():
    """Tool management commands"""
    pass


@tools.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed info")
@pass_config
def tools_list(config, output_json, detailed):
    """List available tools"""
    if detailed:
        data = api_request("GET", "/v1/admin/tools/detailed", config.base_url)
    else:
        data = api_request("GET", "/v1/admin/tools/detailed", config.base_url)
    
    if output_json:
        if not detailed:
            # For JSON output in simple mode, just return the tool names
            tool_names = [t["name"] for t in data]
            print_json(tool_names)
        else:
            print_json(data)
    else:
        if detailed:
            headers = ["ID", "Name", "Category", "Enabled", "Builtin", "Description"]
            rows = []
            for t in data:
                # Only truncate very long IDs
                tool_id = t["id"]
                if len(tool_id) > 20:
                    tool_id = tool_id[:17] + "..."
                rows.append([
                    tool_id,
                    t["name"],
                    t.get("category") or "-",
                    "✓" if t["enabled"] else "✗",
                    "✓" if t.get("is_builtin") else "✗",
                    (t.get("description") or "-")[:40]
                ])
            print_table(headers, rows)
        else:
            # Simple mode: show table with Name, Enabled, Builtin, Description
            if not data:
                click.echo("No tools found.")
                return
            
            headers = ["Name", "Enabled", "Builtin", "Description"]
            rows = []
            for t in data:
                rows.append([
                    t["name"],
                    "✓" if t["enabled"] else "✗",
                    "✓" if t.get("is_builtin") else "✗",
                    (t.get("description") or "-")[:50]
                ])
            print_table(headers, rows)


@tools.command("get")
@click.argument("tool_id")
@pass_config
def tools_get(config, tool_id):
    """Get details of a specific tool"""
    data = api_request("GET", f"/v1/admin/tools/{tool_id}", config.base_url)
    print_json(data)


@tools.command("create")
@click.option("--name", "-n", required=True, help="Tool name")
@click.option("--description", "-d", required=True, help="Tool description")
@click.option("--category", "-c", help="Tool category")
@click.option("--code-file", "-f", type=click.Path(exists=True), help="Python file with function code")
@pass_config
def tools_create(config, name, description, category, code_file):
    """Create a new custom tool"""
    payload = {
        "name": name,
        "description": description,
        "enabled": True,
    }
    
    if category:
        payload["category"] = category
    
    if code_file:
        with open(code_file, "r") as f:
            payload["function_code"] = f.read()
    
    data = api_request("POST", "/v1/admin/tools", config.base_url, json=payload)
    click.echo(f"✅ Tool '{name}' created successfully!")
    if config.verbose:
        print_json(data)


@tools.command("delete")
@click.argument("tool_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@pass_config
def tools_delete(config, tool_id, yes):
    """Delete a custom tool"""
    if not yes:
        click.confirm(f"Are you sure you want to delete tool '{tool_id}'?", abort=True)
    
    api_request("DELETE", f"/v1/admin/tools/{tool_id}", config.base_url)
    click.echo(f"✅ Tool '{tool_id}' deleted successfully!")


# ==================== KNOWLEDGE BASE COMMANDS ====================

@cli.group()
def kb():
    """Knowledge base management commands"""
    pass


@kb.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@pass_config
def kb_list(config, output_json):
    """List all knowledge bases"""
    data = api_request("GET", "/v1/admin/knowledge-bases", config.base_url)
    
    if output_json:
        print_json(data)
    else:
        if not data:
            click.echo("No knowledge bases found.")
            return
        
        headers = ["ID", "Name", "Collection", "Description"]
        rows = []
        for kb in data:
            # Only truncate very long IDs
            kb_id = kb["id"]
            if len(kb_id) > 20:
                kb_id = kb_id[:17] + "..."
            rows.append([
                kb_id,
                kb["name"],
                kb["collection"],
                (kb.get("description") or "-")[:30]
            ])
        print_table(headers, rows)


@kb.command("get")
@click.argument("kb_id")
@pass_config
def kb_get(config, kb_id):
    """Get details of a specific knowledge base"""
    data = api_request("GET", f"/v1/admin/knowledge-bases/{kb_id}", config.base_url)
    print_json(data)


@kb.command("create")
@click.option("--name", "-n", required=True, help="Knowledge base name")
@click.option("--description", "-d", help="Description")
@click.option("--collection", "-c", help="Qdrant collection name (auto-generated if not provided)")
@pass_config
def kb_create(config, name, description, collection):
    """Create a new knowledge base"""
    payload = {"name": name}
    
    if description:
        payload["description"] = description
    if collection:
        payload["collection"] = collection
    
    data = api_request("POST", "/v1/admin/knowledge-bases", config.base_url, json=payload)
    click.echo(f"✅ Knowledge base '{name}' created!")
    click.echo(f"   ID: {data['id']}")
    click.echo(f"   Collection: {data['collection']}")


@kb.command("delete")
@click.argument("kb_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@pass_config
def kb_delete(config, kb_id, yes):
    """Delete a knowledge base"""
    if not yes:
        click.confirm(f"Are you sure you want to delete knowledge base '{kb_id}'?", abort=True)
    
    api_request("DELETE", f"/v1/admin/knowledge-bases/{kb_id}", config.base_url)
    click.echo(f"✅ Knowledge base '{kb_id}' deleted!")


@kb.command("stats")
@click.option("--kb-id", "-k", help="Specific knowledge base ID")
@pass_config
def kb_stats(config, kb_id):
    """Get knowledge base statistics"""
    endpoint = "/v1/rag/stats"
    if kb_id:
        endpoint += f"?kb_id={kb_id}"
    
    data = api_request("GET", endpoint, config.base_url)
    print_json(data)


@kb.command("import")
@click.argument("files", nargs=-1, type=click.Path(exists=True))
@click.option("--kb-id", "-k", help="Target knowledge base ID")
@click.option("--source", "-s", help="Source name for the documents")
@pass_config
def kb_import(config, files, kb_id, source):
    """Import documents into the knowledge base"""
    if not files:
        click.echo("No files specified.")
        return
    
    documents = []
    for file_path in files:
        with open(file_path, "r") as f:
            content = f.read()
        
        doc_source = source or Path(file_path).name
        documents.append({
            "content": content,
            "source": doc_source
        })
    
    endpoint = "/v1/rag/import/documents"
    if kb_id:
        endpoint += f"?kb_id={kb_id}"
    
    data = api_request("POST", endpoint, config.base_url, json={"documents": documents})
    click.echo(f"✅ Imported {data['original_count']} documents -> {data['chunks_created']} chunks")


@kb.command("search")
@click.argument("query")
@click.option("--kb-id", "-k", help="Knowledge base ID to search")
@click.option("--top-k", "-n", default=3, help="Number of results")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@pass_config
def kb_search(config, query, kb_id, top_k, output_json):
    """Search the knowledge base"""
    endpoint = "/v1/rag/search"
    if kb_id:
        endpoint += f"?kb_id={kb_id}"
    
    data = api_request("POST", endpoint, config.base_url, json={"query": query, "top_k": top_k})
    
    if output_json:
        print_json(data)
    else:
        click.echo(f"Query: {data['query']}")
        click.echo(f"Results: {len(data['results'])}")
        click.echo("-" * 50)
        
        for i, result in enumerate(data["results"], 1):
            click.echo(f"\n[{i}] Source: {result['source']}")
            content = result["content"]
            if len(content) > 200:
                content = content[:200] + "..."
            click.echo(f"    {content}")


@kb.command("clear")
@click.option("--kb-id", "-k", help="Knowledge base ID to clear")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@pass_config
def kb_clear(config, kb_id, yes):
    """Clear all documents from a knowledge base"""
    if not yes:
        target = f"knowledge base '{kb_id}'" if kb_id else "the default knowledge base"
        click.confirm(f"Are you sure you want to clear all documents from {target}?", abort=True)
    
    endpoint = "/v1/rag/clear"
    if kb_id:
        endpoint += f"?kb_id={kb_id}"
    
    data = api_request("DELETE", endpoint, config.base_url)
    click.echo(f"✅ {data.get('message', 'Knowledge base cleared')}")


@kb.command("reload")
@click.option("--kb-id", "-k", help="Knowledge base ID to reload")
@pass_config
def kb_reload(config, kb_id):
    """Reload the knowledge base"""
    endpoint = "/v1/rag/reload"
    if kb_id:
        endpoint += f"?kb_id={kb_id}"
    
    data = api_request("POST", endpoint, config.base_url)
    click.echo(f"✅ {data.get('message', 'Knowledge base reloaded')}")
    if config.verbose:
        print_json(data.get("stats", {}))


@kb.command("sync")
@click.argument("folder", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--kb-id", "-k", help="Target knowledge base ID")
@click.option("--clear", "-c", is_flag=True, help="Clear knowledge base before syncing")
@click.option("--extensions", "-e", default="txt,md,pdf", help="File extensions to sync (comma-separated)")
@click.option("--recursive", "-r", is_flag=True, help="Sync recursively")
@pass_config
def kb_sync(config, folder, kb_id, clear, extensions, recursive):
    """Sync a folder with the knowledge base"""
    import os
    from pathlib import Path
    
    folder_path = Path(folder)
    ext_list = [ext.strip().lstrip('.') for ext in extensions.split(',')]
    
    # Find all files with specified extensions
    pattern = "**/*" if recursive else "*"
    files = []
    for ext in ext_list:
        files.extend(folder_path.glob(f"{pattern}.{ext}"))
    
    if not files:
        click.echo(f"No files found with extensions: {', '.join(ext_list)}")
        return
    
    click.echo(f"Found {len(files)} files to sync:")
    for f in files:
        click.echo(f"  {f.relative_to(folder_path)}")
    
    # Clear if requested
    if clear:
        click.echo("Clearing knowledge base...")
        endpoint = "/v1/rag/clear"
        if kb_id:
            endpoint += f"?kb_id={kb_id}"
        api_request("DELETE", endpoint, config.base_url)
        click.echo("✅ Knowledge base cleared")
    
    # Import all files
    documents = []
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Use relative path as source
            source = str(file_path.relative_to(folder_path))
            documents.append({
                "content": content,
                "source": source
            })
        except Exception as e:
            click.echo(f"⚠️  Error reading {file_path}: {e}", err=True)
            continue
    
    if not documents:
        click.echo("No documents to import.")
        return
    
    # Import documents
    endpoint = "/v1/rag/import/documents"
    if kb_id:
        endpoint += f"?kb_id={kb_id}"
    
    data = api_request("POST", endpoint, config.base_url, json={"documents": documents})
    click.echo(f"✅ Synced {data['original_count']} documents -> {data['chunks_created']} chunks")


@kb.command("documents")
@click.option("--kb-id", "-k", help="Knowledge base ID")
@click.option("--limit", "-n", default=20, help="Maximum number of documents to list")
@click.option("--offset", "-o", default=0, help="Offset for pagination")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@pass_config
def kb_documents(config, kb_id, limit, offset, output_json):
    """List documents in a knowledge base"""
    endpoint = "/v1/rag/documents"
    params = []
    if kb_id:
        params.append(f"kb_id={kb_id}")
    if limit != 20:
        params.append(f"limit={limit}")
    if offset != 0:
        params.append(f"offset={offset}")
    
    if params:
        endpoint += "?" + "&".join(params)
    
    data = api_request("GET", endpoint, config.base_url)
    
    if output_json:
        print_json(data)
    else:
        if "error" in data:
            click.echo(f"Error: {data['error']}")
            return
        
        click.echo(f"Knowledge Base: {data.get('collection', 'default')}")
        click.echo(f"Total Documents: {data.get('total_count', 0)}")
        click.echo(f"Showing: {data.get('returned_count', 0)} (offset: {offset}, limit: {limit})")
        click.echo("-" * 80)
        
        if not data.get("documents"):
            click.echo("No documents found.")
            return
        
        for i, doc in enumerate(data["documents"], 1):
            click.echo(f"[{i}] ID: {doc['id']}")
            click.echo(f"    Source: {doc['source']}")
            content = doc["content"]
            if len(content) > 100:
                content = content[:100] + "..."
            click.echo(f"    Content: {content}")
            click.echo()


# ==================== CHAT COMMANDS ====================

@cli.group()
def chat():
    """Chat interaction commands"""
    pass


@chat.command("send")
@click.argument("message")
@click.option("--model", "-m", default=DEFAULT_MODEL, help="Model to use")
@click.option("--system", "-s", help="System message")
@click.option("--kb-id", "-k", help="Knowledge base ID for RAG context")
@click.option("--stream", is_flag=True, help="Stream the response")
@pass_config
def chat_send(config, message, model, system, kb_id, stream):
    """Send a chat message"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": message})
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": stream
    }
    
    headers = {"Content-Type": "application/json"}
    if kb_id:
        headers["X-KB-ID"] = kb_id
    
    url = f"{config.base_url}/v1/chat/completions"
    
    if stream:
        # Handle streaming response
        try:
            response = requests.post(url, json=payload, headers=headers, stream=True)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            click.echo()
                            break
                        try:
                            chunk = json.loads(data)
                            content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                click.echo(content, nl=False)
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    else:
        # Handle non-streaming response
        data = api_request("POST", "/v1/chat/completions", config.base_url, json=payload, headers=headers)
        content = data["choices"][0]["message"]["content"]
        click.echo(content)


@chat.command("interactive")
@click.option("--model", "-m", default=DEFAULT_MODEL, help="Model to use")
@click.option("--system", "-s", help="System message")
@click.option("--kb-id", "-k", help="Knowledge base ID for RAG context")
@pass_config
def chat_interactive(config, model, system, kb_id):
    """Start an interactive chat session"""
    click.echo(f"Starting interactive chat with {model}")
    click.echo("Type 'exit' or 'quit' to end the session")
    click.echo("-" * 50)
    
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
        click.echo(f"System: {system}")
    
    headers = {"Content-Type": "application/json"}
    if kb_id:
        headers["X-KB-ID"] = kb_id
        click.echo(f"Using KB: {kb_id}")
    
    while True:
        try:
            user_input = click.prompt("\nYou", type=str)
            
            if user_input.lower() in ["exit", "quit"]:
                click.echo("Goodbye!")
                break
            
            messages.append({"role": "user", "content": user_input})
            
            payload = {
                "model": model,
                "messages": messages,
                "stream": True
            }
            
            url = f"{config.base_url}/v1/chat/completions"
            response = requests.post(url, json=payload, headers=headers, stream=True)
            response.raise_for_status()
            
            click.echo("\nAssistant: ", nl=False)
            assistant_response = ""
            
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                click.echo(content, nl=False)
                                assistant_response += content
                        except json.JSONDecodeError:
                            pass
            
            click.echo()  # New line after response
            messages.append({"role": "assistant", "content": assistant_response})
            
        except KeyboardInterrupt:
            click.echo("\nGoodbye!")
            break
        except Exception as e:
            click.echo(f"\nError: {e}", err=True)


# ==================== VERSION COMMANDS ====================

@cli.group()
def versions():
    """Model version management commands"""
    pass


@versions.command("list")
@click.argument("model_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@pass_config
def versions_list(config, model_id, output_json):
    """List all versions of a model"""
    data = api_request("GET", f"/v1/admin/models/{model_id}/versions", config.base_url)
    
    if output_json:
        print_json(data)
    else:
        if not data:
            click.echo("No versions found.")
            return
        
        headers = ["Version", "Enabled", "Active", "RAG", "Description"]
        rows = []
        for v in data:
            rag_enabled = v.get("rag_settings", {}).get("enabled", False)
            rows.append([
                v["version"],
                "✓" if v["enabled"] else "✗",
                "✓" if v["active"] else "✗",
                "✓" if rag_enabled else "✗",
                (v.get("description") or "-")[:30]
            ])
        print_table(headers, rows)


@versions.command("create")
@click.argument("model_id")
@click.option("--version", "-v", required=True, help="New version number")
@click.option("--description", "-d", help="Version description")
@click.option("--enable-rag/--disable-rag", default=None, help="Enable/disable RAG")
@click.option("--tool", "-t", multiple=True, help="Tools to enable")
@pass_config
def versions_create(config, model_id, version, description, enable_rag, tool):
    """Create a new version for a model"""
    payload = {"version": version}
    
    if description:
        payload["description"] = description
    if enable_rag is not None:
        payload["rag_settings"] = {"enabled": enable_rag}
    if tool:
        payload["tool_names"] = list(tool)
    
    data = api_request("POST", f"/v1/admin/models/{model_id}/versions", config.base_url, json=payload)
    click.echo(f"✅ Version '{version}' created successfully!")


@versions.command("activate")
@click.argument("model_id")
@click.argument("version")
@pass_config
def versions_activate(config, model_id, version):
    """Activate a specific version for client use"""
    data = api_request("POST", f"/v1/admin/models/{model_id}/versions/{version}/activate", config.base_url)
    click.echo(f"✅ Version '{version}' activated!")


@versions.command("deactivate")
@click.argument("model_id")
@click.argument("version")
@pass_config
def versions_deactivate(config, model_id, version):
    """Deactivate a specific version"""
    data = api_request("POST", f"/v1/admin/models/{model_id}/versions/{version}/deactivate", config.base_url)
    click.echo(f"✅ Version '{version}' deactivated!")


# ==================== TEST COMMANDS ====================

@cli.group()
def test():
    """Testing commands"""
    pass


@test.command("rag")
def test_rag():
    """Run RAG tests"""
    click.echo("Running RAG tests...")
    subprocess.run(["python3", "tests/rag.py"])


@test.command("tools")
def test_tools():
    """Run tool tests"""
    click.echo("Running tool tests...")
    subprocess.run(["python3", "tests/test_tools.py"])


@test.command("all")
def test_all():
    """Run all tests"""
    click.echo("Running all tests...")
    subprocess.run(["python3", "-m", "pytest", "tests/", "-v"])


# ==================== UTILITY COMMANDS ====================

# ==================== Chat Logs Commands ====================

@cli.group()
@pass_config
def logs(config):
    """Manage chat logs for debugging and analytics"""
    pass


@logs.command("list")
@click.option("--model", "-m", help="Filter by model name")
@click.option("--status", "-s", type=click.Choice(["success", "error", "pending"]), help="Filter by status")
@click.option("--limit", "-l", default=20, help="Number of logs to show")
@click.option("--offset", "-o", default=0, help="Offset for pagination")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@pass_config
def logs_list(config, model, status, limit, offset, as_json):
    """List recent chat logs"""
    params = {"limit": limit, "offset": offset}
    if model:
        params["model"] = model
    if status:
        params["status"] = status
    
    result = api_request("GET", "/v1/admin/logs", config.base_url, params=params)
    
    if as_json:
        print_json(result)
        return
    
    click.echo(f"Chat Logs ({result['total']} total, showing {len(result['logs'])})\n")
    
    if not result["logs"]:
        click.echo("No logs found.")
        return
    
    headers = ["ID", "Chat ID", "Model", "Status", "Latency", "Tools", "Created"]
    rows = []
    for log in result["logs"]:
        tools = ", ".join(log.get("tools_used", []) or []) if log.get("tools_used") else "-"
        latency = f"{log.get('latency_ms', '-')}ms" if log.get("latency_ms") else "-"
        created = log.get("created_at", "")[:19] if log.get("created_at") else "-"
        rows.append([
            log["id"][:8] + "...",
            log["chat_id"],
            log["model_name"][:20],
            log["status"],
            latency,
            tools[:30],
            created,
        ])
    
    print_table(headers, rows, max_width=35)


@logs.command("show")
@click.argument("log_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@pass_config
def logs_show(config, log_id, as_json):
    """Show details of a specific chat log"""
    result = api_request("GET", f"/v1/admin/logs/{log_id}", config.base_url)
    
    if as_json:
        print_json(result)
        return
    
    click.echo(f"Chat Log: {result['id']}\n")
    click.echo(f"  Chat ID: {result['chat_id']}")
    click.echo(f"  Model: {result['model_name']}")
    click.echo(f"  Status: {result['status']}")
    click.echo(f"  Stream: {result['is_stream']}")
    click.echo(f"  Latency: {result.get('latency_ms', '-')}ms")
    click.echo(f"  Created: {result['created_at']}")
    
    if result.get("model_config_id"):
        click.echo(f"  Config ID: {result['model_config_id']}")
    if result.get("kb_id"):
        click.echo(f"  KB ID: {result['kb_id']}")
    
    click.echo("\n--- Tokens ---")
    click.echo(f"  Prompt: {result.get('prompt_tokens', '-')}")
    click.echo(f"  Completion: {result.get('completion_tokens', '-')}")
    click.echo(f"  Total: {result.get('total_tokens', '-')}")
    
    click.echo("\n--- Request ---")
    if result.get("user_message"):
        click.echo(f"  User: {result['user_message'][:200]}...")
    
    click.echo("\n--- Response ---")
    if result.get("response_content"):
        content = result["response_content"]
        if len(content) > 500:
            click.echo(f"  {content[:500]}...")
        else:
            click.echo(f"  {content}")
    
    if result.get("tools_used"):
        click.echo("\n--- Tools Used ---")
        for tool in result["tools_used"]:
            click.echo(f"  - {tool}")
    
    if result.get("tool_calls"):
        click.echo("\n--- Tool Calls ---")
        for tc in result["tool_calls"]:
            click.echo(f"  {tc.get('name', 'unknown')}:")
            click.echo(f"    Input: {json.dumps(tc.get('input', {}))}")
            if tc.get("output"):
                output = tc["output"]
                if len(output) > 200:
                    output = output[:200] + "..."
                click.echo(f"    Output: {output}")
    
    if result.get("error_message"):
        click.echo("\n--- Error ---")
        click.echo(f"  Type: {result.get('error_type', 'Unknown')}")
        click.echo(f"  Message: {result['error_message']}")


@logs.command("stats")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@pass_config
def logs_stats(config, as_json):
    """Show chat log statistics"""
    result = api_request("GET", "/v1/admin/logs/stats", config.base_url)
    
    if as_json:
        print_json(result)
        return
    
    click.echo("Chat Log Statistics\n")
    click.echo(f"  Total Logs: {result['total_logs']}")
    click.echo(f"  Success: {result['success_count']}")
    click.echo(f"  Errors: {result['error_count']}")
    click.echo(f"  Pending: {result['pending_count']}")
    
    if result.get("avg_latency_ms"):
        click.echo(f"  Avg Latency: {result['avg_latency_ms']:.1f}ms")
    
    if result.get("models_used"):
        click.echo("\n  Models Used:")
        for model, count in result["models_used"].items():
            click.echo(f"    - {model}: {count} requests")
    
    if result.get("tools_used"):
        click.echo("\n  Tools Used:")
        for tool, count in result["tools_used"].items():
            click.echo(f"    - {tool}: {count} calls")


@logs.command("delete")
@click.argument("log_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@pass_config
def logs_delete(config, log_id, yes):
    """Delete a specific chat log"""
    if not yes:
        click.confirm(f"Delete chat log {log_id}?", abort=True)
    
    result = api_request("DELETE", f"/v1/admin/logs/{log_id}", config.base_url)
    click.echo(f"Deleted log: {result['id']}")


@logs.command("clear")
@click.option("--before-days", "-d", type=int, help="Only delete logs older than this many days")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@pass_config
def logs_clear(config, before_days, yes):
    """Clear chat logs"""
    if before_days:
        msg = f"Delete all chat logs older than {before_days} days?"
    else:
        msg = "Delete ALL chat logs?"
    
    if not yes:
        click.confirm(msg, abort=True)
    
    params = {}
    if before_days:
        params["before_days"] = before_days
    
    result = api_request("DELETE", "/v1/admin/logs", config.base_url, params=params)
    click.echo(f"Deleted {result['deleted_count']} logs")


@cli.command("server")
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, type=int, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.option("--workers", default=1, type=int, help="Number of workers")
@click.option("--init-db", is_flag=True, help="Initialize database on startup")
def server_command(host, port, reload, workers, init_db):
    """Start the LangChain Proxy server"""
    import uvicorn
    from langchain_proxy.server.main import app, lifespan
    from langchain_proxy.server.database import init_db_sync

    if init_db:
        click.echo("Initializing database...")
        try:
            init_db_sync()
            click.echo("✅ Database initialized successfully")
        except Exception as e:
            click.echo(f"❌ Database initialization failed: {e}")
            sys.exit(1)

    click.echo(f"Starting server on {host}:{port}")
    if reload:
        click.echo("Auto-reload enabled")

    uvicorn.run(
        "langchain_proxy.server.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level="info"
    )


@cli.command("config")
@pass_config
def show_config(config):
    """Show current CLI configuration"""
    click.echo("CLI Configuration:")
    click.echo(f"  Server URL: {config.base_url}")
    click.echo(f"  Default Model: {DEFAULT_MODEL}")
    click.echo(f"  Verbose: {config.verbose}")


@cli.command("shell")
@pass_config
def shell_command(config):
    """Open a Python shell with the project loaded"""
    try:
        import IPython
        from langchain_proxy.server.config import get_config_store, get_tool_store, get_kb_store
        from langchain_proxy.core.graph import graph, create_llm_for_model
        
        click.echo("Loading project modules...")
        user_ns = {
            "config_store": get_config_store(),
            "tool_store": get_tool_store(),
            "kb_store": get_kb_store(),
            "graph": graph,
            "create_llm": create_llm_for_model,
            "base_url": config.base_url,
        }
        
        IPython.start_ipython(argv=[], user_ns=user_ns)
    except ImportError:
        click.echo("IPython not installed. Install with: pip install ipython")
        sys.exit(1)


if __name__ == "__main__":
    cli()
