#!/usr/bin/env python3
"""
Live MCP Demo - Works with Deployed Server
==========================================

Real demo that connects to your deployed nutrition MCP server.
Works with Docker, Cloud Run, or any HTTP deployment.

Usage:
    export NUTRITION_API_URL="https://your-service-url.run.app"
    python examples/live_demo.py

    # Or pass URL directly:
    python examples/live_demo.py --url https://your-service-url.run.app
"""

import asyncio
import argparse
import httpx
import json
import os
from typing import Dict, Any, List


class NutritionMCPDemo:
    """Live demo client for deployed MCP nutrition server"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        print(f"🔗 Connected to: {self.base_url}")
    
    async def test_connection(self) -> bool:
        """Test if server is accessible"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def search_foods(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search for foods"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/tools/search_foods",
                json={"query": query, "page_size": limit}
            )
            return response.json()
    
    async def get_nutrition(self, fdc_id: int) -> Dict[str, Any]:
        """Get detailed nutrition"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/tools/get_food_nutrition",
                json={"fdc_id": fdc_id}
            )
            return response.json()
    
    async def compare_foods(self, fdc_ids: List[int]) -> Dict[str, Any]:
        """Compare multiple foods"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/tools/compare_foods",
                json={"fdc_ids": fdc_ids}
            )
            return response.json()
    
    async def demo_protein_search(self):
        """Demo: Find high-protein foods like Claude would"""
        print("\n🔍 Demo 1: High-Protein Food Search")
        print("=" * 50)
        print("Simulating Claude query: 'What are good high-protein foods for athletes?'")
        
        # Step 1: Search for protein sources
        search_result = await self.search_foods("chicken breast salmon greek yogurt", limit=3)
        
        if not search_result.get("success"):
            print("❌ Search failed")
            return
        
        foods = search_result["data"]["foods"]
        print(f"\n✅ Found {len(foods)} protein sources:")
        
        fdc_ids = []
        for food in foods:
            fdc_id = food.get("fdc_id")
            if fdc_id:
                fdc_ids.append(fdc_id)
                print(f"   • {food.get('description')} (ID: {fdc_id})")
        
        # Step 2: Get detailed nutrition for first food
        if fdc_ids:
            print(f"\n🔬 Getting nutrition details for {foods[0]['description']}...")
            nutrition = await self.get_nutrition(fdc_ids[0])
            
            if nutrition.get("success"):
                macros = nutrition["data"]["nutrition"]["macronutrients"]
                protein = macros.get("Protein", {}).get("amount", "N/A")
                calories = macros.get("Energy (kcal)", {}).get("amount", "N/A")
                
                print(f"   Protein: {protein}g per 100g")
                print(f"   Calories: {calories}kcal per 100g")
                
                if isinstance(protein, (int, float)) and protein > 25:
                    print("   ✅ Excellent protein source!")
        
        # Step 3: Compare top foods
        if len(fdc_ids) >= 2:
            print(f"\n⚖️ Comparing top protein sources...")
            comparison = await self.compare_foods(fdc_ids[:2])
            
            if comparison.get("success"):
                nutrients = comparison["data"]["nutrient_comparison"]
                if "Protein" in nutrients:
                    print("   Protein comparison:")
                    for item in nutrients["Protein"]:
                        print(f"   • {item['food']}: {item['amount']}g")
    
    async def demo_weight_loss_foods(self):
        """Demo: Find weight loss foods like Claude would"""
        print("\n🥗 Demo 2: Weight Loss Food Finder")
        print("=" * 50)
        print("Simulating Claude query: 'What are low-calorie, high-fiber foods for weight loss?'")
        
        # Search for low-calorie, high-fiber foods
        search_result = await self.search_foods("broccoli spinach apple berries", limit=4)
        
        if not search_result.get("success"):
            print("❌ Search failed")
            return
        
        foods = search_result["data"]["foods"][:3]  # Top 3
        print(f"\n✅ Analyzing {len(foods)} weight-loss foods:")
        
        food_analyses = []
        for food in foods:
            fdc_id = food.get("fdc_id")
            if not fdc_id:
                continue
                
            nutrition = await self.get_nutrition(fdc_id)
            if nutrition.get("success"):
                macros = nutrition["data"]["nutrition"]["macronutrients"]
                calories = macros.get("Energy (kcal)", {}).get("amount", 0)
                fiber = macros.get("Fiber", {}).get("amount", 0)
                
                food_analyses.append({
                    "name": food["description"],
                    "calories": calories,
                    "fiber": fiber,
                    "fiber_per_calorie": fiber / calories if calories > 0 else 0
                })
        
        # Sort by fiber efficiency
        food_analyses.sort(key=lambda x: x["fiber_per_calorie"], reverse=True)
        
        print("\n📊 Weight Loss Food Rankings:")
        for i, food in enumerate(food_analyses, 1):
            print(f"{i}. {food['name']}")
            print(f"   Calories: {food['calories']}kcal | Fiber: {food['fiber']}g")
            print(f"   Efficiency: {food['fiber_per_calorie']:.3f}g fiber per calorie")
        
        print("\n💡 Claude's Recommendations:")
        print("• High fiber foods help you feel full with fewer calories")
        print("• Aim for >3g fiber per 100 calories for optimal weight loss")
        print("• These foods are perfect for sustainable, healthy weight management")
    
    async def demo_vegetarian_iron(self):
        """Demo: Find iron-rich vegetarian foods"""
        print("\n🌱 Demo 3: Vegetarian Iron Sources")
        print("=" * 50)
        print("Simulating Claude query: 'I'm vegetarian and need more iron. What should I eat?'")
        
        # Search for iron-rich plant foods
        search_result = await self.search_foods("spinach lentils tofu quinoa", limit=4)
        
        if not search_result.get("success"):
            print("❌ Search failed")
            return
        
        foods = search_result["data"]["foods"][:3]
        print(f"\n✅ Found {len(foods)} iron-rich vegetarian foods:")
        
        iron_sources = []
        for food in foods:
            fdc_id = food.get("fdc_id")
            if not fdc_id:
                continue
                
            nutrition = await self.get_nutrition(fdc_id)
            if nutrition.get("success"):
                minerals = nutrition["data"]["nutrition"].get("minerals", {})
                iron = minerals.get("Iron", {}).get("amount", 0)
                
                if iron > 0:
                    iron_sources.append({
                        "name": food["description"],
                        "iron_mg": iron,
                        "fdc_id": fdc_id
                    })
        
        # Sort by iron content
        iron_sources.sort(key=lambda x: x["iron_mg"], reverse=True)
        
        print("\n🔸 Iron Content Analysis:")
        for food in iron_sources:
            print(f"   • {food['name']}: {food['iron_mg']}mg iron per 100g")
        
        print("\n💡 Claude's Iron Absorption Tips:")
        print("• Combine with vitamin C foods (citrus, bell peppers) to enhance absorption")
        print("• Avoid tea/coffee with iron-rich meals (reduces absorption)")
        print("• Cook in cast iron pans to increase iron content")
        print("• Daily iron needs: 8mg (men), 18mg (women)")
    
    async def demo_meal_planning(self):
        """Demo: Balanced meal planning"""
        print("\n🍽️ Demo 4: Balanced Meal Planning")
        print("=" * 50)
        print("Simulating Claude query: 'Help me plan a balanced breakfast with good macros'")
        
        # Search for breakfast components
        components = {
            "protein": "greek yogurt",
            "complex_carbs": "oatmeal",
            "healthy_fats": "almonds",
            "vitamins": "blueberries"
        }
        
        meal_fdc_ids = []
        meal_components = []
        
        for component_type, food_query in components.items():
            search_result = await self.search_foods(food_query, limit=1)
            
            if search_result.get("success") and search_result["data"]["foods"]:
                food = search_result["data"]["foods"][0]
                fdc_id = food.get("fdc_id")
                if fdc_id:
                    meal_fdc_ids.append(fdc_id)
                    meal_components.append({
                        "type": component_type,
                        "name": food["description"],
                        "fdc_id": fdc_id
                    })
        
        print(f"\n✅ Balanced breakfast components:")
        for comp in meal_components:
            print(f"   • {comp['type'].replace('_', ' ').title()}: {comp['name']}")
        
        # Compare all components
        if len(meal_fdc_ids) >= 2:
            print(f"\n📊 Nutritional comparison of breakfast components...")
            comparison = await self.compare_foods(meal_fdc_ids)
            
            if comparison.get("success"):
                nutrients = comparison["data"]["nutrient_comparison"]
                
                # Show key nutrients
                key_nutrients = ["Energy (kcal)", "Protein", "Total Fat", "Carbohydrate"]
                for nutrient in key_nutrients:
                    if nutrient in nutrients:
                        print(f"\n   {nutrient}:")
                        for item in nutrients[nutrient]:
                            print(f"     • {item['food']}: {item['amount']}{item['unit']}")
        
        print("\n💡 Claude's Meal Planning Tips:")
        print("• This combination provides complete amino acids, healthy fats, and complex carbs")
        print("• Aim for 20-30g protein, 30-40g carbs, 10-15g healthy fats per breakfast")
        print("• Add portion sizes: 150g yogurt, 40g oats, 20g almonds, 80g berries")


async def main():
    """Run the live MCP demo"""
    parser = argparse.ArgumentParser(description="Live MCP Nutrition Demo")
    parser.add_argument(
        "--url", 
        default=os.getenv("NUTRITION_API_URL", "https://your-service-url.run.app"),
        help="Nutrition API base URL (or set NUTRITION_API_URL env var)"
    )
    args = parser.parse_args()
    
    print("🥗 Live MCP Nutrition Demo - Real Server Connection")
    print("=" * 60)
    
    # Initialize demo client
    demo = NutritionMCPDemo(args.url)
    
    # Test connection
    print("🔗 Testing server connection...")
    if not await demo.test_connection():
        print("❌ Cannot connect to nutrition server!")
        print(f"   URL: {args.url}")
        print("   Make sure your server is deployed and accessible")
        print("\n💡 Usage:")
        print("   export NUTRITION_API_URL='https://your-actual-url.run.app'")
        print("   python examples/live_demo.py")
        return
    
    print("✅ Server connection successful!")
    
    # Run all demos
    try:
        await demo.demo_protein_search()
        await demo.demo_weight_loss_foods()
        await demo.demo_vegetarian_iron()
        await demo.demo_meal_planning()
        
        print("\n" + "=" * 60)
        print("🎉 Demo Complete!")
        print("\nThis is exactly how Claude Desktop uses your MCP server:")
        print("1. User asks nutrition questions in natural language")
        print("2. Claude automatically calls the appropriate MCP tools")
        print("3. Claude synthesizes the data into helpful recommendations")
        print("\n📋 To use with Claude Desktop, add this to your claude_desktop_config.json:")
        print(f'   "MCP_HTTP_URL": "{args.url}"')
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("Please check your server is running and accessible")


if __name__ == "__main__":
    asyncio.run(main())