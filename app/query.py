from feature_router.router import router_feature
from fastapi import APIRouter

query_router = APIRouter()

@query_router.post("/query")
def query(req):
    
    return router_feature(req)      