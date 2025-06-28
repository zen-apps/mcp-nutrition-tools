"""
Response models for MCP server
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class MCPResponse(BaseModel):
    """Standard MCP response format"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    tool: Optional[str] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ToolInfo(BaseModel):
    """Information about an MCP tool"""
    name: str
    description: str
    input_schema: Dict[str, Any]
