from pydantic import BaseModel
from typing import Any, Dict, Optional, Union


class QueryRequest(BaseModel):
    """Request model for the /ask endpoint."""
    query: str


class SignInRequest(BaseModel):
    """Request model for the /authenticate endpoint."""
    email: str
    password: str
    display_name: Optional[str] = None


class APIResponse(BaseModel):
    """Standard API response model."""
    message: Any
    status_code: int
    error: bool = False 