# API Usage for Developers

## Using the HTTP API Directly

The USDA Nutrition API is available at: **https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app**

### Available Endpoints

#### 1. Search Foods
```bash
curl -X POST "https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app/tools/search_foods" \
  -H "Content-Type: application/json" \
  -d '{"query": "apple", "page_size": 10}'
```

#### 2. Get Food Nutrition
```bash
curl -X POST "https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app/tools/get_food_nutrition" \
  -H "Content-Type: application/json" \
  -d '{"fdc_id": 171688, "format": "abridged"}'
```

#### 3. Compare Foods
```bash
curl -X POST "https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app/tools/compare_foods" \
  -H "Content-Type: application/json" \
  -d '{"fdc_ids": [171688, 171689]}'
```

#### 4. Health Check
```bash
curl "https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app/health"
```

### Interactive Documentation
Visit: **https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app/docs**

## Integration Examples

### Python with requests
```python
import requests

# Search for foods
response = requests.post(
    "https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app/tools/search_foods",
    json={"query": "banana", "page_size": 5}
)
foods = response.json()["data"]["foods"]

# Get nutrition for first result
fdc_id = foods[0]["fdc_id"]
nutrition = requests.post(
    "https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app/tools/get_food_nutrition",
    json={"fdc_id": fdc_id, "format": "abridged"}
)
print(nutrition.json())
```

### JavaScript/Node.js
```javascript
// Search foods
const searchResponse = await fetch(
  'https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app/tools/search_foods',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: 'chicken breast', page_size: 10 })
  }
);
const foods = await searchResponse.json();

// Get nutrition details
const nutritionResponse = await fetch(
  'https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app/tools/get_food_nutrition',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fdc_id: foods.data.foods[0].fdc_id })
  }
);
const nutrition = await nutritionResponse.json();
```

## Rate Limits

- **Hosted Service**: 1,000 requests per hour (shared across all users)
- **Local Deployment**: Unlimited (requires your own USDA API key)

## Integration Options

There are **two main ways** to use this nutrition service:

1. **🔗 HTTP API Integration** - Direct API calls for custom applications
2. **🔌 MCP Integration** - Native protocol support for MCP-compatible clients

---

## 🔗 HTTP API Integration (Custom Applications)

Use these examples when building custom applications that need nutrition data.

### OpenAI Function Calling
```python
import openai
import requests
import json

# Define nutrition tools for OpenAI
nutrition_tools = [
    {
        "type": "function",
        "function": {
            "name": "search_foods",
            "description": "Search USDA database for foods by name or keywords",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Food search term (e.g., 'chicken breast', 'apple')"},
                    "page_size": {"type": "integer", "default": 10, "description": "Number of results to return (max 50)"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "get_food_nutrition",
            "description": "Get detailed nutrition information for a specific food by FDC ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "fdc_id": {"type": "integer", "description": "USDA Food ID from search results"},
                    "format": {"type": "string", "enum": ["abridged", "full"], "default": "abridged"}
                },
                "required": ["fdc_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_foods", 
            "description": "Compare nutritional information between multiple foods",
            "parameters": {
                "type": "object",
                "properties": {
                    "fdc_ids": {
                        "type": "array", 
                        "items": {"type": "integer"},
                        "description": "List of USDA Food IDs to compare",
                        "maxItems": 5
                    }
                },
                "required": ["fdc_ids"]
            }
        }
    }
]

def call_nutrition_api(function_name, arguments):
    """Execute nutrition API call and return results"""
    try:
        response = requests.post(
            f"https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app/tools/{function_name}",
            json=arguments,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"API call failed: {str(e)}"}

def nutrition_assistant(user_query):
    """Complete nutrition assistant with OpenAI + USDA API"""
    client = openai.OpenAI()  # Assumes OPENAI_API_KEY in environment
    
    messages = [
        {
            "role": "system", 
            "content": """You are a nutrition expert with access to the USDA FoodData Central database.
            
            When users ask about nutrition, food comparisons, or dietary advice:
            1. Use search_foods to find relevant foods
            2. Use get_food_nutrition to get detailed nutritional data
            3. Use compare_foods to analyze multiple foods side-by-side
            4. Provide practical, evidence-based nutrition advice
            
            Always cite the specific foods and their FDC IDs in your responses."""
        },
        {"role": "user", "content": user_query}
    ]
    
    # Initial LLM call with function tools
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=nutrition_tools,
        tool_choice="auto"
    )
    
    response_message = response.choices[0].message
    messages.append(response_message)
    
    # Process function calls
    if response_message.tool_calls:
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            print(f"🔍 Calling {function_name} with args: {function_args}")
            
            # Execute the nutrition API call
            function_result = call_nutrition_api(function_name, function_args)
            
            # Add function result to conversation
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": json.dumps(function_result)
            })
        
        # Get final response with function results
        final_response = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
        
        return final_response.choices[0].message.content
    
    return response_message.content

# Example usage
if __name__ == "__main__":
    # Example 1: Basic nutrition question
    question1 = "What's the protein content of chicken breast vs salmon?"
    print("Question:", question1)
    print("Answer:", nutrition_assistant(question1))
    print("\n" + "="*50 + "\n")
    
    # Example 2: Complex dietary advice
    question2 = "I'm trying to build muscle. What are the best high-protein, low-fat foods?"
    print("Question:", question2) 
    print("Answer:", nutrition_assistant(question2))
    print("\n" + "="*50 + "\n")
    
    # Example 3: Specific nutritional analysis
    question3 = "Compare the iron content in spinach, lentils, and beef for someone with iron deficiency"
    print("Question:", question3)
    print("Answer:", nutrition_assistant(question3))
```

#### Sample Conversation Flow:

**User:** *"What's the protein content of chicken breast vs salmon?"*

**OpenAI Function Calls:**
1. `search_foods({"query": "chicken breast", "page_size": 3})`
2. `search_foods({"query": "salmon", "page_size": 3})`  
3. `compare_foods({"fdc_ids": [171077, 175167]})`

**API Responses:**
```json
// search_foods("chicken breast")
{
  "success": true,
  "data": {
    "foods": [
      {"fdc_id": 171077, "description": "Chicken, broilers or fryers, breast, meat only, raw"}
    ]
  }
}

// compare_foods([171077, 175167])
{
  "success": true, 
  "data": {
    "nutrient_comparison": {
      "Protein": [
        {"food": "Chicken breast", "amount": 31.02, "unit": "g"},
        {"food": "Salmon", "amount": 25.44, "unit": "g"}
      ]
    }
  }
}
```

**Final Assistant Response:**
*"Based on USDA data, chicken breast contains significantly more protein than salmon per 100g serving:*

*• **Chicken breast** (FDC ID: 171077): **31.02g protein***
*• **Salmon** (FDC ID: 175167): **25.44g protein***

*Chicken breast provides about 22% more protein, making it the better choice for maximizing protein intake. However, salmon offers additional benefits like omega-3 fatty acids that chicken lacks."*

### LangChain Integration
```python
from langchain.tools import tool
import requests

@tool
def search_foods(query: str, page_size: int = 10) -> dict:
    """Search for foods in the USDA database"""
    response = requests.post(
        "https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app/tools/search_foods",
        json={"query": query, "page_size": page_size}
    )
    return response.json()

@tool 
def get_food_nutrition(fdc_id: int, format: str = "abridged") -> dict:
    """Get detailed nutrition information for a food"""
    response = requests.post(
        "https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app/tools/get_food_nutrition",
        json={"fdc_id": fdc_id, "format": format}
    )
    return response.json()
```

---

## 🔌 MCP Integration (Protocol-Based)

MCP (Model Context Protocol) provides **native integration** with AI assistants. The key advantage is that users don't need to write code - they just talk to their AI assistant naturally.

### MCP vs HTTP API Comparison

| **MCP Integration** | **HTTP API Integration** |
|---|---|
| ✅ Zero coding required | ❌ Requires custom code |
| ✅ Native AI assistant integration | ❌ Manual tool orchestration |
| ✅ Automatic tool discovery | ❌ Manual function definitions |
| ✅ Seamless user experience | ❌ Developer-focused |
| ❌ Limited to MCP clients | ✅ Works with any framework |

### Using MCP Bridge with Python MCP Client

```python
import asyncio
import subprocess
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def use_nutrition_mcp():
    """Example of using the nutrition MCP bridge with a Python MCP client"""
    
    # Start the MCP bridge as a subprocess
    server_params = StdioServerParameters(
        command="python3",
        args=[
            "/path/to/mcp-nutrition-tools/src/mcp_bridge.py",
            "--server-url", 
            "https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app"
        ],
        cwd="/path/to/mcp-nutrition-tools"
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the MCP session
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print("Available MCP tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # Search for foods
            search_result = await session.call_tool(
                "search_foods",
                {"query": "chicken breast", "page_size": 3}
            )
            print(f"\nSearch results: {search_result.content[0].text}")
            
            # Get nutrition details for first result
            # Note: You'd parse the search_result to get the FDC ID
            nutrition_result = await session.call_tool(
                "get_food_nutrition", 
                {"fdc_id": 171077}  # Example FDC ID
            )
            print(f"\nNutrition details: {nutrition_result.content[0].text}")
            
            # Compare multiple foods
            compare_result = await session.call_tool(
                "compare_foods",
                {"fdc_ids": [171077, 175167]}  # Chicken breast vs salmon
            )
            print(f"\nFood comparison: {compare_result.content[0].text}")

# Run the example
if __name__ == "__main__":
    asyncio.run(use_nutrition_mcp())
```

### Using MCP Bridge with Custom MCP Client

```python
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class NutritionMCPClient:
    def __init__(self, bridge_path="/path/to/mcp-nutrition-tools/src/mcp_bridge.py"):
        self.bridge_path = bridge_path
        self.session = None
    
    async def __aenter__(self):
        server_params = StdioServerParameters(
            command="python3",
            args=[
                self.bridge_path,
                "--server-url",
                "https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app"  # or your custom server
            ]
        )
        
        self._stdio_context = stdio_client(server_params)
        read, write = await self._stdio_context.__aenter__()
        
        self._session_context = ClientSession(read, write)
        self.session = await self._session_context.__aenter__()
        
        await self.session.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session_context:
            await self._session_context.__aexit__(exc_type, exc_val, exc_tb)
        if self._stdio_context:
            await self._stdio_context.__aexit__(exc_type, exc_val, exc_tb)
    
    async def search_foods(self, query: str, page_size: int = 10):
        """Search for foods using MCP"""
        result = await self.session.call_tool(
            "search_foods",
            {"query": query, "page_size": page_size}
        )
        return result.content[0].text
    
    async def get_nutrition(self, fdc_id: int):
        """Get nutrition details using MCP"""
        result = await self.session.call_tool(
            "get_food_nutrition",
            {"fdc_id": fdc_id}
        )
        return result.content[0].text
    
    async def compare_foods(self, fdc_ids: list):
        """Compare foods using MCP"""
        result = await self.session.call_tool(
            "compare_foods",
            {"fdc_ids": fdc_ids}
        )
        return result.content[0].text

# Usage example
async def nutrition_analysis():
    async with NutritionMCPClient() as client:
        # Search for protein sources
        search_result = await client.search_foods("high protein")
        print("Search results:", search_result)
        
        # Compare chicken vs salmon
        comparison = await client.compare_foods([171077, 175167])
        print("Comparison:", comparison)

# Run the analysis
asyncio.run(nutrition_analysis())
```

### Using MCP with Node.js/TypeScript

```typescript
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

class NutritionMCPClient {
    private client: Client;
    private transport: StdioClientTransport;

    constructor(bridgePath: string = '/path/to/mcp-nutrition-tools/src/mcp_bridge.py') {
        this.transport = new StdioClientTransport({
            command: 'python3',
            args: [
                bridgePath,
                '--server-url',
                'https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app'
            ]
        });
        this.client = new Client({
            name: "nutrition-client",
            version: "1.0.0"
        }, {
            capabilities: {}
        });
    }

    async connect() {
        await this.client.connect(this.transport);
    }

    async searchFoods(query: string, pageSize: number = 10) {
        const result = await this.client.request(
            { method: "tools/call" },
            {
                name: "search_foods",
                arguments: { query, page_size: pageSize }
            }
        );
        return result.content[0].text;
    }

    async getNutrition(fdcId: number) {
        const result = await this.client.request(
            { method: "tools/call" },
            {
                name: "get_food_nutrition", 
                arguments: { fdc_id: fdcId }
            }
        );
        return result.content[0].text;
    }

    async close() {
        await this.client.close();
    }
}

// Usage
async function main() {
    const client = new NutritionMCPClient();
    
    try {
        await client.connect();
        
        const searchResult = await client.searchFoods("chicken breast");
        console.log("Search results:", searchResult);
        
        const nutrition = await client.getNutrition(171077);
        console.log("Nutrition:", nutrition);
        
    } finally {
        await client.close();
    }
}

main().catch(console.error);
```

### Why Use MCP vs Direct HTTP API?

**Choose MCP when:**
- Building AI assistants or agents
- Want automatic tool discovery  
- Need seamless user experience (no coding)
- Working with MCP-compatible frameworks

**Choose HTTP API when:**
- Building custom applications
- Need full control over data processing
- Working with non-MCP frameworks
- Building web apps, mobile apps, etc.

### MCP Client Libraries

- **Python**: `mcp` package
- **TypeScript/Node.js**: `@modelcontextprotocol/sdk`
- **Other languages**: See [MCP documentation](https://modelcontextprotocol.io/)

## Local Deployment

To run unlimited requests with your own USDA API key:

1. Get API key from: https://fdc.nal.usda.gov/api-guide.html
2. Run with Docker:
   ```bash
   docker run -p 8080:8080 -e FDC_API_KEY=your_key_here nutrition-mcp
   ```
3. Use `http://localhost:8080` as your API base URL

## Support

- API Documentation: https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app/docs
- Issues: Open an issue on GitHub
- Rate Limits: Contact for enterprise usage