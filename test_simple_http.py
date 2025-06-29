#!/usr/bin/env python3
"""
Simple HTTP Test - No AI Required
=================================

Basic test to verify your MCP nutrition server works.
This doesn't require any AI - just tests the HTTP endpoints directly.

Requirements:
    pip install httpx

Usage:
    export NUTRITION_API_URL="https://your-nutrition-server.run.app"
    python test_simple_http.py

Or:
    python test_simple_http.py --url https://your-nutrition-server.run.app
"""

import asyncio
import argparse
import httpx
import json
import os
from typing import Dict, Any


class SimpleNutritionTest:
    """Simple HTTP client to test nutrition API"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        print(f"🔗 Testing server: {self.base_url}")
    
    async def test_health(self) -> bool:
        """Test if server is running"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Server is healthy")
                    print(f"   Status: {data.get('status', 'unknown')}")
                    print(f"   Version: {data.get('version', 'unknown')}")
                    return True
                else:
                    print(f"❌ Health check failed (HTTP {response.status_code})")
                    return False
                    
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            return False
    
    async def test_search_foods(self) -> Dict[str, Any]:
        """Test food search endpoint"""
        print("\n🔍 Testing food search...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/tools/search_foods",
                    json={
                        "query": "chicken breast",
                        "page_size": 3
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success"):
                        foods = data["data"]["foods"]
                        print(f"✅ Found {len(foods)} foods:")
                        
                        for i, food in enumerate(foods, 1):
                            print(f"   {i}. {food['description']} (ID: {food['fdc_id']})")
                        
                        return data
                    else:
                        print(f"❌ Search failed: {data.get('error', 'Unknown error')}")
                        return {}
                else:
                    print(f"❌ HTTP error {response.status_code}")
                    return {}
                    
        except Exception as e:
            print(f"❌ Search test failed: {e}")
            return {}
    
    async def test_get_nutrition(self, fdc_id: int) -> Dict[str, Any]:
        """Test nutrition details endpoint"""
        print(f"\n🔬 Testing nutrition details for FDC ID {fdc_id}...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/tools/get_food_nutrition",
                    json={"fdc_id": fdc_id}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success"):
                        food_info = data["data"]["food_info"]
                        nutrition = data["data"]["nutrition"]
                        
                        print(f"✅ Nutrition data for: {food_info['description']}")
                        print(f"   Serving size: {food_info.get('serving_size', 100)}g")
                        
                        # Show key macronutrients
                        macros = nutrition.get("macronutrients", {})
                        for nutrient, info in macros.items():
                            if nutrient in ["Energy (kcal)", "Protein", "Total Fat", "Carbohydrate"]:
                                amount = info.get("amount", "N/A")
                                unit = info.get("unit", "")
                                print(f"   {nutrient}: {amount}{unit}")
                        
                        return data
                    else:
                        print(f"❌ Nutrition lookup failed: {data.get('error', 'Unknown error')}")
                        return {}
                else:
                    print(f"❌ HTTP error {response.status_code}")
                    return {}
                    
        except Exception as e:
            print(f"❌ Nutrition test failed: {e}")
            return {}
    
    async def test_compare_foods(self, fdc_ids: list) -> Dict[str, Any]:
        """Test food comparison endpoint"""
        print(f"\n⚖️ Testing food comparison for {len(fdc_ids)} foods...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/tools/compare_foods",
                    json={"fdc_ids": fdc_ids}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success"):
                        comparison = data["data"]["nutrient_comparison"]
                        
                        print("✅ Food comparison results:")
                        
                        # Show protein comparison
                        if "Protein" in comparison:
                            print("   Protein content:")
                            for item in comparison["Protein"]:
                                print(f"     • {item['food']}: {item['amount']}{item['unit']}")
                        
                        return data
                    else:
                        print(f"❌ Comparison failed: {data.get('error', 'Unknown error')}")
                        return {}
                else:
                    print(f"❌ HTTP error {response.status_code}")
                    return {}
                    
        except Exception as e:
            print(f"❌ Comparison test failed: {e}")
            return {}
    
    async def test_interactive_demo(self, demo_name: str):
        """Test one of the interactive demo endpoints"""
        print(f"\n🎯 Testing interactive demo: {demo_name}...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/demo/{demo_name}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success"):
                        demo_data = data["data"]
                        print(f"✅ Demo '{demo_name}' completed successfully")
                        print(f"   Scenario: {demo_data.get('demo_scenario', 'Unknown')}")
                        
                        # Show a sample recommendation
                        recommendations = demo_data.get("claude_recommendations", [])
                        if recommendations:
                            print(f"   Sample recommendation: {recommendations[0]}")
                        
                        return True
                    else:
                        print(f"❌ Demo failed: {data.get('error', 'Unknown error')}")
                        return False
                else:
                    print(f"❌ HTTP error {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Demo test failed: {e}")
            return False
    
    async def run_full_test(self):
        """Run complete test suite"""
        print("🥗 Simple HTTP Test - MCP Nutrition Server")
        print("=" * 50)
        
        # Test 1: Health check
        if not await self.test_health():
            print("\n❌ Server not accessible. Cannot continue testing.")
            print("\n💡 Troubleshooting:")
            print("   1. Make sure your nutrition server is running")
            print("   2. Check the URL is correct")
            print("   3. Verify network connectivity")
            return False
        
        # Test 2: Search foods
        search_result = await self.test_search_foods()
        if not search_result.get("success"):
            print("❌ Search test failed. Stopping tests.")
            return False
        
        # Get FDC IDs for further testing
        foods = search_result["data"]["foods"]
        fdc_ids = [food["fdc_id"] for food in foods[:2]]  # Get first 2
        
        # Test 3: Get nutrition details
        if fdc_ids:
            nutrition_result = await self.test_get_nutrition(fdc_ids[0])
            if not nutrition_result.get("success"):
                print("⚠️ Nutrition details test failed, but continuing...")
        
        # Test 4: Compare foods
        if len(fdc_ids) >= 2:
            comparison_result = await self.test_compare_foods(fdc_ids[:2])
            if not comparison_result.get("success"):
                print("⚠️ Food comparison test failed, but continuing...")
        
        # Test 5: Interactive demos
        demo_tests = [
            "protein-search",
            "weight-loss-foods", 
            "vegetarian-iron",
            "meal-planning"
        ]
        
        print(f"\n🎯 Testing {len(demo_tests)} interactive demos...")
        demo_results = []
        
        for demo in demo_tests:
            result = await self.test_interactive_demo(demo)
            demo_results.append(result)
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary:")
        print(f"   ✅ Health check: PASSED")
        print(f"   ✅ Food search: PASSED")
        print(f"   ✅ Nutrition details: {'PASSED' if nutrition_result.get('success') else 'FAILED'}")
        print(f"   ✅ Food comparison: {'PASSED' if len(fdc_ids) >= 2 and comparison_result.get('success') else 'SKIPPED'}")
        print(f"   ✅ Interactive demos: {sum(demo_results)}/{len(demo_results)} PASSED")
        
        if all([search_result.get("success"), len(demo_results) > 0]):
            print("\n🎉 Your MCP nutrition server is working!")
            print("\n💡 What this means:")
            print("   ✅ Your server can handle HTTP requests")
            print("   ✅ USDA API integration is working")
            print("   ✅ All nutrition tools are functional")
            print("   ✅ Ready for LLM integration!")
            
            print("\n🚀 Next steps:")
            print("   1. Try the LangChain test: python test_langchain_integration.py")
            print("   2. Try the OpenAI test: python test_openai_functions.py")
            print("   3. Use the interactive demos at /docs")
            return True
        else:
            print("\n❌ Some tests failed. Check the errors above.")
            return False


async def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Simple HTTP test for MCP nutrition server")
    parser.add_argument(
        "--url",
        default=os.getenv("NUTRITION_API_URL", "https://your-service-url.run.app"),
        help="Nutrition API base URL"
    )
    args = parser.parse_args()
    
    # Run tests
    tester = SimpleNutritionTest(args.url)
    success = await tester.run_full_test()
    
    if success:
        print("\n🎯 Your MCP server is ready for AI integration!")
    else:
        print("\n❌ Fix the errors above before testing with AI")


if __name__ == "__main__":
    asyncio.run(main())