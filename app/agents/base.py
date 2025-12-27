"""Base agent configuration"""
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
from app.utils.logger import logger


def get_llm(temperature: float = 0.7):
    """
    Get configured LLM instance with retry and timeout.
    Supports both OpenAI and Google Gemini providers.
    
    Args:
        temperature: Temperature for generation (0-1)
    
    Returns:
        LLM instance (ChatOpenAI or ChatGoogleGenerativeAI)
    """
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "google":
        if not settings.GOOGLE_API_KEY:
            logger.warning("Google API Key not found, checking OpenAI...")
        else:
            logger.info(f"Using Google Gemini model: {settings.GOOGLE_MODEL}")
            return ChatGoogleGenerativeAI(
                model=settings.GOOGLE_MODEL,
                temperature=temperature,
                google_api_key=settings.GOOGLE_API_KEY,
                max_retries=3,
            )
            
    # Default to OpenAI
    logger.info(f"Using OpenAI model: {settings.OPENAI_MODEL}")
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=temperature,
        openai_api_key=settings.OPENAI_API_KEY,
        max_retries=3,
        request_timeout=60,
        max_tokens=2000,
    )

