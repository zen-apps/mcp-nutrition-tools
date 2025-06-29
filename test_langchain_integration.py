#!/usr/bin/env python3
"""
LangChain + OpenAI Integration Test
==================================

This script shows how to use your MCP nutrition server with LangChain and OpenAI.
Run this on your LangChain Docker machine to test the integration.

Requirements:
    pip install langchain langchain-openai httpx

Usage:
    export OPENAI_API_KEY="your_openai_key"
    export NUTRITION_API_URL="https://your-nutrition-server.run.app"
    python test_langchain_integration.py
"""

import asyncio
import httpx
import os
from typing import Dict, Any, List
from langchain.tools import tool
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate


# =============================================================================
# NUTRITION TOOLS FOR LANGCHAIN
# =============================================================================

# Get your nutrition server URL
NUTRITION_API_URL = os.getenv("NUTRITION_API_URL", "https://your-service-url.run.app")

@tool
async def search_nutrition_foods(query: str, limit: int = 5) -> Dict[str, Any]:
    """Search for foods in the USDA nutrition database by keywords"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{NUTRITION_API_URL}/tools/search_foods",
            json={"query": query, "page_size": limit}
        )
        return response.json()

@tool 
async def get_food_nutrition(fdc_id: int) -> Dict[str, Any]:
    """Get detailed nutrition information for a specific food by FDC ID"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{NUTRITION_API_URL}/tools/get_food_nutrition",
            json={"fdc_id": fdc_id}
        )
        return response.json()

@tool
async def compare_nutrition_foods(fdc_ids: List[int]) -> Dict[str, Any]:
    """Compare nutritional information between multiple foods"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{NUTRITION_API_URL}/tools/compare_foods", 
            json={"fdc_ids": fdc_ids}
        )
        return response.json()

@tool
async def get_nutrition_guidance(question: str, context: str = "") -> Dict[str, Any]:
    """Get guidance and suggestions for nutrition-related questions"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{NUTRITION_API_URL}/tools/nutrition_question_helper",
            json={"question": question, "context": context}
        )
        return response.json()


# =============================================================================
# LANGCHAIN AGENT SETUP
# =============================================================================

def create_nutrition_agent():
    """Create a LangChain agent with nutrition tools"""
    
    # OpenAI LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",  # Use gpt-4 if you have access
        temperature=0.1
    )
    
    # Available tools
    tools = [
        search_nutrition_foods,
        get_food_nutrition, 
        compare_nutrition_foods,
        get_nutrition_guidance
    ]
    
    # Agent prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a nutrition expert with access to the USDA nutrition database.
        
        You can:
        - Search for foods by keywords
        - Get detailed nutrition information 
        - Compare foods side-by-side
        - Provide nutrition guidance
        
        Always provide practical, evidence-based nutrition advice.
        When comparing foods, highlight key differences.
        Include portion recommendations when relevant."""),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}")
    ])
    
    # Create agent
    agent = create_openai_tools_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


# =============================================================================
# TEST SCENARIOS  
# =============================================================================

async def test_basic_connectivity():
    """Test if nutrition server is accessible"""
    print("🔗 Testing nutrition server connectivity...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{NUTRITION_API_URL}/health")
            if response.status_code == 200:
                print("✅ Nutrition server is accessible!")
                return True
            else:
                print(f"❌ Server returned status {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Cannot connect to nutrition server: {e}")
        print(f"   URL: {NUTRITION_API_URL}")
        return False

async def test_tools_directly():
    """Test nutrition tools directly (without LLM)"""
    print("\n🧪 Testing nutrition tools directly...")
    
    try:
        # Test search
        print("  🔍 Testing search_nutrition_foods...")
        search_result = await search_nutrition_foods("chicken breast", 3)
        if search_result.get("success"):
            foods = search_result["data"]["foods"]
            print(f"     ✅ Found {len(foods)} foods")
            
            if foods:
                # Test nutrition details
                fdc_id = foods[0]["fdc_id"]
                print(f"  🔬 Testing get_food_nutrition for FDC ID {fdc_id}...")
                nutrition_result = await get_food_nutrition(fdc_id)
                if nutrition_result.get("success"):
                    protein = nutrition_result["data"]["nutrition"]["macronutrients"].get("Protein", {}).get("amount", "N/A")
                    print(f"     ✅ Protein content: {protein}g per 100g")
                else:
                    print("     ❌ Nutrition lookup failed")
            
        else:
            print("     ❌ Search failed")
            
    except Exception as e:
        print(f"❌ Tool testing failed: {e}")

def test_langchain_agent():
    """Test LangChain agent with nutrition tools"""
    print("\n🤖 Testing LangChain Agent...")
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set. Skipping LangChain test.")
        return
    
    try:
        agent = create_nutrition_agent()
        
        # Test queries
        test_queries = [
            "What are the best high-protein foods for muscle building?",
            "Compare the nutrition of chicken breast vs salmon",
            "I'm vegetarian and need more iron. What foods should I eat?"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Query: {query}")
            try:
                result = agent.invoke({"input": query})
                print(f"🤖 Response: {result['output'][:200]}...")
            except Exception as e:
                print(f"❌ Query failed: {e}")
                
    except Exception as e:
        print(f"❌ LangChain agent test failed: {e}")


# =============================================================================
# SIMPLE HTTP TEST (No LangChain required)
# =============================================================================

async def test_simple_http():
    """Simple HTTP test - no LangChain required"""
    print("\n📡 Simple HTTP API Test...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test search
            print("  🔍 Searching for 'apple'...")
            response = await client.post(
                f"{NUTRITION_API_URL}/tools/search_foods",
                json={"query": "apple", "page_size": 2}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    foods = data["data"]["foods"]
                    print(f"     ✅ Found {len(foods)} apple varieties")
                    
                    if foods:
                        fdc_id = foods[0]["fdc_id"]
                        print(f"  🔬 Getting nutrition for {foods[0]['description']}...")
                        
                        # Get nutrition
                        nutrition_response = await client.post(
                            f"{NUTRITION_API_URL}/tools/get_food_nutrition",
                            json={"fdc_id": fdc_id}
                        )
                        
                        if nutrition_response.status_code == 200:
                            nutrition_data = nutrition_response.json()
                            if nutrition_data.get("success"):
                                macros = nutrition_data["data"]["nutrition"]["macronutrients"]
                                calories = macros.get("Energy (kcal)", {}).get("amount", "N/A")
                                fiber = macros.get("Fiber", {}).get("amount", "N/A")
                                print(f"     ✅ Calories: {calories}kcal, Fiber: {fiber}g per 100g")
                            else:
                                print("     ❌ Nutrition data failed")
                        else:
                            print("     ❌ Nutrition request failed")
                else:
                    print("     ❌ Search was not successful")
            else:
                print(f"     ❌ HTTP error {response.status_code}")
                
    except Exception as e:
        print(f"❌ HTTP test failed: {e}")


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

async def main():
    """Run all tests"""
    print("🥗 MCP Nutrition Server Integration Tests")
    print("=" * 50)
    print(f"🔗 Nutrition API URL: {NUTRITION_API_URL}")
    print(f"🔑 OpenAI API Key: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Not set'}")
    print()
    
    # Test 1: Basic connectivity
    if not await test_basic_connectivity():
        print("\n❌ Cannot proceed - nutrition server not accessible")
        print("\n💡 Troubleshooting:")
        print("   1. Check if your nutrition server is running")
        print("   2. Verify NUTRITION_API_URL is correct")
        print("   3. Check network connectivity between Docker containers")
        return
    
    # Test 2: Direct tool testing
    await test_tools_directly()
    
    # Test 3: Simple HTTP (works without LangChain)
    await test_simple_http()
    
    # Test 4: LangChain agent (requires OpenAI key)
    test_langchain_agent()
    
    print("\n" + "=" * 50)
    print("🎉 Integration testing complete!")
    print("\n💡 Next steps:")
    print("   1. If tests pass, your MCP server works with LLMs!")
    print("   2. Use the LangChain tools in your own applications")
    print("   3. Try the interactive demos at /docs on your server")
    print("   4. For Claude Desktop, use the MCP protocol directly")


if __name__ == "__main__":
    asyncio.run(main())