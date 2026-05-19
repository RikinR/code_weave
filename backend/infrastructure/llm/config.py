import os
from dotenv import load_dotenv
from infrastructure.logging.logger import get_logger

load_dotenv()

logger = get_logger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY is not set — RAG answers will fail until configured")
