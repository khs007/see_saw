from feature_router.router import router_feature
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

query_router = APIRouter()


class QueryRequest(BaseModel):
    """Request model for query endpoint"""
    query: str
    user_id: Optional[str] = "default_user"


class QueryResponse(BaseModel):
    """Response model for query endpoint"""
    answer: str
    type: str
    user_profile: Optional[dict] = None
    target_scope: Optional[str] = None
    transaction: Optional[dict] = None
    alert: Optional[str] = None


@query_router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    """
    Main query endpoint for FinGuard.
    Routes to appropriate handler based on query content.
    
    Args:
        request: QueryRequest with query text and user_id
        
    Returns:
        QueryResponse with answer and metadata
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        response = router_feature({
            "query": request.query,
            "user_id": request.user_id
        })
        return QueryResponse(**response)
        
    except Exception as e:
        print(f"[QueryEndpoint] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )