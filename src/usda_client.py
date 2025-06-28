# src/usda_client.py
"""
USDA FoodData Central API Client
===============================

Async HTTP client for the USDA FoodData Central API with proper error handling,
rate limiting, and response formatting.
"""

import asyncio
import os
from typing import Any, Dict, List, Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger("usda_client")

class USDAClient:
    """Async client for USDA FoodData Central API"""
    
    def __init__(self):
        self.api_key = os.getenv("FDC_API_KEY")
        self.base_url = "https://api.nal.usda.gov/fdc/v1"
        self.client: Optional[httpx.AsyncClient] = None
        
    async def initialize(self):
        """Initialize the HTTP client"""
        if not self.api_key:
            logger.warning("usda_api_key_missing")
            return
            
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(30.0),
            headers={
                "X-Api-Key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "USDA-Nutrition-MCP/1.0.0"
            }
        )
        logger.info("usda_client_initialized")
    
    async def close(self):
        """Close the HTTP client"""
        if self.client:
            await self.client.aclose()
            logger.info("usda_client_closed")
    
    def is_configured(self) -> bool:
        """Check if client is properly configured"""
        return bool(self.api_key and self.client)
    
    async def health_check(self) -> bool:
        """Check if USDA API is accessible"""
        if not self.is_configured():
            return False
            
        try:
            response = await self.client.get("/foods/search", 
                                           params={"query": "apple", "pageSize": 1})
            return response.status_code == 200
        except Exception:
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        if not self.is_configured():
            raise Exception("USDA client not configured - missing API key")
        
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error("usda_api_http_error", 
                        status_code=e.response.status_code,
                        endpoint=endpoint,
                        response_text=e.response.text)
            raise Exception(f"USDA API error: {e.response.status_code}")
        except Exception as e:
            logger.error("usda_api_request_failed", 
                        endpoint=endpoint, 
                        error=str(e))
            raise
    
    async def search_foods(self, 
                          query: str,
                          data_type: Optional[List[str]] = None,
                          page_size: int = 25,
                          page_number: int = 1) -> Dict[str, Any]:
        """Search for foods in the USDA database"""
        
        search_data = {
            "query": query,
            "pageSize": min(page_size, 200),
            "pageNumber": page_number,
        }
        
        if data_type:
            search_data["dataType"] = data_type
        
        logger.info("usda_search_foods", query=query, page_size=page_size)
        
        return await self._make_request("POST", "/foods/search", json=search_data)
    
    async def get_food_details(self, 
                              fdc_id: int, 
                              format: str = "abridged") -> Dict[str, Any]:
        """Get detailed information for a specific food"""
        
        logger.info("usda_get_food_details", fdc_id=fdc_id, format=format)
        
        params = {"format": format} if format else {}
        return await self._make_request("GET", f"/food/{fdc_id}", params=params)
    
    async def get_multiple_foods(self, 
                                fdc_ids: List[int], 
                                format: str = "abridged") -> List[Dict[str, Any]]:
        """Get details for multiple foods"""
        
        if len(fdc_ids) > 20:
            raise ValueError("Maximum 20 foods can be requested at once")
        
        logger.info("usda_get_multiple_foods", fdc_ids=fdc_ids, count=len(fdc_ids))
        
        request_data = {
            "fdcIds": fdc_ids,
            "format": format
        }
        
        return await self._make_request("POST", "/foods", json=request_data)

