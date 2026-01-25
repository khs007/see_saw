
from fastapi import FastAPI
from app.query import query_router

app=FastAPI()

app.include_router(query_router)
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "FinGuard"
    }

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # for demo only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
