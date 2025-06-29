# Claude Desktop Setup Guide

## Quick Start Options

### Option 1: Use Deployed HTTP Server (Recommended)

The easiest way to get started is using our deployed server with the MCP bridge:

```bash
# Clone the repository
git clone https://github.com/your-username/mcp-nutrition-tools
cd mcp-nutrition-tools

# Install dependencies
pip install -r requirements.txt

# Configure Claude Desktop
mkdir -p ~/Library/Application\ Support/Claude/
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "usda-nutrition": {
      "command": "python",
      "args": ["src/mcp_bridge.py", "--server-url", "https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app"],
      "cwd": "/path/to/your/mcp-nutrition-tools"
    }
  }
}
EOF

# Restart Claude Desktop
```

### Option 2: Run Local Native MCP Server

For full local control:

```bash
# Get USDA API key from https://fdc.nal.usda.gov/api-guide.html
export USDA_API_KEY="your-api-key-here"

# Configure Claude Desktop for native MCP
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "usda-nutrition": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/path/to/your/mcp-nutrition-tools",
      "env": {
        "USDA_API_KEY": "your-api-key-here"
      }
    }
  }
}
EOF
```

### Option 3: Use Your Own Deployed Server

If you deploy your own HTTP server:

```bash
# Deploy using Docker
docker build -t nutrition-mcp .
docker run -p 8080:8080 -e USDA_API_KEY=your-key nutrition-mcp

# Configure bridge to use your server
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "usda-nutrition": {
      "command": "python",
      "args": ["src/mcp_bridge.py", "--server-url", "https://your-deployed-server.com"],
      "cwd": "/path/to/your/mcp-nutrition-tools"
    }
  }
}
EOF
```

## Testing

After configuration, restart Claude Desktop and try:

- "Search for chicken breast nutrition"
- "Compare salmon vs beef protein content"  
- "Find foods high in iron"
- "What's the nutrition in quinoa?"

## Troubleshooting

### Tools not showing up?
- Ensure Claude Desktop was completely restarted
- Check file paths in config are correct
- Verify the server is accessible

### Bridge connection errors?
- Check server URL is correct and accessible
- Ensure dependencies are installed: `pip install mcp httpx`
- Test server health: `curl https://your-server.com/health`

### Permission errors?
- Make sure Python path is correct in config
- Try using full absolute paths
- Check file permissions on scripts