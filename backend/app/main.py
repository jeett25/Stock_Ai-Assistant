"""
Main FastAPI application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.api import health, news, prices, ingestion ,analysis , chat

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
    description="""
    Stock Market AI Assistant API
    
    ## Features
    * Fetch news articles from multiple sources
    * Get historical stock prices
    * Trigger data ingestion
    * Health checks and monitoring
    
    **⚠️ Disclaimer**: This is for educational purposes only. Not financial advice.
    """
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📊 Debug mode: {settings.DEBUG}")
    logger.info(f"📚 API docs available at: /docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("👋 Shutting down application...")


# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(news.router, prefix="/api", tags=["News"])
app.include_router(prices.router, prefix="/api", tags=["Prices"])
app.include_router(ingestion.router, prefix="/api", tags=["Ingestion"])
app.include_router(analysis.router, prefix="/api", tags=["Analysis"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    API root endpoint with service information.
    """
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "health": "/api/health",
            "news": "/api/news/{ticker}",
            "prices": "/api/prices/{ticker}",
            "ingestion": "/api/ingest/{ticker}"
        },
        "disclaimer": "⚠️ For educational purposes only. Not financial advice."
    }