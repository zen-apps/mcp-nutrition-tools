#!/usr/bin/env python3
"""
MCP Bridge for USDA Nutrition HTTP Server
Connects Claude Desktop to deployed HTTP server

Usage:
    python src/mcp_bridge.py --server-url http://localhost:8080
    python src/mcp_bridge.py --server-url https://your-deployed-server.com
"""

import argparse
import asyncio
import json
import logging
from typing import Any
import httpx
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nutrition-bridge")

def parse_args():
    parser = argparse.ArgumentParser(description="MCP Bridge for USDA Nutrition Server")
    parser.add_argument(
        "--server-url",
        default="http://localhost:8080",
        help="URL of the nutrition HTTP server"
    )
    return parser.parse_args()

class NutritionMCPBridge:
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        self.server = Server("usda-nutrition")
        self.setup_tools()

    def setup_tools(self):
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name="search_foods",
                    description="Search for foods in the USDA database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Food search term"},
                            "page_size": {"type": "integer", "default": 10, "maximum": 50}
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="get_food_nutrition",
                    description="Get detailed nutrition information for a specific food",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "fdc_id": {"type": "integer", "description": "USDA Food ID"},
                            "format": {"type": "string", "default": "abridged", "enum": ["abridged", "full"]}
                        },
                        "required": ["fdc_id"]
                    }
                ),
                types.Tool(
                    name="compare_foods",
                    description="Compare nutrition between multiple foods",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "fdc_ids": {"type": "array", "items": {"type": "integer"}, "maxItems": 5}
                        },
                        "required": ["fdc_ids"]
                    }
                ),
                types.Tool(
                    name="nutrition_question_helper",
                    description="Get guidance for nutrition questions",
                    inputSchema={
                        "type": "object", 
                        "properties": {
                            "question": {"type": "string", "description": "Your nutrition question"}
                        },
                        "required": ["question"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.server_url}/tools/{name}",
                        json=arguments or {}
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("success"):
                        result = self.format_response(name, data.get("data", {}))
                        return [types.TextContent(type="text", text=result)]
                    else:
                        error_msg = data.get("error", "Unknown error occurred")
                        return [types.TextContent(type="text", text=f"❌ Error: {error_msg}")]
                        
            except httpx.TimeoutException:
                return [types.TextContent(type="text", text="⏰ Request timed out. Please try again.")]
            except httpx.HTTPError as e:
                return [types.TextContent(type="text", text=f"🌐 HTTP Error: {str(e)}")]
            except Exception as e:
                logger.error(f"Tool {name} failed: {e}")
                return [types.TextContent(type="text", text=f"💥 Error calling {name}: {str(e)}")]

    def format_response(self, tool_name: str, data: dict) -> str:
        """Format API response for Claude"""
        
        if tool_name == "search_foods":
            foods = data.get("foods", [])
            if not foods:
                return "🔍 No foods found for your search. Try different keywords!"
            
            result = f"🍎 Found {len(foods)} foods:\n\n"
            for i, food in enumerate(foods, 1):
                result += f"{i}. **{food.get('description', 'Unknown')}** (ID: {food.get('fdc_id')})\n"
                if food.get('brand_owner'):
                    result += f"   🏢 Brand: {food.get('brand_owner')}\n"
                result += f"   📋 Type: {food.get('data_type', 'Unknown')}\n\n"
            
            result += "💡 Use `get_food_nutrition` with an ID to see detailed nutrition info!"
            return result
            
        elif tool_name == "get_food_nutrition":
            food_info = data.get("food_info", {})
            nutrition = data.get("nutrition", {})
            
            result = f"🥘 **{food_info.get('description', 'Unknown Food')}**\n"
            result += f"📊 ID: {food_info.get('fdc_id')}\n\n"
            
            # Macronutrients
            macros = nutrition.get("macronutrients", {})
            if macros:
                result += "⚡ **Macronutrients (per 100g):**\n"
                for nutrient, info in macros.items():
                    amount = info.get('amount', 0)
                    unit = info.get('unit', '')
                    result += f"• {nutrient}: {amount}{unit}\n"
                result += "\n"
            
            # Vitamins
            vitamins = nutrition.get("vitamins", {})
            if vitamins:
                result += "🌟 **Vitamins:**\n"
                for nutrient, info in vitamins.items():
                    amount = info.get('amount', 0)
                    unit = info.get('unit', '')
                    result += f"• {nutrient}: {amount}{unit}\n"
                result += "\n"
                
            # Minerals
            minerals = nutrition.get("minerals", {})
            if minerals:
                result += "⛰️ **Minerals:**\n"
                for nutrient, info in minerals.items():
                    amount = info.get('amount', 0)
                    unit = info.get('unit', '')
                    result += f"• {nutrient}: {amount}{unit}\n"
                result += "\n"
                
            return result
            
        elif tool_name == "compare_foods":
            foods = data.get("foods", [])
            comparison = data.get("nutrient_comparison", {})
            
            result = "⚖️ **Food Comparison (per 100g):**\n\n"
            
            result += "📋 **Foods being compared:**\n"
            for i, food in enumerate(foods, 1):
                result += f"{i}. {food.get('description', 'Unknown')}\n"
            result += "\n"
            
            for nutrient, food_data in comparison.items():
                result += f"🔍 **{nutrient}:**\n"
                for item in food_data:
                    food_name = item.get('food', 'Unknown')
                    amount = item.get('amount', 0)
                    unit = item.get('unit', '')
                    result += f"• {food_name}: {amount}{unit}\n"
                result += "\n"
                
            return result
            
        elif tool_name == "nutrition_question_helper":
            question = data.get("question", "")
            suggestions = data.get("suggested_searches", [])
            tips = data.get("tips", [])
            
            result = f"❓ **Your question:** {question}\n\n"
            
            if suggestions:
                result += "🔍 **Suggested foods to search for:**\n"
                for suggestion in suggestions:
                    result += f"• {suggestion}\n"
                result += "\n"
            
            if tips:
                result += "💡 **Tips:**\n"
                for tip in tips:
                    result += f"• {tip}\n"
                result += "\n"
                    
            return result
        
        else:
            # Fallback for any other tools
            return json.dumps(data, indent=2)

    async def run(self):
        """Run the MCP bridge"""
        # Test connection to HTTP server
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.server_url}/health")
                logger.info(f"✅ Connected to nutrition server at {self.server_url}")
        except Exception as e:
            logger.error(f"❌ Cannot connect to {self.server_url}: {e}")
            logger.info("Make sure the HTTP server is running and accessible")
            return
        
        logger.info("🚀 Starting MCP bridge...")
        
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            init_options = InitializationOptions(
                server_name="usda-nutrition",
                server_version="1.0.0",
                capabilities=self.server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
            
            await self.server.run(read_stream, write_stream, init_options)

def main():
    args = parse_args()
    bridge = NutritionMCPBridge(args.server_url)
    asyncio.run(bridge.run())

if __name__ == "__main__":
    main()