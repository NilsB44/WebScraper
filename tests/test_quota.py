import os
import logging
import pytest
from google import genai

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

@pytest.mark.skip(reason="Requires real API key")
def test_quota_check() -> None:
    api_key = os.environ.get("GEMINI_API_KEY", "dummy_key")
    client = genai.Client(api_key=api_key)

    models_to_test = ["gemini-2.0-flash", "gemini-2.0-flash-lite-001"]

    for model in models_to_test:
        logger.info(f"Testing model: {model}")
        try:
            response = client.models.generate_content(
                model=model,
                contents="Say 'Hello'",
            )
            logger.info(f"✅ {model} works: {response.text}")
        except Exception as e:
            logger.error(f"❌ {model} failed: {e}")
        logger.info("-" * 20)


if __name__ == "__main__":
    test_quota_check()
