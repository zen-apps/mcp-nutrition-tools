# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a USDA Nutrition MCP (Model Context Protocol) Server that provides nutrition tools powered by the USDA FoodData Central database. It implements both MCP protocol for Claude Desktop integration and a FastAPI HTTP server for general consumption.

## Development Commands

**Start servers:**
- `python -m src.mcp_server` - Run MCP protocol server
- `python -m src.mcp_http_server` - Run HTTP API server
- `python test_quick.py` - Quick USDA API connectivity test

**Testing:**
- `python -m pytest tests/` - Run test suite
- `pytest tests/ -v` - Verbose test output

**Code quality:**
- `ruff check src/` - Lint code
- `ruff format src/` - Format code
- `mypy src/` - Type checking

**Docker development:**
- `make up` - Start development environment
- `make down` - Stop services
- `make logs` - View container logs

## Architecture

### Dual Server Design
- **MCP Server** (`src/mcp_server.py`) - FastMCP implementation for Claude Desktop
- **HTTP Server** (`src/mcp_http_server.py`) - FastAPI REST API for general use
- **USDA Client** (`src/usda_client.py`) - API client with retry logic and rate limiting

### Key Components
- **Models** (`src/models/`) - Pydantic request/response schemas
- **Examples** (`examples/`) - Live demos and AI agent integration patterns
- **Deployment** (`deployment/`) - Docker and Terraform infrastructure

### MCP Tools Available
1. `search_foods` - Search USDA database by text
2. `get_food_details` - Get detailed nutrition for specific food
3. `get_multiple_foods` - Batch lookup up to 20 foods
4. `analyze_nutrition` - Compare nutritional data

## Configuration

**Required Environment Variables:**
- `FDC_API_KEY` - USDA FoodData Central API key (required)
- `ENVIRONMENT` - Set to "development" or "production"
- `LOG_LEVEL` - Logging level (DEBUG, INFO, etc.)

**API Constraints:**
- USDA API: 1000 requests/hour per key
- Batch requests: max 20 foods per call
- Automatic retry with exponential backoff

## Key Files for Understanding

- `src/mcp_server.py:45-60` - MCP tool registration
- `src/usda_client.py:78-95` - Rate limiting and retry logic
- `src/models/requests.py` - Input validation schemas
- `examples/live_demo.py` - Usage patterns and examples

## Testing Strategy

The codebase uses pytest with async support. Tests should mock USDA API calls using httpx-mock. Use `test_quick.py` for basic connectivity validation before running full test suite.