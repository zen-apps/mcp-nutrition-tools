"""
Request models for MCP tool parameters - Fixed for Pydantic v2
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class SearchParams(BaseModel):
    """Parameters for food search"""
    query: str = Field(..., description="Search term for foods", min_length=1)
    data_type: Optional[List[str]] = Field(None, description="Food data types to filter by")
    page_size: Optional[int] = Field(25, ge=1, le=200, description="Number of results")
    page_number: Optional[int] = Field(1, ge=1, description="Page number")

class FoodDetailParams(BaseModel):
    """Parameters for getting food details"""
    fdc_id: int = Field(..., description="USDA FoodData Central ID", gt=0)
    format: Optional[str] = Field("abridged", description="Response format", pattern="^(abridged|full)$")

class CompareFoodsParams(BaseModel):
    """Parameters for comparing multiple foods"""
    fdc_ids: List[int] = Field(..., description="List of FDC IDs to compare", min_length=2, max_length=5)


class AgentTestParams(BaseModel):
    """Parameters for agent integration demos"""
    agent_type: str = Field(..., description="Type of agent to demo", pattern="^(claude|openai|langchain)$")
    query: Optional[str] = Field(None, description="Nutrition query to test with")
    claude_api_key: Optional[str] = Field(None, description="Claude API key for live demo", min_length=10)
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key for live demo", min_length=10)