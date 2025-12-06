"""
Pagination utilities for API endpoints
"""

from pydantic import BaseModel, Field
from typing import TypeVar, Generic, List, Optional
from fastapi import Query

T = TypeVar('T')


class PaginationParams:
    """
    Dependency for pagination parameters.

    Usage:
        @router.get("/items")
        async def get_items(pagination: PaginationParams = Depends()):
            skip = pagination.skip
            limit = pagination.limit
    """

    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return (max 100)")
    ):
        self.skip = skip
        self.limit = min(limit, 100)  # Enforce max limit


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.

    Provides metadata about the pagination state along with the data.
    """
    items: List[T]
    total: int = Field(..., description="Total number of items available")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum items per page")
    has_more: bool = Field(..., description="Whether there are more items available")

    class Config:
        from_attributes = True


def paginate_response(
    items: List[T],
    total: int,
    skip: int,
    limit: int
) -> dict:
    """
    Helper function to create a paginated response dict.

    Args:
        items: The list of items for current page
        total: Total count of all items
        skip: Number of items skipped
        limit: Maximum items per page

    Returns:
        Dictionary with pagination metadata
    """
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + len(items) < total
    }
