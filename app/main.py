from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.query import query_router
from contextlib import asynccontextmanager
import os
import sys
from app.upi_api import upi_router

# Startup/shutdown lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize services on startup, cleanup on shutdown
    """
    print("\n" + "="*60)
    print("🚀 FINGUARD STARTUP")
    print("="*60)
    
    print("\n[Phase 1] Validating environment variables...")
    
    required_vars = [
        "GROQ_API_KEY",
        "GOOGLE_API_KEY", 
        "NEO4J_URI",
        "NEO4J_USERNAME",
        "NEO4J_PASSWORD",
        "NEO4J_URI2",
        "NEO4J_USERNAME2", 
        "NEO4J_PASSWORD2"
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"❌ FATAL: Missing environment variables: {missing}")
        print("💡 Add these in Render Dashboard → Environment → Environment Variables")
        sys.exit(1)
    
    print("✅ All required environment variables present")
    
    print("\n[Phase 2] Initializing Finance Database...")
    
    try:
        from db_.neo4j_finance import get_finance_db
        finance_db = get_finance_db()
        
        if not finance_db.verify_connection():
            raise Exception("Finance DB connection failed")
        
        print("✅ Finance Database ready")
        
    except Exception as e:
        print(f"❌ Finance DB initialization failed: {e}")
        print("⚠️  Finance features will be unavailable")
   
    print("\n[Phase 3] Initializing Scam Detector...")
    
    try:
        from scam_detector.scam_detector import get_scam_detector
        detector = get_scam_detector()
        print("✅ Scam Detector ready")
    except Exception as e:
        print(f"⚠️  Scam Detector initialization failed: {e}")

    # ✅ FIX: Don't initialize KG at startup - do it lazily
    print("\n[Phase 4] Knowledge Graph...")
    print("✅ Will initialize on first query (lazy loading)")
    print("ℹ️  This avoids blocking startup")

    print("\n" + "="*60)
    print("✅ FINGUARD READY TO SERVE")
    print("="*60 + "\n")
    
    yield

    print("\n🛑 Shutting down FinGuard...")
    print("✅ Cleanup complete\n")


# Create FastAPI app
app = FastAPI(
    title="FinGuard API",
    description="AI-powered financial assistant for Indian users",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(query_router)
app.include_router(upi_router)  

# Include email router
try:
    from app.email_api import email_router
    app.include_router(email_router)
    print("[Main] ✅ Email API loaded")
except ImportError as e:
    print(f"[Main] ⚠️ Email API not available: {e}")

# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint for Render"""
    return {
        "status": "healthy",
        "service": "FinGuard",
        "version": "1.0.0",
        "features": {
            "government_schemes": True,
            "finance_tracking": True,
            "scam_detection": True,
            "concept_explanation": True,
            "email_scam_detection": True
        }
    }

# Root endpoint
@app.get("/")
def root():
    """Root endpoint - API documentation"""
    return {
        "message": "Welcome to FinGuard API",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0"
    }