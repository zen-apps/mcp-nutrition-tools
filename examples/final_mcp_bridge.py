#!/usr/bin/env python3
"""
Final working MCP Bridge for USDA Nutrition Server
"""

import asyncio
import json
import httpx
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

HTTP_SERVER_URL = "http://localhost:8080"
server = Server("usda-nutrition")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_foods",
            description="Search for foods in the USDA database",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Food search term"},
                    "page_size": {"type": "integer", "default": 10, "maximum": 50},
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
                    "fdc_id": {"type": "integer", "description": "USDA Food ID"},
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
        types.Tool(
            name="nutrition_question_helper",
            description="Get guidance for nutrition questions",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Your nutrition question",
                    }
                },
                "required": ["question"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{HTTP_SERVER_URL}/tools/{name}", json=arguments or {}
            )
            data = response.json()

            if data.get("success"):
                # Format the response nicely
                result = format_response(name, data.get("data", {}))
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


def format_response(tool_name: str, data: dict) -> str:
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


async def main():
    # Test connection first
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{HTTP_SERVER_URL}/health")
            print("✅ Connected to nutrition server!")
    except Exception as e:
        print(f"❌ Cannot connect to {HTTP_SERVER_URL}: {e}")
        print("Make sure your Docker container is running on port 8080")
        return

    print("🚀 Starting MCP bridge...")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        from mcp.server import NotificationOptions

        init_options = InitializationOptions(
            server_name="usda-nutrition",
            server_version="1.0.0",
            capabilities=server.get_capabilities(
                notification_options=NotificationOptions(), experimental_capabilities={}
            ),
        )

        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())
