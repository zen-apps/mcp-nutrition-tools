#!/usr/bin/env python3

"""
USDA Nutrition MCP Server
=========================

Model Context Protocol server for USDA FoodData Central API integration.
Provides tools for searching foods, getting nutrition details, and analyzing foods.
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional, Sequence

from fastmcp import FastMCP
import structlog

from .usda_client import USDAClient
# from .models.responses import FoodSearchResponse, FoodDetailsResponse  # Not needed for MCP tools

logger = structlog.get_logger("mcp_server")

# Initialize MCP server
mcp = FastMCP("USDA Nutrition")

# Global client instance
client: Optional[USDAClient] = None

async def get_client() -> USDAClient:
    """Get or initialize the USDA client"""
    global client
    if client is None:
        client = USDAClient()
        await client.initialize()
    return client

@mcp.tool()
async def search_foods(
    query: str,
    data_type: Optional[List[str]] = None,
    page_size: int = 25,
    page_number: int = 1
) -> Dict[str, Any]:
    """
    Search for foods in the USDA FoodData Central database.
    
    Args:
        query: Search term (e.g., "apple", "chicken breast")
        data_type: Filter by data types (e.g., ["Foundation", "SR Legacy"])
        page_size: Number of results per page (max 200)
        page_number: Page number to retrieve
        
    Returns:
        Search results with food items and pagination info
    """
    try:
        usda_client = await get_client()
        if not usda_client.is_configured():
            return {
                "error": "USDA API key not configured. Please set FDC_API_KEY environment variable."
            }
        
        result = await usda_client.search_foods(
            query=query,
            data_type=data_type,
            page_size=page_size,
            page_number=page_number
        )
        
        logger.info("food_search_completed", query=query, results_count=len(result.get("foods", [])))
        return result
        
    except Exception as e:
        logger.error("food_search_failed", query=query, error=str(e))
        return {"error": f"Search failed: {str(e)}"}

@mcp.tool()
async def get_food_details(
    fdc_id: int,
    format: str = "abridged"
) -> Dict[str, Any]:
    """
    Get detailed nutrition information for a specific food.
    
    Args:
        fdc_id: Food Data Central ID
        format: Response format ("abridged" or "full")
        
    Returns:
        Detailed food information including nutrients
    """
    try:
        usda_client = await get_client()
        if not usda_client.is_configured():
            return {
                "error": "USDA API key not configured. Please set FDC_API_KEY environment variable."
            }
        
        result = await usda_client.get_food_details(fdc_id=fdc_id, format=format)
        
        logger.info("food_details_retrieved", fdc_id=fdc_id, format=format)
        return result
        
    except Exception as e:
        logger.error("food_details_failed", fdc_id=fdc_id, error=str(e))
        return {"error": f"Failed to get food details: {str(e)}"}

@mcp.tool() 
async def get_multiple_foods(
    fdc_ids: List[int],
    format: str = "abridged"
) -> Dict[str, Any]:
    """
    Get nutrition information for multiple foods at once.
    
    Args:
        fdc_ids: List of Food Data Central IDs (max 20)
        format: Response format ("abridged" or "full")
        
    Returns:
        List of food details
    """
    try:
        if len(fdc_ids) > 20:
            return {"error": "Maximum 20 foods can be requested at once"}
            
        usda_client = await get_client()
        if not usda_client.is_configured():
            return {
                "error": "USDA API key not configured. Please set FDC_API_KEY environment variable."
            }
        
        result = await usda_client.get_multiple_foods(fdc_ids=fdc_ids, format=format)
        
        logger.info("multiple_foods_retrieved", fdc_ids=fdc_ids, count=len(fdc_ids))
        return {"foods": result}
        
    except Exception as e:
        logger.error("multiple_foods_failed", fdc_ids=fdc_ids, error=str(e))
        return {"error": f"Failed to get multiple foods: {str(e)}"}

@mcp.tool()
async def analyze_nutrition(
    fdc_ids: List[int],
    nutrients_of_interest: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Analyze and compare nutrition data across multiple foods.
    
    Args:
        fdc_ids: List of Food Data Central IDs to analyze
        nutrients_of_interest: Specific nutrients to focus on (e.g., ["Protein", "Vitamin C"])
        
    Returns:
        Nutrition analysis and comparison
    """
    try:
        if len(fdc_ids) > 10:
            return {"error": "Maximum 10 foods can be analyzed at once"}
            
        usda_client = await get_client()
        if not usda_client.is_configured():
            return {
                "error": "USDA API key not configured. Please set FDC_API_KEY environment variable."
            }
        
        foods = await usda_client.get_multiple_foods(fdc_ids=fdc_ids, format="full")
        
        analysis = {
            "foods_analyzed": len(foods),
            "comparison": [],
            "summary": {}
        }
        
        for food in foods:
            food_analysis = {
                "name": food.get("description", "Unknown"),
                "fdc_id": food.get("fdcId"),
                "nutrients": {}
            }
            
            if "foodNutrients" in food:
                for nutrient in food["foodNutrients"]:
                    nutrient_name = nutrient.get("nutrient", {}).get("name")
                    if nutrient_name and (not nutrients_of_interest or nutrient_name in nutrients_of_interest):
                        food_analysis["nutrients"][nutrient_name] = {
                            "amount": nutrient.get("amount"),
                            "unit": nutrient.get("nutrient", {}).get("unitName")
                        }
            
            analysis["comparison"].append(food_analysis)
        
        logger.info("nutrition_analysis_completed", fdc_ids=fdc_ids, foods_count=len(foods))
        return analysis
        
    except Exception as e:
        logger.error("nutrition_analysis_failed", fdc_ids=fdc_ids, error=str(e))
        return {"error": f"Nutrition analysis failed: {str(e)}"}

async def main():
    """Main entry point for the MCP server"""
    try:
        # Initialize logging
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        logger.info("usda_nutrition_mcp_server_starting")
        
        # Run the MCP server
        await mcp.run()
        
    except KeyboardInterrupt:
        logger.info("usda_nutrition_mcp_server_shutdown")
    except Exception as e:
        logger.error("usda_nutrition_mcp_server_error", error=str(e))
        raise
    finally:
        # Clean up client
        if client:
            await client.close()

import asyncio

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "already running" in str(e):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
        else:
            raise
