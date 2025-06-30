# 🥗 USDA Nutrition MCP Server

> **Professional Model Context Protocol (MCP) server for USDA FoodData Central**  
> Transforms 600k+ foods into intelligent nutrition tools for Claude Desktop and other MCP clients

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io/)
[![Hosted Service](https://img.shields.io/badge/Hosted_Service-Live-green.svg)](https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app)

## 🌟 What This Demonstrates

This project showcases **professional MCP implementation skills**:

✅ **Dual Architecture** - Both MCP protocol server AND HTTP API  
✅ **Production Bridge** - Smart `mcp_bridge.py` with hosted/local/custom server support  
✅ **Three Deployment Options** - Hosted service, local development, custom server  
✅ **Type-Safe Models** - Pydantic schemas with proper validation  
✅ **Rate Limiting & Retries** - Production-ready USDA API client  
✅ **Docker + Cloud Run** - Complete deployment pipeline  
✅ **Comprehensive Testing** - pytest with async support and API mocking  

## 🚀 Quick Start for Claude Desktop

### Option 1: Minimal Installation (Recommended)
Download just the bridge file - no need to clone the entire repository:

```bash
# Download the bridge
wget https://raw.githubusercontent.com/zen-apps/mcp-nutrition-tools/main/src/mcp_bridge.py

# Install dependencies
pip install mcp httpx
```

Then add to your Claude Desktop config:
```json
{
  "mcpServers": {
    "usda-nutrition": {
      "command": "python3",
      "args": ["/path/to/downloaded/mcp_bridge.py"]
    }
  }
}
```

#### Mac Users with Virtual Environment
```bash
# Navigate to your project
cd /Users/yourusername/your-project-folder

# Create new venv in the project folder
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install mcp httpx

# Test it works
python src/mcp_bridge.py --server-url https://usda-nutrition-mcp-356272800218.us-central1.run.app
```

### Option 2: Full Repository (For Development)
```json
{
  "mcpServers": {
    "usda-nutrition": {
      "command": "python3",
      "args": ["/path/to/mcp-nutrition-tools/src/mcp_bridge.py"],
      "cwd": "/path/to/mcp-nutrition-tools"
    }
  }
}
```

### Option 2: Local Development
```json
{
  "mcpServers": {
    "usda-nutrition": {
      "command": "python3",
      "args": [
        "/path/to/mcp-nutrition-tools/src/mcp_bridge.py",
        "--server-url",
        "http://localhost:8080"
      ],
      "cwd": "/path/to/mcp-nutrition-tools"
    }
  }
}
```

### Option 3: Custom Server
```json
{
  "mcpServers": {
    "usda-nutrition": {
      "command": "python3", 
      "args": [
        "/path/to/mcp-nutrition-tools/src/mcp_bridge.py",
        "--server-url",
        "https://your-server.com"
      ],
      "cwd": "/path/to/mcp-nutrition-tools"
    }
  }
}
```

See [examples/configs/claude_desktop_config_examples.json](examples/configs/claude_desktop_config_examples.json) for detailed configuration examples.

## 🔧 For Non-Claude Desktop Users

### Direct HTTP API
**Live API**: https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app  
**Documentation**: https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app/docs

```bash
# Search foods
curl -X POST "https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app/tools/search_foods" \
  -H "Content-Type: application/json" \
  -d '{"query": "chicken breast", "page_size": 5}'

# Get nutrition details  
curl -X POST "https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app/tools/get_food_nutrition" \
  -H "Content-Type: application/json" \
  -d '{"fdc_id": 171688}'
```

See [API_USAGE.md](API_USAGE.md) for complete integration examples with Python, JavaScript, LangChain, and OpenAI.

## 🛠 MCP Tools Available

Once configured, Claude Desktop gets these nutrition tools:

- **`search_foods`** - Search USDA database by text
- **`get_food_nutrition`** - Get detailed nutrition for specific food  
- **`compare_foods`** - Compare nutrition between multiple foods

### Example Claude Interaction

**You:** *"Compare the protein content of chicken breast vs salmon"*

**Claude:** *Uses MCP tools automatically:*
1. `search_foods("chicken breast")` → Finds FDC ID 171077
2. `search_foods("salmon")` → Finds FDC ID 175167  
3. `compare_foods([171077, 175167])` → Gets comparison data
4. Provides detailed analysis with recommendations

## 🏗 Architecture Deep Dive

### Dual Server Design
```
Claude Desktop ←→ mcp_bridge.py ←→ HTTP API ←→ USDA FoodData Central
     (MCP)              ↑              ↑              ↑
                   Smart Bridge    FastAPI       Rate Limited
                                                   Client
```

**Key Implementation Details:**
- `src/mcp_server.py` - FastMCP protocol server
- `src/mcp_http_server.py` - FastAPI HTTP server  
- `src/mcp_bridge.py` - Smart bridge with server auto-detection
- `src/usda_client.py` - Production API client with retry logic
- `src/models/` - Type-safe Pydantic schemas

### Smart Bridge Logic
The bridge automatically detects server type and provides appropriate user feedback:
```python
# Hosted service detection
if "usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app" in args.server_url:
    print("🌐 Using hosted service (1,000 requests/hour shared)")

# Local development  
elif "localhost" in args.server_url:
    print("🏠 Using local server (requires your USDA API key)")
```

## 📦 Installation & Development

```bash
# Clone and setup
git clone https://github.com/zen-apps/mcp-nutrition-tools
cd mcp-nutrition-tools
pip install -r requirements.txt

# Get USDA API key (for local development)
# Visit: https://fdc.nal.usda.gov/api-guide.html
echo "FDC_API_KEY=your_key_here" > .env

# Test MCP server
python -m src.mcp_server

# Test HTTP server  
python -m src.mcp_http_server

# Run tests
python -m pytest tests/ -v

# Code quality
ruff check src/
ruff format src/
mypy src/
```

## 🐳 Deployment Options

### Local Development
```bash
# Run HTTP server locally
python -m src.mcp_http_server

# Run with Docker
make up
```

### Production Deployment
```bash
# Deploy to Google Cloud Run
export FDC_API_KEY="your_usda_key"
./scripts/deploy-gcp.sh
```

The production deployment includes:
- Automatic SSL/HTTPS
- Health checks and monitoring
- Auto-scaling based on demand
- Rate limiting and retry logic
- Structured logging

## 🔑 Configuration

### Environment Variables
- `FDC_API_KEY` - USDA FoodData Central API key (required for local)
- `ENVIRONMENT` - "development" or "production"  
- `LOG_LEVEL` - Logging level (DEBUG, INFO, etc.)

### Rate Limits
- **Hosted Service**: 1,000 requests/hour (shared)
- **Local Deployment**: 1,000 requests/hour (your key)
- **Enterprise**: Contact for higher limits

## 🧪 Testing Strategy

```bash
# Quick connectivity test
python test_quick.py

# Full test suite with mocking
python -m pytest tests/ -v

# Test specific MCP tools
python examples/live_demo.py
```

The test suite includes:
- USDA API mocking with httpx-mock
- Async MCP server testing
- Integration test examples
- Performance benchmarking

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Run tests: `python -m pytest tests/`
4. Run linting: `ruff check src/`
5. Submit pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**🎯 Ready to use? See [examples/configs/claude_desktop_config_examples.json](examples/configs/claude_desktop_config_examples.json) for setup instructions!**

**🔗 Live API: https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app/docs**