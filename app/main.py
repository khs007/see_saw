from fastapi import FastAPI
from app.query import query_router
from contextlib import asynccontextmanager

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Finance DB (creates indexes once)
    print("[Startup] Initializing Finance Database...")
    from db_.neo4j_finance import get_finance_db
    from retrieval.kg_retrieval import kg_conn
    
    try:
        # This will create indexes on first call
        finance_db = get_finance_db(kg_conn)
        print("[Startup] ✅ Finance DB initialized")
    except Exception as e:
        print(f"[Startup] ⚠️ Finance DB initialization failed: {e}")
    
    # Initialize Scam Detector (optional, will auto-initialize on first use)
    try:
        from scam_detector.scam_detector import get_scam_detector
        detector = get_scam_detector()
        print("[Startup] ✅ Scam Detector initialized")
    except Exception as e:
        print(f"[Startup] ⚠️ Scam Detector initialization failed: {e}")
    
    yield
 
app = FastAPI(lifespan=lifespan)

app.include_router(query_router)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "FinGuard",
        "features": [
            "government_schemes",
            "finance_tracking",
            "scam_detection"
        ]
    }

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # for demo only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)