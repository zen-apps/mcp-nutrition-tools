#!/usr/bin/env python3
"""
Agent Integration Test Examples
===============================

Demonstrates how different AI agents can integrate with the USDA Nutrition MCP Server.
Shows practical examples for Claude (MCP), OpenAI (Function Calling), and LangChain.
"""

import asyncio
import httpx
import json
import os
from typing import Dict, Any

# =============================================================================
# BASE API CLIENT
# =============================================================================


class USDANutritionAPI:
    """Client for the USDA Nutrition MCP HTTP API"""

    def __init__(self, base_url: str = None):
        # Default to environment variable or production URL
        if base_url is None:
            self.base_url = os.getenv("NUTRITION_API_URL", "https://your-service-url.run.app")
        else:
            self.base_url = base_url

    async def search_foods(self, query: str, page_size: int = 10) -> Dict[str, Any]:
        """Search for foods"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/tools/search_foods",
                json={"query": query, "page_size": page_size},
            )
            return response.json()

    async def get_nutrition(self, fdc_id: int) -> Dict[str, Any]:
        """Get food nutrition details"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/tools/get_food_nutrition", json={"fdc_id": fdc_id}
            )
            return response.json()

    async def compare_foods(self, fdc_ids: list) -> Dict[str, Any]:
        """Compare multiple foods"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/tools/compare_foods", json={"fdc_ids": fdc_ids}
            )
            return response.json()


# =============================================================================
# CLAUDE MCP INTEGRATION
# =============================================================================


async def claude_mcp_demo():
    """
    Demo: How Claude Desktop would use MCP tools

    In Claude Desktop, users simply ask questions and Claude automatically
    calls the appropriate MCP tools. This simulates that workflow.
    """
    print("🤖 Claude MCP Integration Demo")
    print("=" * 50)

    # Simulate user question: "What are good high-protein foods for athletes?"
    user_question = "What are good high-protein foods for athletes?"
    print(f"User: {user_question}")
    print()

    print(
        "Claude (thinking): I'll search for high-protein foods, get detailed nutrition, and compare options."
    )
    print()

    api = USDANutritionAPI()

    # Step 1: Search for protein-rich foods
    print("🔍 Claude calls: search_foods('high protein')")
    search_result = await api.search_foods("high protein", page_size=5)

    if search_result.get("success") and search_result["data"].get("foods"):
        foods = search_result["data"]["foods"][:3]  # Top 3 results
        print(f"   Found {len(foods)} protein sources:")

        fdc_ids = []
        for food in foods:
            fdc_id = food.get("fdc_id")
            if fdc_id:
                fdc_ids.append(fdc_id)
                print(f"   - {food.get('description')} (ID: {fdc_id})")
        print()

        # Step 2: Get detailed nutrition for first food
        if fdc_ids:
            print(f"🔬 Claude calls: get_food_nutrition({fdc_ids[0]})")
            nutrition = await api.get_nutrition(fdc_ids[0])

            if nutrition.get("success"):
                macros = nutrition["data"]["nutrition"]["macronutrients"]
                protein = macros.get("Protein", {}).get("amount", "N/A")
                calories = macros.get("Energy (kcal)", {}).get("amount", "N/A")
                print(f"   Protein: {protein}g per 100g")
                print(f"   Calories: {calories}kcal per 100g")
                print()

        # Step 3: Compare top foods
        if len(fdc_ids) >= 2:
            print(f"⚖️ Claude calls: compare_foods({fdc_ids[:2]})")
            comparison = await api.compare_foods(fdc_ids[:2])

            if comparison.get("success"):
                nutrients = comparison["data"]["nutrient_comparison"]
                if "Protein" in nutrients:
                    print("   Protein comparison:")
                    for item in nutrients["Protein"]:
                        print(f"   - {item['food']}: {item['amount']}g")
                print()

    # Claude's synthesized response
    print("💬 Claude responds:")
    print(
        "Based on the USDA database, excellent high-protein foods for athletes include:"
    )
    print("- Chicken breast: ~31g protein per 100g, lean and versatile")
    print("- Fish like salmon: ~25g protein plus healthy omega-3s")
    print("- Greek yogurt: High protein with probiotics")
    print()
    print("For athletes, aim for 1.6-2.2g protein per kg body weight daily.")
    print("These whole food sources provide complete amino acid profiles.")


# =============================================================================
# OPENAI FUNCTION CALLING INTEGRATION
# =============================================================================


async def openai_function_demo():
    """
    Demo: OpenAI GPT with function calling

    Shows how to define functions that GPT can call to access nutrition data.
    """
    print("🤖 OpenAI Function Calling Demo")
    print("=" * 50)

    # Function definitions that would be sent to OpenAI
    function_definitions = [
        {
            "name": "search_nutrition_foods",
            "description": "Search the USDA database for foods by keywords",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term for foods"},
                    "page_size": {
                        "type": "integer",
                        "default": 10,
                        "description": "Number of results",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_food_nutrition_details",
            "description": "Get detailed nutrition information for a specific food",
            "parameters": {
                "type": "object",
                "properties": {
                    "fdc_id": {
                        "type": "integer",
                        "description": "USDA FoodData Central ID",
                    }
                },
                "required": ["fdc_id"],
            },
        },
        {
            "name": "compare_nutrition_foods",
            "description": "Compare nutritional information between multiple foods",
            "parameters": {
                "type": "object",
                "properties": {
                    "fdc_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of FDC IDs to compare",
                    }
                },
                "required": ["fdc_ids"],
            },
        },
    ]

    print("📋 Function definitions sent to OpenAI:")
    for func in function_definitions:
        print(f"   - {func['name']}: {func['description']}")
    print()

    # Simulate GPT deciding to call functions
    user_query = "Compare the protein content of chicken breast and tofu"
    print(f"User: {user_query}")
    print()

    print("🧠 GPT decides to call functions:")
    print("   1. search_nutrition_foods('chicken breast')")
    print("   2. search_nutrition_foods('tofu')")
    print("   3. compare_nutrition_foods([chicken_id, tofu_id])")
    print()

    # Execute the function calls
    api = USDANutritionAPI()

    # Function call 1
    chicken_result = await api.search_foods("chicken breast", page_size=1)
    chicken_fdc = None
    if chicken_result.get("success") and chicken_result["data"].get("foods"):
        chicken_fdc = chicken_result["data"]["foods"][0].get("fdc_id")
        print(f"🐔 Found chicken breast: FDC ID {chicken_fdc}")

    # Function call 2
    tofu_result = await api.search_foods("tofu", page_size=1)
    tofu_fdc = None
    if tofu_result.get("success") and tofu_result["data"].get("foods"):
        tofu_fdc = tofu_result["data"]["foods"][0].get("fdc_id")
        print(f"🥩 Found tofu: FDC ID {tofu_fdc}")

    # Function call 3
    if chicken_fdc and tofu_fdc:
        comparison = await api.compare_foods([chicken_fdc, tofu_fdc])
        if comparison.get("success"):
            nutrients = comparison["data"]["nutrient_comparison"]
            print("\n⚖️ Comparison results:")
            if "Protein" in nutrients:
                for item in nutrients["Protein"]:
                    print(f"   - {item['food']}: {item['amount']}g protein per 100g")
    print()

    print("💬 GPT synthesizes response:")
    print("Chicken breast contains significantly more protein (~31g per 100g) compared")
    print("to tofu (~8-15g per 100g). However, tofu is a complete plant protein and")
    print("excellent for vegetarians. Choose based on your dietary preferences!")


# =============================================================================
# LANGCHAIN INTEGRATION
# =============================================================================


async def langchain_demo():
    """
    Demo: LangChain agent with nutrition tools

    Shows how to create LangChain tools and use them in an agent workflow.
    """
    print("🤖 LangChain Agent Demo")
    print("=" * 50)

    # Simulated LangChain tool definitions
    print("🔧 LangChain tools defined:")

    langchain_tools = [
        {
            "name": "search_foods",
            "description": "Search for foods in the USDA nutrition database",
            "implementation": "Wraps HTTP call to /tools/search_foods",
        },
        {
            "name": "get_food_nutrition",
            "description": "Get detailed nutrition info for a specific food by FDC ID",
            "implementation": "Wraps HTTP call to /tools/get_food_nutrition",
        },
        {
            "name": "compare_foods_nutrition",
            "description": "Compare nutrition between multiple foods",
            "implementation": "Wraps HTTP call to /tools/compare_foods",
        },
    ]

    for tool in langchain_tools:
        print(f"   - {tool['name']}: {tool['description']}")
    print()

    # Simulate agent planning
    user_question = (
        "I'm trying to lose weight. What are some low-calorie, high-fiber foods?"
    )
    print(f"User: {user_question}")
    print()

    print("🤔 LangChain Agent planning:")
    print("   Step 1: Search for 'low calorie high fiber' foods")
    print("   Step 2: Get detailed nutrition for promising options")
    print("   Step 3: Analyze and recommend based on calorie/fiber ratio")
    print()

    # Execute the plan
    api = USDANutritionAPI()

    print("📋 Executing plan:")

    # Step 1: Search
    print("   🔍 Searching for low-calorie, high-fiber foods...")
    search_result = await api.search_foods("broccoli spinach apple", page_size=3)

    foods_to_analyze = []
    if search_result.get("success") and search_result["data"].get("foods"):
        for food in search_result["data"]["foods"]:
            fdc_id = food.get("fdc_id")
            if fdc_id:
                foods_to_analyze.append(
                    {"name": food.get("description"), "fdc_id": fdc_id}
                )
                print(f"      - Found: {food.get('description')}")
    print()

    # Step 2: Get nutrition details
    print("   🔬 Analyzing nutrition profiles...")
    food_analyses = []

    for food in foods_to_analyze[:2]:  # Analyze first 2
        nutrition = await api.get_nutrition(food["fdc_id"])
        if nutrition.get("success"):
            macros = nutrition["data"]["nutrition"]["macronutrients"]
            calories = macros.get("Energy (kcal)", {}).get("amount", 0)
            fiber = macros.get("Fiber", {}).get("amount", 0)

            food_analyses.append(
                {
                    "name": food["name"],
                    "calories": calories,
                    "fiber": fiber,
                    "fiber_per_calorie": fiber / calories if calories > 0 else 0,
                }
            )

            print(f"      - {food['name']}: {calories}kcal, {fiber}g fiber")
    print()

    # Step 3: Make recommendations
    print("💬 LangChain Agent recommends:")
    if food_analyses:
        # Sort by fiber per calorie ratio
        food_analyses.sort(key=lambda x: x["fiber_per_calorie"], reverse=True)

        print("Top low-calorie, high-fiber foods for weight loss:")
        for i, food in enumerate(food_analyses, 1):
            ratio = food["fiber_per_calorie"]
            print(f"{i}. {food['name']}")
            print(f"   - {food['calories']} calories, {food['fiber']}g fiber per 100g")
            print(f"   - Fiber efficiency: {ratio:.3f}g fiber per calorie")
            print()

        print("💡 Tips:")
        print("- High fiber helps you feel full with fewer calories")
        print("- Aim for foods with >3g fiber per 100 calories")
        print("- These vegetables are excellent for sustainable weight loss")


# =============================================================================
# PERFORMANCE COMPARISON
# =============================================================================


async def compare_agent_approaches():
    """Compare the different agent integration approaches"""
    print("📊 Agent Integration Comparison")
    print("=" * 50)

    comparison = {
        "Claude MCP": {
            "setup_complexity": "Low",
            "api_calls_required": "None (direct tool access)",
            "latency": "Lowest (native integration)",
            "user_experience": "Seamless conversation",
            "flexibility": "Limited to Claude Desktop",
            "best_for": "End users wanting AI nutrition assistant",
        },
        "OpenAI Functions": {
            "setup_complexity": "Medium",
            "api_calls_required": "HTTP requests to nutrition API",
            "latency": "Medium (HTTP overhead)",
            "user_experience": "Natural but requires orchestration",
            "flexibility": "Works with any OpenAI-compatible model",
            "best_for": "Custom applications and chatbots",
        },
        "LangChain": {
            "setup_complexity": "High",
            "api_calls_required": "HTTP requests + agent framework",
            "latency": "Highest (multiple layers)",
            "user_experience": "Highly customizable",
            "flexibility": "Extremely flexible, many integrations",
            "best_for": "Complex workflows and enterprise applications",
        },
    }

    for approach, details in comparison.items():
        print(f"🤖 {approach}:")
        for key, value in details.items():
            print(f"   {key.replace('_', ' ').title()}: {value}")
        print()


# =============================================================================
# MAIN DEMO RUNNER
# =============================================================================


async def main():
    """Run all agent integration demos"""
    print("🥗 USDA Nutrition MCP Server - Agent Integration Demos")
    print("=" * 60)
    print()

    try:
        # Test server connectivity
        api = USDANutritionAPI()
        test_result = await api.search_foods("apple", page_size=1)

        if not test_result.get("success"):
            print("❌ Cannot connect to nutrition server.")
            print(f"Please ensure the server is running at {api.base_url}")
            print("Set NUTRITION_API_URL environment variable for custom URL")
            return

        print("✅ Server connection successful!")
        print()

        # Run demos
        await claude_mcp_demo()
        print("\n" + "=" * 60 + "\n")

        await openai_function_demo()
        print("\n" + "=" * 60 + "\n")

        await langchain_demo()
        print("\n" + "=" * 60 + "\n")

        await compare_agent_approaches()

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("Please ensure the USDA Nutrition MCP Server is running.")


if __name__ == "__main__":
    asyncio.run(main())
