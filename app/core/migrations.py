"""Database migration utilities"""
import asyncio
import os
import subprocess
import sys
from pathlib import Path
from app.core.config import settings
from app.utils.logger import logger


async def run_migrations() -> bool:
    """
    Run database migrations programmatically using Alembic.
    
    Returns:
        True if migrations were successful, False otherwise
    """
    try:
        logger.info("Running database migrations...")
        
        # Find project root (where alembic.ini should be)
        current_dir = Path(__file__).parent.parent.parent
        alembic_ini = current_dir / "alembic.ini"
        
        if not alembic_ini.exists():
            logger.error(f"alembic.ini not found at {alembic_ini}")
            return False
        
        # Run alembic upgrade head
        # Use asyncio to run subprocess in background
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m", "alembic",
            "upgrade", "head",
            cwd=str(current_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={
                **dict(os.environ),
                "DATABASE_URL": settings.DATABASE_URL,
            }
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"Migration failed: {error_msg}")
            return False
        
        output = stdout.decode() if stdout else ""
        if output:
            logger.debug(f"Migration output: {output}")
        
        logger.info("✅ Database migrations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error running migrations: {e}", exc_info=True)
        return False

