# 🥗 USDA Nutrition MCP Server

> **Model Context Protocol (MCP) server providing nutrition tools powered by USDA FoodData Central**  
> Connect AI assistants to 600k+ foods with comprehensive nutrition data

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io/)

## 🌟 Overview

This MCP server transforms the USDA FoodData Central database (600k+ foods) into intelligent, accessible nutrition tools for AI assistants like Claude. Built with FastMCP, it provides standardized MCP protocol tools for nutrition analysis.

**Perfect for:**
- 🤖 **AI Assistants** - Claude Desktop, custom MCP clients
- 📱 **Nutrition Apps** - Diet tracking, meal planning, health coaching
- 🔬 **Research** - Nutritional analysis, food comparison studies
- 💻 **Developer Tools** - Any application needing nutrition data

## 🔌 MCP Configuration

## Quick Setup for Claude Desktop

1. **Clone and install:**
   ```bash
   git clone https://github.com/your-username/mcp-nutrition-tools
   cd mcp-nutrition-tools
   pip install mcp httpx
```

#### **Option 2: HTTP Connection to Deployed Server**
For Docker or Cloud Run deployments, use HTTP connection:

```json
{
  "mcpServers": {
    "usda-nutrition": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-everything"],
      "env": {
        "MCP_HTTP_URL": "https://your-service-url.run.app"
      }
    }
  }
}
```

#### **Option 3: Using MCP HTTP Bridge**
```json
{
  "mcpServers": {
    "usda-nutrition": {
      "command": "python",
      "args": ["-m", "mcp_http_bridge", "https://your-service-url.run.app"],
      "env": {}
    }
  }
}
```

### **Alternative: NPM Installation** 
```bash
# Install globally (coming soon)
npm install -g usda-nutrition-mcp-server

# Then configure Claude Desktop with:
{
  "mcpServers": {
    "usda-nutrition": {
      "command": "usda-nutrition-mcp-server",
      "env": {
        "FDC_API_KEY": "your_usda_api_key_here"
      }
    }
  }
}
```

### **Available MCP Tools**

Once configured, Claude will have access to these nutrition tools:

- **`search_foods`** - Search USDA database for foods
- **`get_food_details`** - Get detailed nutrition information  
- **`get_multiple_foods`** - Get nutrition for multiple foods at once
- **`analyze_nutrition`** - Compare nutritional data across foods

### **Example Usage with Claude**

#### **Real MCP Demo Examples**

**Query:** *"Search for high-protein foods and compare chicken breast with salmon"*

Claude will automatically use the MCP tools:
1. **search_foods** - Find protein-rich foods in USDA database
2. **get_food_details** - Get nutrition data for chicken breast and salmon  
3. **analyze_nutrition** - Compare protein, calories, and other nutrients
4. Provide comprehensive analysis with recommendations

**Query:** *"What are the best foods for someone trying to build muscle?"*

Claude's workflow:
1. **search_foods("high protein lean meat")** → Find muscle-building foods
2. **get_multiple_foods([ids])** → Get nutrition for top results
3. **analyze_nutrition** → Compare protein efficiency, amino acid profiles
4. Recommend optimal foods with portion guidance

**Query:** *"I'm vegetarian and need more iron. What foods should I eat?"*

Claude's response:
1. **search_foods("iron rich vegetarian")** → Find plant-based iron sources
2. **get_food_details** → Analyze iron content and bioavailability factors
3. **nutrition_guidance** → Suggest combinations that enhance iron absorption

## 🚀 Quick Start

### **Installation & Setup**
```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-nutrition-tools
cd mcp-nutrition-tools

# Install dependencies
pip install -r requirements.txt

# Get your free USDA API key from https://fdc.nal.usda.gov/api-guide.html
echo "FDC_API_KEY=your_key_here" > .env

# Test the MCP server
python -m src.mcp_server
```

### **Quick Test**
```bash
# Test MCP tools directly
python -c "
import asyncio
from src.mcp_server import search_foods

async def test():
    result = await search_foods('apple')
    print(result)

asyncio.run(test())
"
```

## 🛠 API Reference

### **Base URL**
- **Production**: `https://your-service-url.run.app`
- **Local**: `http://localhost:8080`

### **Authentication**
No authentication required for API consumption. The server handles USDA API authentication internally.

---

## 📚 Available Tools

### **1. Search Foods**
Search the USDA database for foods by keywords.

**Endpoint:** `POST /tools/search_foods`

**Request:**
```json
{
  "query": "chicken breast",
  "page_size": 10,
  "page_number": 1,
  "data_type": ["Foundation", "Branded"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "foods": [
      {
        "fdc_id": 171077,
        "description": "Chicken, broilers or fryers, breast, meat only, raw",
        "data_type": "Foundation",
        "food_category": "Poultry Products",
        "brand_owner": null
      }
    ],
    "total_results": 156,
    "current_page": 1,
    "message": "Found 10 foods matching 'chicken breast'"
  },
  "tool": "search_foods",
  "timestamp": "2025-06-28T20:30:00Z"
}
```

---

### **2. Get Food Nutrition**
Get detailed nutritional information for a specific food.

**Endpoint:** `POST /tools/get_food_nutrition`

**Request:**
```json
{
  "fdc_id": 171077,
  "format": "abridged"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "food_info": {
      "fdc_id": 171077,
      "description": "Chicken, broilers or fryers, breast, meat only, raw",
      "data_type": "Foundation",
      "serving_size": 100,
      "serving_size_unit": "g"
    },
    "nutrition": {
      "macronutrients": {
        "Energy (kcal)": {"amount": 165, "unit": "kcal"},
        "Protein": {"amount": 31.02, "unit": "g"},
        "Total Fat": {"amount": 3.57, "unit": "g"},
        "Carbohydrate": {"amount": 0, "unit": "g"},
        "Fiber": {"amount": 0, "unit": "g"}
      },
      "vitamins": {
        "Vitamin B-6": {"amount": 0.6, "unit": "mg"},
        "Vitamin B-12": {"amount": 0.34, "unit": "µg"}
      },
      "minerals": {
        "Phosphorus": {"amount": 228, "unit": "mg"},
        "Potassium": {"amount": 256, "unit": "mg"},
        "Sodium": {"amount": 74, "unit": "mg"},
        "Zinc": {"amount": 1.1, "unit": "mg"}
      }
    }
  },
  "tool": "get_food_nutrition",
  "message": "Retrieved nutrition data for Chicken, broilers or fryers, breast, meat only, raw"
}
```

---

### **3. Compare Foods**
Side-by-side nutritional comparison of multiple foods.

**Endpoint:** `POST /tools/compare_foods`

**Request:**
```json
{
  "fdc_ids": [171077, 175167]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "foods": [
      {
        "fdc_id": 171077,
        "description": "Chicken, broilers or fryers, breast, meat only, raw",
        "nutrients": {
          "Energy (kcal)": {"amount": 165, "unit": "kcal"},
          "Protein": {"amount": 31.02, "unit": "g"}
        }
      },
      {
        "fdc_id": 175167,
        "description": "Salmon, Atlantic, farmed, raw",
        "nutrients": {
          "Energy (kcal)": {"amount": 208, "unit": "kcal"},
          "Protein": {"amount": 25.44, "unit": "g"}
        }
      }
    ],
    "nutrient_comparison": {
      "Energy (kcal)": [
        {"food": "Chicken breast", "amount": 165, "unit": "kcal"},
        {"food": "Salmon", "amount": 208, "unit": "kcal"}
      ],
      "Protein": [
        {"food": "Chicken breast", "amount": 31.02, "unit": "g"},
        {"food": "Salmon", "amount": 25.44, "unit": "g"}
      ]
    }
  }
}
```

---

### **4. Nutrition Question Helper**
Get guidance and suggestions for nutrition-related questions.

**Endpoint:** `POST /tools/nutrition_question_helper`

**Request:**
```json
{
  "question": "What foods are high in protein?",
  "context": "Looking for muscle building options"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "question": "What foods are high in protein?",
    "suggested_searches": ["chicken breast", "salmon", "tofu", "greek yogurt", "lentils"],
    "recommended_tools": ["search_foods", "compare_foods"],
    "tips": [
      "Search for specific protein sources",
      "Compare protein content per 100g",
      "Look for foods with >20g protein per 100g for high-protein options"
    ],
    "sample_queries": [
      "search_foods: 'chicken breast'",
      "compare_foods: [multiple protein source FDC IDs]"
    ]
  }
}
```

---

### **5. Get Food Categories**
Information about USDA food categories and data types.

**Endpoint:** `GET /tools/get_food_categories`

**Response:**
```json
{
  "success": true,
  "data": {
    "data_types": {
      "Foundation": {
        "description": "Generic food items with detailed nutrient profiles",
        "example": "Chicken breast, raw",
        "best_for": "Getting nutrition data for basic, unbranded foods"
      },
      "Branded": {
        "description": "Commercial food products with UPC codes",
        "example": "Cheerios Original cereal",
        "best_for": "Specific brand name products and packaged foods"
      }
    },
    "search_tips": [
      "Use simple, descriptive terms for best results",
      "Foundation and SR Legacy are good for basic foods"
    ]
  }
}
```

---

## 💻 Usage Examples

### **Python Integration**

#### **Basic Usage**
```python
import httpx
import asyncio

class USDANutritionAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    async def search_foods(self, query: str, limit: int = 10):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/tools/search_foods",
                json={"query": query, "page_size": limit}
            )
            return response.json()
    
    async def get_nutrition(self, fdc_id: int):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/tools/get_food_nutrition",
                json={"fdc_id": fdc_id}
            )
            return response.json()

# Usage
async def main():
    api = USDANutritionAPI("https://your-service-url.run.app")
    
    # Search for high-protein foods
    search_results = await api.search_foods("chicken breast")
    
    if search_results["success"]:
        foods = search_results["data"]["foods"]
        
        # Get detailed nutrition for first result
        nutrition = await api.get_nutrition(foods[0]["fdc_id"])
        
        if nutrition["success"]:
            macros = nutrition["data"]["nutrition"]["macronutrients"]
            protein = macros.get("Protein", {}).get("amount", "N/A")
            calories = macros.get("Energy (kcal)", {}).get("amount", "N/A")
            
            print(f"Food: {foods[0]['description']}")
            print(f"Protein: {protein}g")
            print(f"Calories: {calories}kcal")

asyncio.run(main())
```

#### **LangGraph Agent Integration**
```python
from langchain_core.tools import tool
import httpx

# Define tools for LangGraph
@tool
async def search_nutrition_foods(query: str) -> dict:
    """Search for foods in the USDA nutrition database"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://your-service-url.run.app/tools/search_foods",
            json={"query": query, "page_size": 5}
        )
        return response.json()

@tool
async def get_food_nutrition_details(fdc_id: int) -> dict:
    """Get detailed nutrition information for a specific food"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://your-service-url.run.app/tools/get_food_nutrition",
            json={"fdc_id": fdc_id}
        )
        return response.json()

@tool
async def compare_nutrition_foods(fdc_ids: list) -> dict:
    """Compare nutritional information between multiple foods"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://your-service-url.run.app/tools/compare_foods",
            json={"fdc_ids": fdc_ids}
        )
        return response.json()

# Add to your LangGraph agent
tools = [search_nutrition_foods, get_food_nutrition_details, compare_nutrition_foods]
```

#### **Nutrition Analysis Workflow**
```python
async def analyze_meal_nutrition(foods: list):
    """Analyze nutrition for a complete meal"""
    api = USDANutritionAPI("https://your-service-url.run.app")
    
    meal_nutrition = {
        "foods": [],
        "totals": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    }
    
    for food_query in foods:
        # Search for each food
        search_result = await api.search_foods(food_query)
        
        if search_result["success"] and search_result["data"]["foods"]:
            food = search_result["data"]["foods"][0]
            
            # Get nutrition details
            nutrition_result = await api.get_nutrition(food["fdc_id"])
            
            if nutrition_result["success"]:
                macros = nutrition_result["data"]["nutrition"]["macronutrients"]
                
                food_data = {
                    "name": food["description"],
                    "calories": macros.get("Energy (kcal)", {}).get("amount", 0),
                    "protein": macros.get("Protein", {}).get("amount", 0),
                    "carbs": macros.get("Carbohydrate", {}).get("amount", 0),
                    "fat": macros.get("Total Fat", {}).get("amount", 0)
                }
                
                meal_nutrition["foods"].append(food_data)
                
                # Add to totals
                meal_nutrition["totals"]["calories"] += food_data["calories"]
                meal_nutrition["totals"]["protein"] += food_data["protein"]
                meal_nutrition["totals"]["carbs"] += food_data["carbs"]
                meal_nutrition["totals"]["fat"] += food_data["fat"]
    
    return meal_nutrition

# Usage
meal = ["chicken breast", "brown rice", "broccoli"]
nutrition_analysis = await analyze_meal_nutrition(meal)
print(f"Meal totals: {nutrition_analysis['totals']}")
```

### **JavaScript/Node.js Integration**
```javascript
class USDANutritionAPI {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }
    
    async searchFoods(query, pageSize = 10) {
        const response = await fetch(`${this.baseUrl}/tools/search_foods`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query, page_size: pageSize})
        });
        return response.json();
    }
    
    async getNutrition(fdcId) {
        const response = await fetch(`${this.baseUrl}/tools/get_food_nutrition`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({fdc_id: fdcId})
        });
        return response.json();
    }
    
    async compareFoods(fdcIds) {
        const response = await fetch(`${this.baseUrl}/tools/compare_foods`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({fdc_ids: fdcIds})
        });
        return response.json();
    }
}

// Usage
const api = new USDANutritionAPI('https://your-service-url.run.app');

async function findHighProteinFoods() {
    const searchResult = await api.searchFoods('protein');
    
    if (searchResult.success) {
        const proteinFoods = [];
        
        for (const food of searchResult.data.foods.slice(0, 3)) {
            const nutrition = await api.getNutrition(food.fdc_id);
            
            if (nutrition.success) {
                const protein = nutrition.data.nutrition.macronutrients.Protein?.amount || 0;
                
                if (protein > 20) {  // High protein threshold
                    proteinFoods.push({
                        name: food.description,
                        protein: protein,
                        fdc_id: food.fdc_id
                    });
                }
            }
        }
        
        return proteinFoods.sort((a, b) => b.protein - a.protein);
    }
}

findHighProteinFoods().then(foods => {
    console.log('High protein foods:', foods);
});
```

### **curl Examples**
```bash
# Find the best protein sources
curl -X POST https://your-service-url.run.app/tools/search_foods \
  -H "Content-Type: application/json" \
  -d '{"query": "lean protein", "page_size": 5}' | jq '.data.foods[] | {fdc_id, description}'

# Compare chicken vs salmon for fitness goals
curl -X POST https://your-service-url.run.app/tools/compare_foods \
  -H "Content-Type: application/json" \
  -d '{"fdc_ids": [171077, 175167]}' | jq '.data.nutrient_comparison'

# Get guidance for weight loss foods
curl -X POST https://your-service-url.run.app/tools/nutrition_question_helper \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the best foods for weight loss?"}' | jq '.data.tips'
```

## 🎯 Common Use Cases

### **1. Fitness & Bodybuilding**
```python
# Find high-protein, low-fat foods for cutting
async def find_cutting_foods():
    foods_to_check = ["chicken breast", "white fish", "egg whites", "lean beef"]
    
    for food_query in foods_to_check:
        search_result = await api.search_foods(food_query)
        if search_result["success"]:
            food = search_result["data"]["foods"][0]
            nutrition = await api.get_nutrition(food["fdc_id"])
            
            if nutrition["success"]:
                macros = nutrition["data"]["nutrition"]["macronutrients"]
                protein = macros.get("Protein", {}).get("amount", 0)
                fat = macros.get("Total Fat", {}).get("amount", 0)
                
                if protein > 20 and fat < 5:  # High protein, low fat
                    print(f"✅ {food['description']}: {protein}g protein, {fat}g fat")
```

### **2. Meal Planning**
```python
# Plan a balanced breakfast
async def plan_balanced_breakfast():
    breakfast_components = {
        "protein": "greek yogurt",
        "carbs": "oatmeal", 
        "healthy_fats": "almonds",
        "vitamins": "blueberries"
    }
    
    fdc_ids = []
    for component, food_query in breakfast_components.items():
        search_result = await api.search_foods(food_query)
        if search_result["success"]:
            fdc_ids.append(search_result["data"]["foods"][0]["fdc_id"])
    
    # Compare all components
    comparison = await api.compare_foods(fdc_ids)
    return comparison["data"]
```

### **3. Dietary Restrictions**
```python
# Find high-iron foods for vegetarians
async def find_vegetarian_iron_sources():
    iron_sources = ["spinach", "lentils", "tofu", "quinoa", "pumpkin seeds"]
    
    iron_foods = []
    for food_query in iron_sources:
        search_result = await api.search_foods(food_query)
        if search_result["success"]:
            food = search_result["data"]["foods"][0]
            nutrition = await api.get_nutrition(food["fdc_id"])
            
            if nutrition["success"]:
                minerals = nutrition["data"]["nutrition"]["minerals"]
                iron = minerals.get("Iron", {}).get("amount", 0)
                
                iron_foods.append({
                    "food": food["description"],
                    "iron_mg": iron,
                    "per_100g": True
                })
    
    return sorted(iron_foods, key=lambda x: x["iron_mg"], reverse=True)
```

## 🔍 Advanced Features

### **Data Types Explained**
- **Foundation**: Generic, unbranded foods with comprehensive nutrient profiles
- **Branded**: Commercial products with UPC codes and brand information  
- **Survey (FNDDS)**: Foods as consumed in dietary surveys
- **SR Legacy**: Historical data from the Standard Reference database

### **Search Tips**
- Use simple, descriptive terms: `"chicken breast"` not `"boneless skinless chicken breast meat"`
- Filter by data type for specific needs: `"data_type": ["Foundation"]` for generic foods
- Try variations: `"salmon"`, `"atlantic salmon"`, `"farmed salmon"`

### **Nutrition Notes**
- All values are per 100g unless otherwise specified
- Branded foods may have serving size information
- Some nutrients may not be available for all foods
- Values are from laboratory analysis or calculated estimates

## 🚀 Deployment

### **Local Development**
```bash
git clone <repository>
cd usda-nutrition-ai-toolkit
pip install -r requirements.txt
echo "FDC_API_KEY=your_key" > .env
python -m uvicorn src.mcp_http_server:app --reload
```

### **Docker**
```bash
docker-compose up --build
```

### **Google Cloud Run**
```bash
export PROJECT_ID="your-gcp-project"
export FDC_API_KEY="your-usda-key"
./scripts/deploy-gcp.sh
```

## 📄 API Response Format

All endpoints return a consistent response format:

```json
{
  "success": boolean,
  "data": object | null,
  "error": string | null,
  "tool": string | null,
  "message": string | null,
  "timestamp": "ISO 8601 datetime"
}
```

## 🔑 Getting Your USDA API Key

1. Visit [USDA FoodData Central API](https://fdc.nal.usda.gov/api-guide.html)
2. Sign up for a free account
3. Generate your API key
4. Add to your `.env` file: `FDC_API_KEY=your_key_here`

## 📊 Rate Limits

- **USDA API**: 1000 requests per hour per API key
- **This service**: No additional rate limits (inherit USDA limits)
- **Recommendation**: Cache results for frequently accessed foods

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **USDA FoodData Central** for providing comprehensive, free nutrition data
- **Anthropic** for the MCP protocol
- **FastAPI** for the excellent web framework

---

**Built with ❤️ for the nutrition and AI community**