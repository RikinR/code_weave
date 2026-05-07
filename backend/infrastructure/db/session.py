from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infrastructure.db.config import DATABASE_URL
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

engine = create_engine(DATABASE_URL, echo=False)
logger.info("SQLAlchemy engine created (echo=False)")

SessionLocal = sessionmaker(autoflush=False, bind=engine)
