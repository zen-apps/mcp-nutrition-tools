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
    NutritionQuestionParams
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
        structlog.processors.JSONRenderer()
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
    description="HTTP MCP server providing nutrition tools powered by USDA FoodData Central",
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
        }
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
            }
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
                    "data_type": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["query"]
            }
        ),
        ToolInfo(
            name="get_food_nutrition",
            description="Get detailed nutrition information for a specific food",
            input_schema={
                "type": "object", 
                "properties": {
                    "fdc_id": {"type": "integer", "description": "USDA FoodData Central ID"},
                    "format": {"type": "string", "default": "abridged", "enum": ["abridged", "full"]}
                },
                "required": ["fdc_id"]
            }
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
                        "description": "List of FDC IDs to compare"
                    }
                },
                "required": ["fdc_ids"]
            }
        ),
        ToolInfo(
            name="nutrition_question_helper",
            description="Get guidance for nutrition questions and food recommendations",
            input_schema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Nutrition question"},
                    "context": {"type": "string", "description": "Additional context"}
                },
                "required": ["question"]
            }
        ),
        ToolInfo(
            name="get_food_categories",
            description="Get information about USDA food categories and data types",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
    ]
    
    return {
        "tools": [tool.dict() for tool in tools],
        "count": len(tools),
        "server": "usda-nutrition-mcp",
        "version": "1.0.0"
    }

# =============================================================================
# MCP TOOL ENDPOINTS
# =============================================================================

@app.post("/tools/search_foods", response_model=MCPResponse)
async def search_foods(params: SearchParams):
    """Search for foods in the USDA database"""
    try:
        logger.info("search_foods_called", query=params.query, page_size=params.page_size)
        
        result = await usda_client.search_foods(
            query=params.query,
            data_type=params.data_type,
            page_size=params.page_size,
            page_number=params.page_number
        )
        
        # Format response for better readability
        if result.get("foods"):
            formatted_foods = []
            for food in result["foods"][:10]:  # Limit for API response size
                formatted_foods.append({
                    "fdc_id": food.get("fdcId"),
                    "description": food.get("description"),
                    "data_type": food.get("dataType"),
                    "food_category": food.get("foodCategory"),
                    "brand_owner": food.get("brandOwner"),
                    "ingredients": food.get("ingredients"),
                })
            
            response_data = {
                "success": True,
                "total_results": result.get("totalPages", 0) * result.get("pageSize", 0),
                "current_page": result.get("currentPage", 1),
                "foods": formatted_foods,
                "message": f"Found {len(formatted_foods)} foods matching '{params.query}'"
            }
        else:
            response_data = {
                "success": False,
                "error": "No foods found",
                "foods": []
            }
        
        return MCPResponse(
            success=True,
            data=response_data,
            tool="search_foods"
        )
        
    except Exception as e:
        logger.error("search_foods_failed", error=str(e), query=params.query)
        return MCPResponse(
            success=False,
            error=f"Search failed: {str(e)}",
            tool="search_foods"
        )

@app.post("/tools/get_food_nutrition", response_model=MCPResponse)
async def get_food_nutrition(params: FoodDetailParams):
    """Get detailed nutrition information for a specific food"""
    try:
        logger.info("get_food_nutrition_called", fdc_id=params.fdc_id)
        
        result = await usda_client.get_food_details(
            fdc_id=params.fdc_id,
            format=params.format
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
                "other_nutrients": []
            }
        }
        
        # Process nutrients with categorization
        food_nutrients = result.get("foodNutrients", [])
        
        # Key nutrient mappings
        macro_nutrients = {
            1008: "Energy (kcal)", 1003: "Protein", 1004: "Total Fat", 
            1005: "Carbohydrate", 1079: "Fiber", 2000: "Sugar"
        }
        vitamin_nutrients = {
            1106: "Vitamin A", 1162: "Vitamin C", 1114: "Vitamin D",
            1109: "Vitamin E", 1185: "Folate"
        }
        mineral_nutrients = {
            1087: "Calcium", 1089: "Iron", 1090: "Magnesium",
            1091: "Phosphorus", 1092: "Potassium", 1093: "Sodium", 1095: "Zinc"
        }
        
        for nutrient in food_nutrients:
            nutrient_info = nutrient.get("nutrient", {})
            nutrient_id = nutrient_info.get("id")
            nutrient_name = nutrient_info.get("name")
            amount = nutrient.get("amount")
            unit = nutrient_info.get("unitName")
            
            if amount is not None:
                nutrient_data = {
                    "name": nutrient_name,
                    "amount": amount,
                    "unit": unit
                }
                
                # Categorize nutrients
                if nutrient_id in macro_nutrients:
                    nutrition_summary["nutrition"]["macronutrients"][nutrient_name] = nutrient_data
                elif nutrient_id in vitamin_nutrients:
                    nutrition_summary["nutrition"]["vitamins"][nutrient_name] = nutrient_data
                elif nutrient_id in mineral_nutrients:
                    nutrition_summary["nutrition"]["minerals"][nutrient_name] = nutrient_data
                else:
                    # Limit other nutrients for response size
                    if len(nutrition_summary["nutrition"]["other_nutrients"]) < 10:
                        nutrition_summary["nutrition"]["other_nutrients"].append(nutrient_data)
        
        return MCPResponse(
            success=True,
            data=nutrition_summary,
            tool="get_food_nutrition",
            message=f"Retrieved nutrition data for {result.get('description', 'food item')}"
        )
        
    except Exception as e:
        logger.error("get_food_nutrition_failed", error=str(e), fdc_id=params.fdc_id)
        return MCPResponse(
            success=False,
            error=f"Failed to get nutrition data: {str(e)}",
            tool="get_food_nutrition"
        )

@app.post("/tools/compare_foods", response_model=MCPResponse)
async def compare_foods(params: CompareFoodsParams):
    """Compare nutritional information between multiple foods"""
    try:
        if len(params.fdc_ids) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 foods can be compared")
        
        logger.info("compare_foods_called", fdc_ids=params.fdc_ids)
        
        # Get nutrition data for all foods
        foods_data = []
        for fdc_id in params.fdc_ids:
            try:
                food_result = await usda_client.get_food_details(fdc_id, format="abridged")
                foods_data.append(food_result)
            except Exception as e:
                logger.warning("failed_to_get_food_data", fdc_id=fdc_id, error=str(e))
        
        if not foods_data:
            return MCPResponse(
                success=False,
                error="No valid food data found for comparison",
                tool="compare_foods"
            )
        
        # Build comparison structure
        comparison = {
            "foods": [],
            "nutrient_comparison": {},
            "summary": {
                "total_foods_compared": len(foods_data),
                "comparison_notes": [
                    "Values shown are per 100g unless otherwise specified",
                    "Use this data to compare foods for your dietary goals"
                ]
            }
        }
        
        # Key nutrients for comparison
        key_nutrients = {
            1008: "Energy (kcal)", 1003: "Protein", 1004: "Total Fat",
            1005: "Carbohydrate", 1079: "Fiber", 1087: "Calcium",
            1089: "Iron", 1162: "Vitamin C"
        }
        
        # Process each food
        for food in foods_data:
            food_summary = {
                "fdc_id": food.get("fdcId"),
                "description": food.get("description"),
                "data_type": food.get("dataType"),
                "nutrients": {}
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
                        "unit": unit
                    }
                    
                    # Add to comparison matrix
                    if nutrient_name not in comparison["nutrient_comparison"]:
                        comparison["nutrient_comparison"][nutrient_name] = []
                    
                    comparison["nutrient_comparison"][nutrient_name].append({
                        "food": food.get("description"),
                        "amount": amount,
                        "unit": unit
                    })
            
            comparison["foods"].append(food_summary)
        
        return MCPResponse(
            success=True,
            data=comparison,
            tool="compare_foods",
            message=f"Successfully compared {len(foods_data)} foods"
        )
        
    except Exception as e:
        logger.error("compare_foods_failed", error=str(e), fdc_ids=params.fdc_ids)
        return MCPResponse(
            success=False,
            error=f"Failed to compare foods: {str(e)}",
            tool="compare_foods"
        )

@app.post("/tools/nutrition_question_helper", response_model=MCPResponse)
async def nutrition_question_helper(params: NutritionQuestionParams):
    """Get guidance for nutrition questions"""
    try:
        logger.info("nutrition_question_helper_called", question=params.question)
        
        question = params.question.lower()
        context = params.context or ""
        
        suggestions = {
            "question": params.question,
            "suggested_searches": [],
            "recommended_tools": [],
            "tips": [],
            "sample_queries": []
        }
        
        # Analyze question for relevant suggestions
        if any(word in question for word in ["high protein", "protein rich", "protein content"]):
            suggestions["suggested_searches"] = ["chicken breast", "salmon", "tofu", "greek yogurt", "lentils"]
            suggestions["recommended_tools"] = ["search_foods", "compare_foods"]
            suggestions["tips"] = [
                "Search for specific protein sources",
                "Compare protein content per 100g",
                "Look for foods with >20g protein per 100g for high-protein options"
            ]
        elif any(word in question for word in ["low sodium", "low salt", "reduce sodium"]):
            suggestions["suggested_searches"] = ["fresh vegetables", "unsalted nuts", "fresh fruits"]
            suggestions["recommended_tools"] = ["search_foods", "get_food_nutrition"]
            suggestions["tips"] = [
                "Look for fresh, unprocessed foods",
                "Check sodium content in nutrition labels",
                "Aim for <140mg sodium per serving for 'low sodium'"
            ]
        elif any(word in question for word in ["compare", "better", "versus", "vs"]):
            suggestions["recommended_tools"] = ["compare_foods", "search_foods"]
            suggestions["tips"] = [
                "First search for each food to get their FDC IDs",
                "Then use compare_foods to see side-by-side nutrition"
            ]
        else:
            suggestions["recommended_tools"] = ["search_foods"]
            suggestions["tips"] = [
                "Start by searching for specific foods you're interested in",
                "Use get_food_nutrition for detailed information"
            ]
        
        # Add general tips
        suggestions["tips"].extend([
            "All nutrition values are per 100g unless specified",
            "Look for 'Foundation' data type for generic foods",
            "Use 'Branded' data type for specific commercial products"
        ])
        
        return MCPResponse(
            success=True,
            data=suggestions,
            tool="nutrition_question_helper",
            message="Suggestions for exploring your nutrition question with USDA data"
        )
        
    except Exception as e:
        logger.error("nutrition_question_helper_failed", error=str(e))
        return MCPResponse(
            success=False,
            error=f"Failed to process nutrition question: {str(e)}",
            tool="nutrition_question_helper"
        )

@app.get("/tools/get_food_categories", response_model=MCPResponse)
async def get_food_categories():
    """Get information about USDA food categories and data types"""
    try:
        data_types = {
            "Foundation": {
                "description": "Generic food items with detailed nutrient profiles",
                "example": "Chicken breast, raw",
                "best_for": "Getting nutrition data for basic, unbranded foods"
            },
            "Branded": {
                "description": "Commercial food products with UPC codes",
                "example": "Cheerios Original cereal",
                "best_for": "Specific brand name products and packaged foods"
            },
            "Survey": {
                "description": "Foods from the Food and Nutrient Database for Dietary Studies",
                "example": "Pizza, meat topping, regular crust",
                "best_for": "Foods as typically consumed in surveys"
            },
            "SR Legacy": {
                "description": "Data from the legacy Standard Reference database",
                "example": "Milk, whole, 3.25% milkfat",
                "best_for": "Historical data and research comparisons"
            }
        }
        
        info = {
            "data_types": data_types,
            "search_tips": [
                "Use simple, descriptive terms for best results",
                "Try both generic names ('chicken') and specific terms ('chicken breast')",
                "Foundation and SR Legacy are good for basic foods",
                "Branded is best for specific commercial products"
            ],
            "common_categories": [
                "Dairy and Egg Products", "Spices and Herbs", "Fats and Oils",
                "Poultry Products", "Fruits and Fruit Juices", "Vegetables and Vegetable Products",
                "Nut and Seed Products", "Beef Products", "Beverages", "Legumes and Legume Products",
                "Baked Products", "Sweets", "Cereal Grains and Pasta", "Fast Foods"
            ]
        }
        
        return MCPResponse(
            success=True,
            data=info,
            tool="get_food_categories",
            message="USDA FoodData Central organization and search guidance"
        )
        
    except Exception as e:
        logger.error("get_food_categories_failed", error=str(e))
        return MCPResponse(
            success=False,
            error=f"Failed to get category information: {str(e)}",
            tool="get_food_categories"
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
    
    logger.info("mcp_http_server_started", 
                usda_api_configured=usda_client.is_configured())

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