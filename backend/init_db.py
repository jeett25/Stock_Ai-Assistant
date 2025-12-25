"""
Run this once to create all tables.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from app.core.database import init_db, engine
from app.models import stock, news  # Import to register models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Create all database tables."""
    logger.info("Starting database initialization...")
    
    try:
        # This will create all tables defined in Base subclasses
        init_db()
        logger.info("✅ Database initialized successfully!")
        
        # Verify tables were created
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"Created tables: {', '.join(tables)}")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()