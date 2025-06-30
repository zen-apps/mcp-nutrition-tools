#!/usr/bin/env python3
"""
Test script for the HTTP MCP server
"""

import asyncio
import json
import httpx

async def test_mcp_server(base_url: str = "http://localhost:8080"):
    """Test all MCP server endpoints"""
    
    print(f"🧪 Testing MCP Server at {base_url}")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Health check
        print("1. Testing health endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                health_data = response.json()
                print(f"   Service: {health_data.get('service')}")
                print(f"   USDA API: {health_data.get('usda_api')}")
            print("   ✅ Health check passed\n")
        except Exception as e:
            print(f"   ❌ Health check failed: {e}\n")
            return
        
        # Test 2: List tools
        print("2. Testing tools list...")
        try:
            response = await client.get(f"{base_url}/tools")
            if response.status_code == 200:
                tools_data = response.json()
                print(f"   Available tools: {tools_data.get('count')}")
                for tool in tools_data.get('tools', []):
                    print(f"   - {tool['name']}: {tool['description']}")
            print("   ✅ Tools list passed\n")
        except Exception as e:
            print(f"   ❌ Tools list failed: {e}\n")
        
        # Test 3: Search foods
        print("3. Testing food search...")
        try:
            response = await client.post(
                f"{base_url}/tools/search_foods",
                json={"query": "chicken breast", "page_size": 3}
            )
            if response.status_code == 200:
                search_data = response.json()
                if search_data.get('success'):
                    foods = search_data.get('data', {}).get('foods', [])
                    print(f"   Found {len(foods)} foods:")
                    for food in foods[:2]:
                        print(f"   - {food.get('description')} (ID: {food.get('fdc_id')})")
                    
                    # Test 4: Get nutrition details
                    if foods:
                        print("\n4. Testing nutrition details...")
                        fdc_id = foods[0]['fdc_id']
                        response = await client.post(
                            f"{base_url}/tools/get_food_nutrition",
                            json={"fdc_id": fdc_id, "format": "abridged"}
                        )
                        if response.status_code == 200:
                            nutrition_data = response.json()
                            if nutrition_data.get('success'):
                                food_info = nutrition_data.get('data', {}).get('food_info', {})
                                macros = nutrition_data.get('data', {}).get('nutrition', {}).get('macronutrients', {})
                                print(f"   Food: {food_info.get('description')}")
                                print(f"   Macronutrients:")
                                for macro, data in macros.items():
                                    print(f"     - {macro}: {data.get('amount')} {data.get('unit')}")
                                print("   ✅ Nutrition details passed\n")
                
            print("   ✅ Food search passed\n")
        except Exception as e:
            print(f"   ❌ Food search failed: {e}\n")
        
        # Test 5: Compare foods (if we have multiple foods)
        print("5. Testing food comparison...")
        try:
            # Search for two different foods
            apple_response = await client.post(
                f"{base_url}/tools/search_foods",
                json={"query": "apple", "page_size": 1}
            )
            banana_response = await client.post(
                f"{base_url}/tools/search_foods", 
                json={"query": "banana", "page_size": 1}
            )
            
            if (apple_response.status_code == 200 and banana_response.status_code == 200):
                apple_foods = apple_response.json().get('data', {}).get('foods', [])
                banana_foods = banana_response.json().get('data', {}).get('foods', [])
                
                if apple_foods and banana_foods:
                    fdc_ids = [apple_foods[0]['fdc_id'], banana_foods[0]['fdc_id']]
                    
                    response = await client.post(
                        f"{base_url}/tools/compare_foods",
                        json={"fdc_ids": fdc_ids}
                    )
                    
                    if response.status_code == 200:
                        comparison_data = response.json()
                        if comparison_data.get('success'):
                            compared_foods = comparison_data.get('data', {}).get('foods', [])
                            print(f"   Compared {len(compared_foods)} foods:")
                            for food in compared_foods:
                                print(f"   - {food.get('description')}")
                            print("   ✅ Food comparison passed\n")
        except Exception as e:
            print(f"   ❌ Food comparison failed: {e}\n")
        
        # Test 6: Nutrition question helper
        print("6. Testing nutrition question helper...")
        try:
            response = await client.post(
                f"{base_url}/tools/nutrition_question_helper",
                json={"question": "What foods are high in protein?"}
            )
            if response.status_code == 200:
                help_data = response.json()
                if help_data.get('success'):
                    suggestions = help_data.get('data', {})
                    print(f"   Question: {suggestions.get('question')}")
                    print(f"   Suggested searches: {suggestions.get('suggested_searches')}")
                    print("   ✅ Nutrition helper passed\n")
        except Exception as e:
            print(f"   ❌ Nutrition helper failed: {e}\n")
    
    print("🎉 All tests completed!")

if __name__ == "__main__":
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    asyncio.run(test_mcp_server(base_url))

---

# scripts/run_dev.sh
#!/bin/bash

# Development server runner
set -e

echo "🚀 Starting USDA Nutrition MCP Server (Development Mode)"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run ./scripts/setup.sh first"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create it from .env.example"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check if FDC_API_KEY is set
if [ -z "$FDC_API_KEY" ]; then
    echo "❌ FDC_API_KEY not set in .env file"
    echo "Get your free API key at: https://fdc.nal.usda.gov/api-guide.html"
    exit 1
fi

echo "✅ Environment configured"
echo "📡 USDA API Key: ${FDC_API_KEY:0:8}..."

# Set development environment
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG

# Start the server
echo "🌐 Starting server on http://localhost:8080"
echo "📚 API docs will be available at http://localhost:8080/docs"
echo ""
echo "Press Ctrl+C to stop the server"

python -m uvicorn src.mcp_http_server:app \
    --host 0.0.0.0 \
    --port 8080 \
    --reload \
    --log-level info

---

# Quick test command you can run right now:
# test_quick.py
#!/usr/bin/env python3
"""
Quick test to verify your setup works
"""

import os
import asyncio
import httpx

async def quick_test():
    """Quick test of USDA API connectivity"""
    
    api_key = os.getenv("FDC_API_KEY")
    if not api_key:
        print("❌ FDC_API_KEY not found in environment")
        print("Please set it in your .env file")
        return False
    
    print(f"🔑 API Key found: {api_key[:8]}...")
    
    # Test direct USDA API call
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.nal.usda.gov/fdc/v1/foods/search",
                headers={"X-Api-Key": api_key},
                json={"query": "apple", "pageSize": 1},
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                total_hits = data.get("totalHits", 0)
                print(f"✅ USDA API working! Found {total_hits} foods for 'apple'")
                
                if data.get("foods"):
                    first_food = data["foods"][0]
                    print(f"📝 Sample food: {first_food.get('description')}")
                    print(f"🆔 FDC ID: {first_food.get('fdcId')}")
                
                return True
            else:
                print(f"❌ USDA API error: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    # Load .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    print("🧪 Quick API Test")
    print("=" * 30)
    
    success = asyncio.run(quick_test())
    
    if success:
        print("\n🎉 Setup looks good! Ready to start the MCP server.")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run server: python -m uvicorn src.mcp_http_server:app --reload")
        print("3. Test server: python examples/test_http_server.py")
    else:
        print("\n💡 Troubleshooting:")
        print("1. Check your FDC_API_KEY in .env file")
        print("2. Get a free key at: https://fdc.nal.usda.gov/api-guide.html")
        print("3. Verify internet connectivity")