#!/usr/bin/env python3
"""
HTTP MCP Server for USDA Nutrition Tools
========================================

FastAPI-based HTTP server that exposes MCP nutrition tools via REST API.
Designed for Cloud Run deployment and framework-agnostic access.

Author: Josh Janzen
License: MIT
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .models.requests import (
    SearchParams,
    FoodDetailParams,
    CompareFoodsParams,
    AgentTestParams,
)
from .models.responses import MCPResponse, ToolInfo
from .usda_client import USDAClient

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("mcp_http_server")

# Initialize FastAPI app
app = FastAPI(
    title="USDA Nutrition MCP Server",
    description="""HTTP MCP server providing nutrition tools powered by USDA FoodData Central.
    
🔌 **MCP Integration Ready** - Connect AI assistants to 600k+ foods with comprehensive nutrition data.

🎯 **Test Endpoints:**
- `/test/mcp-tools` - Test MCP server functionality  
- `/test/agent-demo` - Demo Claude/OpenAI/LangChain integration

🛠 **Nutrition Tools:**
- Search foods, get nutrition details, compare foods, analyze nutrition
- Perfect for AI agents, nutrition apps, and health research

Get your free USDA API key: https://fdc.nal.usda.gov/api-guide.html""",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize USDA client
usda_client = USDAClient()

# =============================================================================
# MIDDLEWARE & ERROR HANDLING
# =============================================================================


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with structured logging"""
    start_time = datetime.now(timezone.utc)

    # Log request
    logger.info(
        "http_request_started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
    )

    try:
        response = await call_next(request)

        # Log response
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            "http_request_completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            duration_seconds=duration,
        )

        return response

    except Exception as e:
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.error(
            "http_request_failed",
            method=request.method,
            url=str(request.url),
            error=str(e),
            duration_seconds=duration,
        )
        raise


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with structured logging"""
    logger.error(
        "unhandled_exception",
        method=request.method,
        url=str(request.url),
        error=str(exc),
        error_type=type(exc).__name__,
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers"""
    try:
        # Test USDA API connectivity
        is_usda_healthy = await usda_client.health_check()

        return {
            "status": "healthy" if is_usda_healthy else "degraded",
            "service": "usda-nutrition-mcp",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "usda_api": "connected" if is_usda_healthy else "disconnected",
        }
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


@app.get("/tools")
async def list_tools():
    """List available MCP tools"""
    tools = [
        ToolInfo(
            name="search_foods",
            description="Search for foods in the USDA database by keywords",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term"},
                    "page_size": {"type": "integer", "default": 25, "maximum": 200},
                    "data_type": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["query"],
            },
        ),
        ToolInfo(
            name="get_food_nutrition",
            description="Get detailed nutrition information for a specific food",
            input_schema={
                "type": "object",
                "properties": {
                    "fdc_id": {
                        "type": "integer",
                        "description": "USDA FoodData Central ID",
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
        ToolInfo(
            name="compare_foods",
            description="Compare nutritional information between multiple foods",
            input_schema={
                "type": "object",
                "properties": {
                    "fdc_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "maxItems": 5,
                        "description": "List of FDC IDs to compare",
                    }
                },
                "required": ["fdc_ids"],
            },
        ),
        ToolInfo(
            name="nutrition_question_helper",
            description="Get guidance for nutrition questions and food recommendations",
            input_schema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Nutrition question"},
                    "context": {"type": "string", "description": "Additional context"},
                },
                "required": ["question"],
            },
        ),
        ToolInfo(
            name="get_food_categories",
            description="Get information about USDA food categories and data types",
            input_schema={"type": "object", "properties": {}},
        ),
    ]

    return {
        "tools": [tool.dict() for tool in tools],
        "count": len(tools),
        "server": "usda-nutrition-mcp",
        "version": "1.0.0",
    }


# =============================================================================
# MCP TOOL ENDPOINTS
# =============================================================================


@app.post("/tools/search_foods", response_model=MCPResponse)
async def search_foods(params: SearchParams):
    """Search for foods in the USDA database"""
    try:
        logger.info(
            "search_foods_called", query=params.query, page_size=params.page_size
        )

        result = await usda_client.search_foods(
            query=params.query,
            data_type=params.data_type,
            page_size=params.page_size,
            page_number=params.page_number,
        )

        # Format response for better readability
        if result.get("foods"):
            formatted_foods = []
            for food in result["foods"][:10]:  # Limit for API response size
                formatted_foods.append(
                    {
                        "fdc_id": food.get("fdcId"),
                        "description": food.get("description"),
                        "data_type": food.get("dataType"),
                        "food_category": food.get("foodCategory"),
                        "brand_owner": food.get("brandOwner"),
                        "ingredients": food.get("ingredients"),
                    }
                )

            response_data = {
                "success": True,
                "total_results": result.get("totalPages", 0)
                * result.get("pageSize", 0),
                "current_page": result.get("currentPage", 1),
                "foods": formatted_foods,
                "message": f"Found {len(formatted_foods)} foods matching '{params.query}'",
            }
            print(
                f"search_foods: Found {len(formatted_foods)} foods for query '{params.query}'"
            )

        else:
            response_data = {"success": False, "error": "No foods found", "foods": []}
        logger.info(
            "search_foods_completed", foods_found=len(response_data.get("foods", []))
        )
        return MCPResponse(success=True, data=response_data, tool="search_foods")

    except Exception as e:
        logger.error("search_foods_failed", error=str(e), query=params.query)
        return MCPResponse(
            success=False, error=f"Search failed: {str(e)}", tool="search_foods"
        )


@app.post("/tools/get_food_nutrition", response_model=MCPResponse)
async def get_food_nutrition(params: FoodDetailParams):
    """Get detailed nutrition information for a specific food"""
    try:
        logger.info("get_food_nutrition_called", fdc_id=params.fdc_id)

        result = await usda_client.get_food_details(
            fdc_id=params.fdc_id, format=params.format
        )

        # Extract and organize nutrition information
        nutrition_summary = {
            "food_info": {
                "fdc_id": result.get("fdcId"),
                "description": result.get("description"),
                "data_type": result.get("dataType"),
                "food_category": result.get("foodCategory"),
                "brand_owner": result.get("brandOwner"),
                "serving_size": result.get("servingSize"),
                "serving_size_unit": result.get("servingSizeUnit"),
            },
            "nutrition": {
                "macronutrients": {},
                "vitamins": {},
                "minerals": {},
                "other_nutrients": [],
            },
        }

        # Process nutrients with categorization
        food_nutrients = result.get("foodNutrients", [])

        # Key nutrient mappings
        macro_nutrients = {
            1008: "Energy (kcal)",
            1003: "Protein",
            1004: "Total Fat",
            1005: "Carbohydrate",
            1079: "Fiber",
            2000: "Sugar",
        }
        vitamin_nutrients = {
            1106: "Vitamin A",
            1162: "Vitamin C",
            1114: "Vitamin D",
            1109: "Vitamin E",
            1185: "Folate",
        }
        mineral_nutrients = {
            1087: "Calcium",
            1089: "Iron",
            1090: "Magnesium",
            1091: "Phosphorus",
            1092: "Potassium",
            1093: "Sodium",
            1095: "Zinc",
        }

        for nutrient in food_nutrients:
            nutrient_info = nutrient.get("nutrient", {})
            nutrient_id = nutrient_info.get("id")
            nutrient_name = nutrient_info.get("name")
            amount = nutrient.get("amount")
            unit = nutrient_info.get("unitName")

            if amount is not None:
                nutrient_data = {"name": nutrient_name, "amount": amount, "unit": unit}

                # Categorize nutrients
                if nutrient_id in macro_nutrients:
                    nutrition_summary["nutrition"]["macronutrients"][
                        nutrient_name
                    ] = nutrient_data
                elif nutrient_id in vitamin_nutrients:
                    nutrition_summary["nutrition"]["vitamins"][
                        nutrient_name
                    ] = nutrient_data
                elif nutrient_id in mineral_nutrients:
                    nutrition_summary["nutrition"]["minerals"][
                        nutrient_name
                    ] = nutrient_data
                else:
                    # Limit other nutrients for response size
                    if len(nutrition_summary["nutrition"]["other_nutrients"]) < 10:
                        nutrition_summary["nutrition"]["other_nutrients"].append(
                            nutrient_data
                        )

        return MCPResponse(
            success=True,
            data=nutrition_summary,
            tool="get_food_nutrition",
            message=f"Retrieved nutrition data for {result.get('description', 'food item')}",
        )

    except Exception as e:
        logger.error("get_food_nutrition_failed", error=str(e), fdc_id=params.fdc_id)
        return MCPResponse(
            success=False,
            error=f"Failed to get nutrition data: {str(e)}",
            tool="get_food_nutrition",
        )


@app.post("/tools/compare_foods", response_model=MCPResponse)
async def compare_foods(params: CompareFoodsParams):
    """Compare nutritional information between multiple foods"""
    try:
        if len(params.fdc_ids) > 5:
            raise HTTPException(
                status_code=400, detail="Maximum 5 foods can be compared"
            )

        logger.info("compare_foods_called", fdc_ids=params.fdc_ids)

        # Get nutrition data for all foods
        foods_data = []
        for fdc_id in params.fdc_ids:
            try:
                food_result = await usda_client.get_food_details(
                    fdc_id, format="abridged"
                )
                foods_data.append(food_result)
            except Exception as e:
                logger.warning("failed_to_get_food_data", fdc_id=fdc_id, error=str(e))

        if not foods_data:
            return MCPResponse(
                success=False,
                error="No valid food data found for comparison",
                tool="compare_foods",
            )

        # Build comparison structure
        comparison = {
            "foods": [],
            "nutrient_comparison": {},
            "summary": {
                "total_foods_compared": len(foods_data),
                "comparison_notes": [
                    "Values shown are per 100g unless otherwise specified",
                    "Use this data to compare foods for your dietary goals",
                ],
            },
        }

        # Key nutrients for comparison
        key_nutrients = {
            1008: "Energy (kcal)",
            1003: "Protein",
            1004: "Total Fat",
            1005: "Carbohydrate",
            1079: "Fiber",
            1087: "Calcium",
            1089: "Iron",
            1162: "Vitamin C",
        }

        # Process each food
        for food in foods_data:
            food_summary = {
                "fdc_id": food.get("fdcId"),
                "description": food.get("description"),
                "data_type": food.get("dataType"),
                "nutrients": {},
            }

            # Extract key nutrients
            for nutrient in food.get("foodNutrients", []):
                nutrient_info = nutrient.get("nutrient", {})
                nutrient_id = nutrient_info.get("id")

                if nutrient_id in key_nutrients:
                    nutrient_name = key_nutrients[nutrient_id]
                    amount = nutrient.get("amount", 0)
                    unit = nutrient_info.get("unitName", "")

                    food_summary["nutrients"][nutrient_name] = {
                        "amount": amount,
                        "unit": unit,
                    }

                    # Add to comparison matrix
                    if nutrient_name not in comparison["nutrient_comparison"]:
                        comparison["nutrient_comparison"][nutrient_name] = []

                    comparison["nutrient_comparison"][nutrient_name].append(
                        {
                            "food": food.get("description"),
                            "amount": amount,
                            "unit": unit,
                        }
                    )

            comparison["foods"].append(food_summary)

        return MCPResponse(
            success=True,
            data=comparison,
            tool="compare_foods",
            message=f"Successfully compared {len(foods_data)} foods",
        )

    except Exception as e:
        logger.error("compare_foods_failed", error=str(e), fdc_ids=params.fdc_ids)
        return MCPResponse(
            success=False,
            error=f"Failed to compare foods: {str(e)}",
            tool="compare_foods",
        )




@app.get("/tools/get_food_categories", response_model=MCPResponse)
async def get_food_categories():
    """Get information about USDA food categories and data types"""
    try:
        data_types = {
            "Foundation": {
                "description": "Generic food items with detailed nutrient profiles",
                "example": "Chicken breast, raw",
                "best_for": "Getting nutrition data for basic, unbranded foods",
            },
            "Branded": {
                "description": "Commercial food products with UPC codes",
                "example": "Cheerios Original cereal",
                "best_for": "Specific brand name products and packaged foods",
            },
            "Survey": {
                "description": "Foods from the Food and Nutrient Database for Dietary Studies",
                "example": "Pizza, meat topping, regular crust",
                "best_for": "Foods as typically consumed in surveys",
            },
            "SR Legacy": {
                "description": "Data from the legacy Standard Reference database",
                "example": "Milk, whole, 3.25% milkfat",
                "best_for": "Historical data and research comparisons",
            },
        }

        info = {
            "data_types": data_types,
            "search_tips": [
                "Use simple, descriptive terms for best results",
                "Try both generic names ('chicken') and specific terms ('chicken breast')",
                "Foundation and SR Legacy are good for basic foods",
                "Branded is best for specific commercial products",
            ],
            "common_categories": [
                "Dairy and Egg Products",
                "Spices and Herbs",
                "Fats and Oils",
                "Poultry Products",
                "Fruits and Fruit Juices",
                "Vegetables and Vegetable Products",
                "Nut and Seed Products",
                "Beef Products",
                "Beverages",
                "Legumes and Legume Products",
                "Baked Products",
                "Sweets",
                "Cereal Grains and Pasta",
                "Fast Foods",
            ],
        }

        return MCPResponse(
            success=True,
            data=info,
            tool="get_food_categories",
            message="USDA FoodData Central organization and search guidance",
        )

    except Exception as e:
        logger.error("get_food_categories_failed", error=str(e))
        return MCPResponse(
            success=False,
            error=f"Failed to get category information: {str(e)}",
            tool="get_food_categories",
        )


# =============================================================================
# AGENT INTEGRATION DEMOS
# =============================================================================


@app.post("/test/mcp-tools")
async def test_mcp_tools():
    """Test MCP server tools directly - mimics what Claude Desktop would do"""
    try:
        logger.info("testing_mcp_tools_directly")

        # Test the same functionality that MCP tools use (via USDA client)
        # This simulates what the MCP server does internally

        # Test search_foods functionality
        search_result = await usda_client.search_foods("chicken breast", page_size=3)

        # Test get_food_details functionality
        food_details = None
        if search_result.get("foods") and len(search_result["foods"]) > 0:
            fdc_id = search_result["foods"][0].get("fdcId")
            if fdc_id:
                food_details = await usda_client.get_food_details(fdc_id)

        # Test multiple foods functionality (simulate analyze_nutrition)
        multiple_foods = None
        if search_result.get("foods") and len(search_result["foods"]) >= 2:
            fdc_ids = [
                food.get("fdcId")
                for food in search_result["foods"][:2]
                if food.get("fdcId")
            ]
            if len(fdc_ids) >= 2:
                multiple_foods = await usda_client.get_multiple_foods(fdc_ids)

        return {
            "success": True,
            "message": "MCP tools functionality tested successfully",
            "test_results": {
                "search_foods": {
                    "status": "success" if search_result.get("foods") else "no_results",
                    "foods_found": len(search_result.get("foods", [])),
                    "sample_food": (
                        search_result.get("foods", [{}])[0].get("description")
                        if search_result.get("foods")
                        else None
                    ),
                },
                "get_food_details": {
                    "status": "success" if food_details else "skipped",
                    "has_nutrition_data": bool(
                        food_details and food_details.get("foodNutrients")
                    ),
                },
                "analyze_nutrition": {
                    "status": "success" if multiple_foods else "skipped",
                    "foods_analyzed": len(multiple_foods) if multiple_foods else 0,
                },
            },
            "note": "This endpoint tests the same USDA API functionality that MCP tools use",
            "mcp_server_url": "Use python -m src.mcp_server for actual MCP protocol",
        }

    except Exception as e:
        logger.error("mcp_tools_test_failed", error=str(e))
        return {
            "success": False,
            "error": f"MCP tools test failed: {str(e)}",
            "note": "Check server logs for details",
        }


# =============================================================================
# INTERACTIVE DEMO ENDPOINTS - Run directly from Swagger UI!
# =============================================================================


@app.get(
    "/demo/protein-search",
    summary="🥩 Demo: Find High-Protein Foods",
    description="**Interactive Demo** - Finds high-protein foods like Claude would. Click 'Try it out' to run!",
    response_model=MCPResponse,
    tags=["🎯 Interactive Demos"],
)
async def demo_protein_search():
    """Demo: Search for high-protein foods and analyze nutrition"""
    try:
        logger.info("demo_protein_search_called")

        # Step 1: Search for protein sources
        search_params = SearchParams(
            query="chicken breast salmon greek yogurt", page_size=3
        )
        search_result = await search_foods(search_params)

        if not search_result.success:
            return MCPResponse(
                success=False, error="Search failed", tool="demo_protein_search"
            )

        foods = search_result.data["foods"][:2]  # Top 2
        fdc_ids = [food["fdc_id"] for food in foods if food.get("fdc_id")]

        # Step 2: Get detailed nutrition
        nutrition_details = []
        for fdc_id in fdc_ids[:2]:
            detail_params = FoodDetailParams(fdc_id=fdc_id)
            nutrition = await get_food_nutrition(detail_params)
            if nutrition.success:
                nutrition_details.append(nutrition.data)

        # Step 3: Compare if we have 2+ foods
        comparison_result = None
        if len(fdc_ids) >= 2:
            compare_params = CompareFoodsParams(fdc_ids=fdc_ids[:2])
            comparison_result = await compare_foods(compare_params)

        # Claude-style response
        demo_response = {
            "demo_scenario": "🥩 High-Protein Food Search (Claude MCP Style)",
            "user_query": "What are good high-protein foods for athletes?",
            "claude_workflow": [
                "1. 🔍 search_foods('chicken breast salmon greek yogurt')",
                "2. 🔬 get_food_nutrition() for top results",
                "3. ⚖️ compare_foods() to analyze differences",
                "4. 💬 Synthesize recommendations",
            ],
            "search_results": {
                "foods_found": len(foods),
                "top_foods": [
                    {"name": f["description"], "fdc_id": f["fdc_id"]} for f in foods
                ],
            },
            "nutrition_analysis": nutrition_details,
            "comparison": (
                comparison_result.data
                if comparison_result and comparison_result.success
                else None
            ),
            "claude_recommendations": [
                "🐔 Chicken breast: Excellent lean protein (~31g per 100g)",
                "🐟 Salmon: High protein + omega-3 fatty acids",
                "🥛 Greek yogurt: Protein + probiotics for gut health",
                "🎯 Target: 1.6-2.2g protein per kg body weight for athletes",
            ],
            "next_steps": [
                "Try asking Claude: 'Compare protein absorption rates'",
                "Or: 'What's the best protein timing for muscle growth?'",
            ],
        }

        return MCPResponse(
            success=True,
            data=demo_response,
            tool="demo_protein_search",
            message="🎉 Demo complete! This is exactly how Claude Desktop uses MCP tools.",
        )

    except Exception as e:
        logger.error("demo_protein_search_failed", error=str(e))
        return MCPResponse(
            success=False, error=f"Demo failed: {str(e)}", tool="demo_protein_search"
        )


@app.get(
    "/demo/weight-loss-foods",
    summary="🥗 Demo: Weight Loss Food Finder",
    description="**Interactive Demo** - Finds low-calorie, high-fiber foods for weight loss. One-click demo!",
    response_model=MCPResponse,
    tags=["🎯 Interactive Demos"],
)
async def demo_weight_loss_foods():
    """Demo: Find optimal foods for weight loss"""
    try:
        logger.info("demo_weight_loss_foods_called")

        # Search for weight-loss friendly foods
        search_params = SearchParams(
            query="broccoli spinach apple berries", page_size=4
        )
        search_result = await search_foods(search_params)

        if not search_result.success:
            return MCPResponse(
                success=False, error="Search failed", tool="demo_weight_loss"
            )

        foods = search_result.data["foods"][:3]
        food_analyses = []

        # Analyze each food for weight loss metrics
        for food in foods:
            fdc_id = food.get("fdc_id")
            if fdc_id:
                detail_params = FoodDetailParams(fdc_id=fdc_id)
                nutrition = await get_food_nutrition(detail_params)

                if nutrition.success:
                    macros = nutrition.data["nutrition"]["macronutrients"]
                    calories = macros.get("Energy (kcal)", {}).get("amount", 0)
                    fiber = macros.get("Fiber", {}).get("amount", 0)

                    food_analyses.append(
                        {
                            "food": food["description"],
                            "calories": calories,
                            "fiber": fiber,
                            "fiber_per_calorie": (
                                fiber / calories if calories > 0 else 0
                            ),
                            "weight_loss_score": (fiber * 10)
                            / (calories if calories > 0 else 1),  # Higher is better
                        }
                    )

        # Sort by weight loss effectiveness
        food_analyses.sort(key=lambda x: x["weight_loss_score"], reverse=True)

        demo_response = {
            "demo_scenario": "🥗 Weight Loss Food Optimization",
            "user_query": "What are the best low-calorie, high-fiber foods for weight loss?",
            "claude_analysis": {
                "methodology": "Analyze fiber-to-calorie ratio for satiety vs calories",
                "foods_analyzed": len(food_analyses),
                "ranking_criteria": "Higher fiber + Lower calories = Better for weight loss",
            },
            "food_rankings": [
                {
                    "rank": i + 1,
                    "food": food["food"],
                    "calories": f"{food['calories']}kcal per 100g",
                    "fiber": f"{food['fiber']}g per 100g",
                    "efficiency": f"{food['fiber_per_calorie']:.3f}g fiber per calorie",
                    "weight_loss_score": f"{food['weight_loss_score']:.1f}/10",
                }
                for i, food in enumerate(food_analyses)
            ],
            "claude_recommendations": [
                f"🥇 Top choice: {food_analyses[0]['food']} - Maximum fiber with minimal calories",
                "🍎 Aim for foods with >3g fiber per 100 calories",
                "🥬 Vegetables are your best friends for sustainable weight loss",
                "💧 High water content foods increase satiety",
            ],
            "meal_planning_tips": [
                "Fill half your plate with these high-fiber, low-calorie foods",
                "Eat these before higher-calorie foods to reduce overall intake",
                "Combine with lean protein for complete satiety",
            ],
        }

        return MCPResponse(
            success=True,
            data=demo_response,
            tool="demo_weight_loss_foods",
            message="🎯 Weight loss food analysis complete!",
        )

    except Exception as e:
        return MCPResponse(success=False, error=str(e), tool="demo_weight_loss_foods")


@app.get(
    "/demo/vegetarian-iron",
    summary="🌱 Demo: Vegetarian Iron Sources",
    description="**Interactive Demo** - Finds iron-rich plant foods for vegetarians. Perfect for dietary planning!",
    response_model=MCPResponse,
    tags=["🎯 Interactive Demos"],
)
async def demo_vegetarian_iron():
    """Demo: Find iron-rich foods for vegetarians"""
    try:
        logger.info("demo_vegetarian_iron_called")

        # Search for iron-rich plant foods
        search_params = SearchParams(query="spinach lentils tofu quinoa", page_size=4)
        search_result = await search_foods(search_params)

        if not search_result.success:
            return MCPResponse(
                success=False, error="Search failed", tool="demo_vegetarian_iron"
            )

        foods = search_result.data["foods"][:3]
        iron_sources = []

        for food in foods:
            fdc_id = food.get("fdc_id")
            if fdc_id:
                detail_params = FoodDetailParams(fdc_id=fdc_id)
                nutrition = await get_food_nutrition(detail_params)

                if nutrition.success:
                    minerals = nutrition.data["nutrition"].get("minerals", {})
                    iron = minerals.get("Iron", {}).get("amount", 0)

                    if iron > 0:
                        iron_sources.append(
                            {
                                "food": food["description"],
                                "iron_mg": iron,
                                "daily_value_percent": (iron / 18)
                                * 100,  # Based on 18mg RDA for women
                                "absorption_type": "Non-heme (plant-based)",
                            }
                        )

        iron_sources.sort(key=lambda x: x["iron_mg"], reverse=True)

        demo_response = {
            "demo_scenario": "🌱 Vegetarian Iron Optimization",
            "user_query": "I'm vegetarian and need more iron. What foods should I eat?",
            "iron_analysis": {
                "daily_needs": {
                    "men": "8mg per day",
                    "women": "18mg per day (premenopausal)",
                    "vegetarian_challenge": "Plant iron (non-heme) is less absorbable than meat iron",
                },
                "foods_analyzed": len(iron_sources),
            },
            "iron_rich_foods": [
                {
                    "food": source["food"],
                    "iron_content": f"{source['iron_mg']}mg per 100g",
                    "daily_value": f"{source['daily_value_percent']:.1f}% DV",
                    "absorption_tip": "Combine with vitamin C for better absorption",
                }
                for source in iron_sources
            ],
            "claude_recommendations": [
                f"🥬 Best source: {iron_sources[0]['food']} with {iron_sources[0]['iron_mg']}mg iron",
                "🍊 Always pair with vitamin C foods (citrus, bell peppers, strawberries)",
                "☕ Avoid tea/coffee with iron-rich meals (reduces absorption by 50-90%)",
                "🍳 Cook in cast iron pans to boost iron content",
            ],
            "meal_combinations": [
                "🥗 Spinach salad + strawberries + lemon dressing",
                "🍲 Lentil curry + tomatoes + bell peppers",
                "🥘 Tofu stir-fry + broccoli + orange segments",
            ],
            "absorption_enhancers": ["Vitamin C", "Meat proteins", "Fermented foods"],
            "absorption_inhibitors": [
                "Tea",
                "Coffee",
                "Calcium supplements",
                "Whole grains (phytates)",
            ],
        }

        return MCPResponse(
            success=True,
            data=demo_response,
            tool="demo_vegetarian_iron",
            message="🌱 Vegetarian iron guide complete!",
        )

    except Exception as e:
        return MCPResponse(success=False, error=str(e), tool="demo_vegetarian_iron")


@app.get(
    "/demo/meal-planning",
    summary="🍽️ Demo: Balanced Meal Planning",
    description="**Interactive Demo** - Plans a nutritionally balanced meal. Great for meal prep inspiration!",
    response_model=MCPResponse,
    tags=["🎯 Interactive Demos"],
)
async def demo_meal_planning():
    """Demo: Plan a balanced meal with optimal macros"""
    try:
        logger.info("demo_meal_planning_called")

        # Search for balanced meal components
        components = {
            "protein": "chicken breast",
            "complex_carbs": "brown rice",
            "healthy_fats": "avocado",
            "vegetables": "broccoli",
        }

        meal_components = []
        fdc_ids = []

        for component_type, food_query in components.items():
            search_params = SearchParams(query=food_query, page_size=1)
            search_result = await search_foods(search_params)

            if search_result.success and search_result.data["foods"]:
                food = search_result.data["foods"][0]
                fdc_id = food.get("fdc_id")
                if fdc_id:
                    fdc_ids.append(fdc_id)
                    meal_components.append(
                        {
                            "component": component_type,
                            "food": food["description"],
                            "fdc_id": fdc_id,
                        }
                    )

        # Get nutrition for all components
        nutrition_data = []
        for component in meal_components:
            detail_params = FoodDetailParams(fdc_id=component["fdc_id"])
            nutrition = await get_food_nutrition(detail_params)
            if nutrition.success:
                nutrition_data.append(
                    {
                        **component,
                        "nutrition": nutrition.data["nutrition"]["macronutrients"],
                    }
                )

        # Compare all meal components
        comparison_result = None
        if len(fdc_ids) >= 2:
            compare_params = CompareFoodsParams(fdc_ids=fdc_ids)
            comparison_result = await compare_foods(compare_params)

        # Calculate meal totals (example portions)
        portions = {
            "protein": 150,
            "complex_carbs": 80,
            "healthy_fats": 50,
            "vegetables": 200,
        }  # grams
        meal_totals = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}

        for data in nutrition_data:
            component = data["component"]
            portion_g = portions.get(component, 100)
            nutrition = data["nutrition"]

            # Scale nutrition to portion size
            multiplier = portion_g / 100
            meal_totals["calories"] += (
                nutrition.get("Energy (kcal)", {}).get("amount", 0) * multiplier
            )
            meal_totals["protein"] += (
                nutrition.get("Protein", {}).get("amount", 0) * multiplier
            )
            meal_totals["carbs"] += (
                nutrition.get("Carbohydrate", {}).get("amount", 0) * multiplier
            )
            meal_totals["fat"] += (
                nutrition.get("Total Fat", {}).get("amount", 0) * multiplier
            )

        demo_response = {
            "demo_scenario": "🍽️ Balanced Meal Planning",
            "user_query": "Help me plan a balanced meal with good macros for muscle building",
            "meal_composition": [
                {
                    "component": comp["component"].replace("_", " ").title(),
                    "food": comp["food"],
                    "portion": f"{portions.get(comp['component'], 100)}g",
                    "why_chosen": {
                        "protein": "Complete amino acid profile, lean protein",
                        "complex_carbs": "Sustained energy, B vitamins, fiber",
                        "healthy_fats": "Essential fatty acids, fat-soluble vitamins",
                        "vegetables": "Micronutrients, fiber, antioxidants",
                    }.get(comp["component"], "Nutritional balance"),
                }
                for comp in meal_components
            ],
            "meal_totals": {
                "total_calories": f"{meal_totals['calories']:.0f}kcal",
                "protein": f"{meal_totals['protein']:.1f}g ({meal_totals['protein']*4/meal_totals['calories']*100:.0f}% calories)",
                "carbohydrates": f"{meal_totals['carbs']:.1f}g ({meal_totals['carbs']*4/meal_totals['calories']*100:.0f}% calories)",
                "fat": f"{meal_totals['fat']:.1f}g ({meal_totals['fat']*9/meal_totals['calories']*100:.0f}% calories)",
            },
            "nutritional_analysis": {
                "macro_balance": "Optimal for muscle building and recovery",
                "protein_target": "30-40g protein per meal for muscle synthesis",
                "carb_timing": "Complex carbs for sustained energy",
                "micronutrients": "Vegetables provide essential vitamins and minerals",
            },
            "claude_recommendations": [
                f"🍗 Protein: {meal_totals['protein']:.1f}g supports muscle recovery",
                f"🍚 Carbs: {meal_totals['carbs']:.1f}g provides sustained energy",
                f"🥑 Fats: {meal_totals['fat']:.1f}g supports hormone production",
                f"📊 Total: {meal_totals['calories']:.0f}kcal - perfect for active individuals",
            ],
            "meal_prep_tips": [
                "Prep proteins in bulk on Sundays",
                "Cook grains in batches for the week",
                "Pre-cut vegetables for quick assembly",
                "Season with herbs/spices for variety",
            ],
        }

        return MCPResponse(
            success=True,
            data=demo_response,
            tool="demo_meal_planning",
            message="🍽️ Balanced meal plan complete!",
        )

    except Exception as e:
        return MCPResponse(success=False, error=str(e), tool="demo_meal_planning")


@app.post("/test/agent-demo")
async def agent_demo(params: AgentTestParams):
    """Demo how different AI agents would use the nutrition API"""
    try:
        logger.info("agent_demo_called", agent_type=params.agent_type)

        # Base nutrition query
        query = params.query or "high protein foods for athletes"

        if params.agent_type == "claude":
            # Claude MCP integration demo
            demo_response = {
                "agent": "Claude (via MCP)",
                "api_key_required": bool(params.claude_api_key),
                "query": query,
                "approach": "Uses MCP tools directly in Claude Desktop",
                "workflow": [
                    "1. Claude calls search_foods('high protein') via MCP",
                    "2. Claude calls get_food_details() for top results",
                    "3. Claude calls analyze_nutrition() to compare foods",
                    "4. Claude provides comprehensive nutrition guidance",
                ],
                "sample_mcp_calls": [
                    {
                        "tool": "search_foods",
                        "args": {"query": "chicken breast", "page_size": 5},
                    },
                    {"tool": "get_food_details", "args": {"fdc_id": 171077}},
                    {
                        "tool": "analyze_nutrition",
                        "args": {"fdc_ids": [171077, 175167]},
                    },
                ],
                "advantages": [
                    "Direct tool access in Claude Desktop",
                    "No API orchestration needed",
                    "Natural conversation flow",
                    "Automatic tool selection",
                ],
            }

        elif params.agent_type == "openai":
            # OpenAI function calling demo
            demo_response = {
                "agent": "OpenAI GPT (Function Calling)",
                "api_key_required": bool(params.openai_api_key),
                "query": query,
                "approach": "Uses OpenAI function calling with HTTP endpoints",
                "workflow": [
                    "1. Define functions for each nutrition tool",
                    "2. GPT decides which functions to call",
                    "3. Make HTTP requests to /tools/* endpoints",
                    "4. GPT processes results and responds",
                ],
                "sample_function_definition": {
                    "name": "search_nutrition_foods",
                    "description": "Search USDA database for foods",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "page_size": {"type": "integer", "default": 10},
                        },
                    },
                },
                "advantages": [
                    "Works with any OpenAI-compatible model",
                    "Flexible function definitions",
                    "HTTP-based, language agnostic",
                    "Can be used in any application",
                ],
            }

        elif params.agent_type == "langchain":
            # LangChain tool integration demo
            demo_response = {
                "agent": "LangChain Agent",
                "api_key_required": bool(
                    params.openai_api_key
                ),  # LangChain can use various models
                "query": query,
                "approach": "Uses LangChain tools and agents",
                "workflow": [
                    "1. Define LangChain tools wrapping HTTP endpoints",
                    "2. Create agent with nutrition tools",
                    "3. Agent plans and executes tool sequence",
                    "4. Agent synthesizes final response",
                ],
                "sample_tool_code": '''from langchain.tools import tool
import httpx

@tool
async def search_foods(query: str) -> dict:
    """Search for foods in USDA database"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "YOUR_SERVER/tools/search_foods",
            json={"query": query}
        )
        return response.json()''',
                "advantages": [
                    "Rich ecosystem of integrations",
                    "Memory and state management",
                    "Multi-step reasoning",
                    "Custom agent architectures",
                ],
            }

        else:
            demo_response = {
                "error": "Unknown agent type",
                "supported_types": ["claude", "openai", "langchain"],
            }

        # Add live demo if API key provided
        if params.agent_type in ["claude", "openai", "langchain"] and (
            params.claude_api_key or params.openai_api_key
        ):
            # Simulate actual API call workflow
            search_result = await usda_client.search_foods(
                "chicken breast", page_size=3
            )
            if search_result.get("foods"):
                demo_response["live_demo"] = {
                    "query_executed": "chicken breast",
                    "foods_found": len(search_result["foods"]),
                    "sample_results": [
                        {"name": food.get("description"), "fdc_id": food.get("fdcId")}
                        for food in search_result["foods"][:2]
                    ],
                    "note": "This demonstrates the data your agent would receive",
                }

        return MCPResponse(
            success=True,
            data=demo_response,
            tool="agent_demo",
            message=f"Demo for {params.agent_type} agent integration",
        )

    except Exception as e:
        logger.error("agent_demo_failed", error=str(e), agent_type=params.agent_type)
        return MCPResponse(
            success=False, error=f"Agent demo failed: {str(e)}", tool="agent_demo"
        )


# =============================================================================
# SERVER STARTUP
# =============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("mcp_http_server_starting", version="1.0.0")

    # Initialize USDA client
    await usda_client.initialize()

    logger.info(
        "mcp_http_server_started", usda_api_configured=usda_client.is_configured()
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("mcp_http_server_shutting_down")
    await usda_client.close()


if __name__ == "__main__":
    import uvicorn

    # Configuration
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")

    uvicorn.run(
        "src.mcp_http_server:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_config=None,  # Use our structured logging
    )
