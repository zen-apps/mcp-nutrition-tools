#!/usr/bin/env python3
"""
USDA Nutrition MCP Bridge
Supports both hosted and local deployment options

Usage:
    # Use hosted service (default, rate limited)
    python src/mcp_bridge.py

    # Use local deployment with your own API key
    python src/mcp_bridge.py --server-url http://localhost:8080

    # Use custom server
    python src/mcp_bridge.py --server-url https://your-server.com
"""

import argparse
import asyncio
import json
import httpx
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types


def parse_args():
    parser = argparse.ArgumentParser(description="USDA Nutrition MCP Bridge")
    parser.add_argument(
        "--server-url",
        default="https://usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app",
        help="URL of the nutrition HTTP server (default: hosted service)",
    )
    return parser.parse_args()


class NutritionMCPBridge:
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip("/")
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
                            "query": {
                                "type": "string",
                                "description": "Food search term",
                            },
                            "page_size": {
                                "type": "integer",
                                "default": 10,
                                "maximum": 50,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                types.Tool(
                    name="get_food_nutrition",
                    description="Get detailed nutrition information for a specific food",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "fdc_id": {
                                "type": "integer",
                                "description": "USDA Food ID",
                            },
                            "format": {
                                "type": "string",
                                "default": "abridged",
                                "enum": ["abridged", "full"],
                            },
                        },
                        "required": ["fdc_id"],
                    },
                ),
                types.Tool(
                    name="compare_foods",
                    description="Compare nutrition between multiple foods",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "fdc_ids": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "maxItems": 5,
                            }
                        },
                        "required": ["fdc_ids"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict | None
        ) -> list[types.TextContent]:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.server_url}/tools/{name}", json=arguments or {}
                    )
                    data = response.json()

                    if data.get("success"):
                        # Format the response nicely
                        result = self.format_response(name, data.get("data", {}))
                        return [types.TextContent(type="text", text=result)]
                    else:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"❌ Error: {data.get('error', 'Unknown error')}",
                            )
                        ]
            except Exception as e:
                return [types.TextContent(type="text", text=f"💥 Error: {str(e)}")]

    def format_response(self, tool_name: str, data: dict) -> str:
        """Format the response nicely for Claude"""
        if tool_name == "search_foods":
            foods = data.get("foods", [])
            if not foods:
                return "🔍 No foods found. Try different search terms!"

            result = f"🍎 Found {len(foods)} foods:\n\n"
            for i, food in enumerate(foods, 1):
                result += f"{i}. **{food.get('description', 'Unknown')}** (ID: {food.get('fdc_id')})\n"
                if food.get("brand_owner"):
                    result += f"   Brand: {food.get('brand_owner')}\n"
                result += f"   Type: {food.get('data_type', 'Unknown')}\n\n"
            return result

        elif tool_name == "get_food_nutrition":
            food_info = data.get("food_info", {})
            nutrition = data.get("nutrition", {})

            result = f"🥘 **{food_info.get('description', 'Unknown Food')}**\n\n"

            macros = nutrition.get("macronutrients", {})
            if macros:
                result += "**Macronutrients (per 100g):**\n"
                for nutrient, info in macros.items():
                    result += (
                        f"• {nutrient}: {info.get('amount', 0)}{info.get('unit', '')}\n"
                    )
                result += "\n"

            vitamins = nutrition.get("vitamins", {})
            if vitamins:
                result += "**Vitamins:**\n"
                for nutrient, info in vitamins.items():
                    result += (
                        f"• {nutrient}: {info.get('amount', 0)}{info.get('unit', '')}\n"
                    )
                result += "\n"

            minerals = nutrition.get("minerals", {})
            if minerals:
                result += "**Minerals:**\n"
                for nutrient, info in minerals.items():
                    result += (
                        f"• {nutrient}: {info.get('amount', 0)}{info.get('unit', '')}\n"
                    )

            return result

        else:
            # For other tools, return formatted JSON
            return json.dumps(data, indent=2)

    async def run(self):
        """Run the MCP bridge"""
        # Test connection first
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.server_url}/health")
                print(f"✅ Connected to nutrition server at {self.server_url}")
        except Exception as e:
            print(f"❌ Cannot connect to {self.server_url}: {e}")
            if "localhost" in self.server_url:
                print("💡 Make sure you're running the local server:")
                print(
                    "   docker run -p 8080:8080 -e USDA_API_KEY=your_key nutrition-mcp"
                )
            else:
                print("💡 Check if the server URL is correct and accessible")
            return

        print("🚀 Starting MCP bridge...")

        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            init_options = InitializationOptions(
                server_name="usda-nutrition",
                server_version="1.0.0",
                capabilities=self.server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            )

            await self.server.run(read_stream, write_stream, init_options)


def main():
    args = parse_args()

    # Show which server we're connecting to
    if "localhost" in args.server_url:
        print(f"🏠 Using local server: {args.server_url}")
        print("   (Requires your own USDA API key)")
    elif "usda-nutrition-mcp-oc46l7ob5a-uc.a.run.app" in args.server_url:
        print(f"🌐 Using hosted service: {args.server_url}")
        print("   (Shared rate limit: 1,000 requests/hour)")
    else:
        print(f"🔗 Using custom server: {args.server_url}")

    bridge = NutritionMCPBridge(args.server_url)
    asyncio.run(bridge.run())


if __name__ == "__main__":
    main()
