#!/usr/bin/env python3
"""
OpenAI Function Calling Test
============================

Direct OpenAI function calling integration with your MCP nutrition server.
This shows how to use OpenAI's function calling feature with your nutrition API.

Requirements:
    pip install openai httpx

Usage:
    export OPENAI_API_KEY="your_openai_key"
    export NUTRITION_API_URL="https://your-nutrition-server.run.app"
    python test_openai_functions.py
"""

import asyncio
import json
import httpx
import os
from openai import AsyncOpenAI


# =============================================================================
# NUTRITION API CLIENT
# =============================================================================

class NutritionAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
    
    async def search_foods(self, query: str, limit: int = 5):
        """Search for foods"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/tools/search_foods",
                json={"query": query, "page_size": limit}
            )
            return response.json()
    
    async def get_nutrition(self, fdc_id: int):
        """Get food nutrition details"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/tools/get_food_nutrition",
                json={"fdc_id": fdc_id}
            )
            return response.json()
    
    async def compare_foods(self, fdc_ids: list):
        """Compare multiple foods"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/tools/compare_foods",
                json={"fdc_ids": fdc_ids}
            )
            return response.json()


# =============================================================================
# OPENAI FUNCTION DEFINITIONS
# =============================================================================

# These are the function definitions that OpenAI will use
NUTRITION_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_nutrition_foods",
            "description": "Search the USDA nutrition database for foods by keywords",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term for foods (e.g., 'chicken breast', 'high protein')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return (1-10)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "get_food_nutrition_details",
            "description": "Get detailed nutrition information for a specific food",
            "parameters": {
                "type": "object",
                "properties": {
                    "fdc_id": {
                        "type": "integer",
                        "description": "USDA FoodData Central ID for the food"
                    }
                },
                "required": ["fdc_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_nutrition_foods",
            "description": "Compare nutritional information between multiple foods",
            "parameters": {
                "type": "object",
                "properties": {
                    "fdc_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of FDC IDs to compare (2-5 foods)"
                    }
                },
                "required": ["fdc_ids"]
            }
        }
    }
]


# =============================================================================
# FUNCTION EXECUTION HANDLER
# =============================================================================

async def execute_function_call(function_name: str, arguments: dict, nutrition_api: NutritionAPI):
    """Execute a function call from OpenAI"""
    
    if function_name == "search_nutrition_foods":
        query = arguments.get("query")
        limit = arguments.get("limit", 5)
        return await nutrition_api.search_foods(query, limit)
    
    elif function_name == "get_food_nutrition_details":
        fdc_id = arguments.get("fdc_id")
        return await nutrition_api.get_nutrition(fdc_id)
    
    elif function_name == "compare_nutrition_foods":
        fdc_ids = arguments.get("fdc_ids")
        return await nutrition_api.compare_foods(fdc_ids)
    
    else:
        return {"error": f"Unknown function: {function_name}"}


# =============================================================================
# OPENAI CHAT WITH FUNCTION CALLING
# =============================================================================

async def chat_with_nutrition_functions(user_query: str, nutrition_api: NutritionAPI):
    """Have a conversation with OpenAI using nutrition functions"""
    
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    messages = [
        {
            "role": "system",
            "content": """You are a nutrition expert with access to the USDA nutrition database. 
            
            You can search for foods, get detailed nutrition information, and compare foods.
            Always provide practical, evidence-based nutrition advice.
            When you get nutrition data, explain what it means in practical terms.
            Include portion recommendations when relevant."""
        },
        {
            "role": "user", 
            "content": user_query
        }
    ]
    
    print(f"🤖 User: {user_query}")
    print("🧠 OpenAI is thinking...")
    
    # First API call - OpenAI decides what functions to call
    response = await client.chat.completions.create(
        model="gpt-4o-mini",  # Use gpt-4 if available
        messages=messages,
        tools=NUTRITION_FUNCTIONS,
        tool_choice="auto"
    )
    
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    
    # Add the assistant's response to conversation
    messages.append(response_message)
    
    # Execute any function calls
    if tool_calls:
        print(f"🔧 OpenAI wants to call {len(tool_calls)} function(s):")
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            print(f"   📞 Calling {function_name}({function_args})")
            
            # Execute the function
            function_result = await execute_function_call(function_name, function_args, nutrition_api)
            
            # Add function result to conversation
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": json.dumps(function_result)
            })
        
        # Get final response from OpenAI
        print("🧠 OpenAI is synthesizing the results...")
        final_response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        
        final_answer = final_response.choices[0].message.content
        print(f"💬 OpenAI: {final_answer}")
        
    else:
        # No function calls needed
        print(f"💬 OpenAI: {response_message.content}")


# =============================================================================
# TEST SCENARIOS
# =============================================================================

async def test_openai_integration():
    """Test OpenAI function calling with nutrition API"""
    
    nutrition_api_url = os.getenv("NUTRITION_API_URL", "https://your-service-url.run.app")
    nutrition_api = NutritionAPI(nutrition_api_url)
    
    print("🥗 OpenAI Function Calling Test")
    print("=" * 50)
    print(f"🔗 Nutrition API: {nutrition_api_url}")
    print(f"🔑 OpenAI API Key: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Not set'}")
    print()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Please set OPENAI_API_KEY environment variable")
        return
    
    # Test connectivity
    print("🔗 Testing nutrition API connectivity...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{nutrition_api_url}/health")
            if response.status_code != 200:
                print(f"❌ Nutrition API not accessible (status {response.status_code})")
                return
    except Exception as e:
        print(f"❌ Cannot connect to nutrition API: {e}")
        return
    
    print("✅ Nutrition API is accessible!")
    print()
    
    # Test queries that should trigger function calls
    test_queries = [
        "What are the best high-protein foods for muscle building?",
        "Compare the protein content of chicken breast vs salmon",
        "I need foods rich in iron. Can you find some and tell me their iron content?",
        "What's the calorie difference between an apple and a banana?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*20} Test {i} {'='*20}")
        try:
            await chat_with_nutrition_functions(query, nutrition_api)
        except Exception as e:
            print(f"❌ Test {i} failed: {e}")
        
        print()
    
    print("=" * 50)
    print("🎉 OpenAI function calling test complete!")
    print("\n💡 What happened:")
    print("1. OpenAI analyzed each question")
    print("2. OpenAI decided which nutrition functions to call")
    print("3. Your MCP server provided the nutrition data")
    print("4. OpenAI synthesized the data into helpful answers")


# =============================================================================
# SIMPLE DEMO WITHOUT OPENAI
# =============================================================================

async def test_api_directly():
    """Test the nutrition API directly (no OpenAI required)"""
    print("\n📡 Direct API Test (No OpenAI needed)")
    print("-" * 30)
    
    nutrition_api_url = os.getenv("NUTRITION_API_URL", "https://your-service-url.run.app")
    nutrition_api = NutritionAPI(nutrition_api_url)
    
    try:
        # Test search
        print("🔍 Searching for 'chicken breast'...")
        search_result = await nutrition_api.search_foods("chicken breast", 2)
        
        if search_result.get("success"):
            foods = search_result["data"]["foods"]
            print(f"✅ Found {len(foods)} foods:")
            
            for food in foods:
                print(f"   • {food['description']} (ID: {food['fdc_id']})")
            
            if foods:
                # Test nutrition details
                fdc_id = foods[0]["fdc_id"]
                print(f"\n🔬 Getting nutrition for FDC ID {fdc_id}...")
                
                nutrition_result = await nutrition_api.get_nutrition(fdc_id)
                if nutrition_result.get("success"):
                    macros = nutrition_result["data"]["nutrition"]["macronutrients"]
                    protein = macros.get("Protein", {}).get("amount", "N/A")
                    calories = macros.get("Energy (kcal)", {}).get("amount", "N/A")
                    
                    print(f"✅ Nutrition data:")
                    print(f"   • Protein: {protein}g per 100g")
                    print(f"   • Calories: {calories}kcal per 100g")
                else:
                    print("❌ Failed to get nutrition data")
        else:
            print("❌ Food search failed")
            
    except Exception as e:
        print(f"❌ API test failed: {e}")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run OpenAI function calling tests"""
    
    # Test 1: Direct API test (always works)
    await test_api_directly()
    
    # Test 2: OpenAI integration (requires API key)
    await test_openai_integration()


if __name__ == "__main__":
    asyncio.run(main())