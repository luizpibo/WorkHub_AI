"""FastAPI application entry point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.core.config import settings
from app.utils.logger import logger

# Import routers
from app.api.v1 import chat, analytics, users, plans

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Sistema de vendas com IA para espaços de coworking",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info(f"Starting {settings.APP_NAME}")
    logger.info(f"Environment: {settings.APP_ENV}")
    
    # Run database migrations first
    try:
        from app.core.migrations import run_migrations
        
        migration_success = await run_migrations()
        if not migration_success:
            logger.warning("Migrations failed, but application will continue")
    except Exception as e:
        logger.error(f"Error running migrations: {e}", exc_info=True)
        logger.warning("Application will continue without running migrations")
    
    # Auto-seed database if enabled and not already seeded
    if settings.AUTO_SEED:
        try:
            from app.core.seed import check_if_seeded, run_seed
            
            logger.info("Checking if database needs seeding...")
            is_seeded = await check_if_seeded()
            
            if not is_seeded:
                logger.info("Database not seeded. Running automatic seed...")
                await run_seed()
                logger.info("✅ Database automatically seeded on startup")
            else:
                logger.info("✅ Database already seeded, skipping auto-seed")
        except Exception as e:
            logger.error(f"Error during auto-seed: {e}", exc_info=True)
            logger.warning("Application will continue without seed data")
    else:
        logger.info("Auto-seed is disabled (AUTO_SEED=false)")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info(f"Shutting down {settings.APP_NAME}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "WorkHub AI Sales System",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Include routers
app.include_router(chat.router, prefix=settings.API_V1_PREFIX, tags=["chat"])
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX, tags=["analytics"])
app.include_router(users.router, prefix=settings.API_V1_PREFIX, tags=["users"])
app.include_router(plans.router, prefix=settings.API_V1_PREFIX, tags=["plans"])

# Serve static files for frontend
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")
    
    @app.get("/chat")
    async def chat_page():
        """Serve the chat frontend page"""
        index_path = frontend_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"error": "Frontend not found"}
