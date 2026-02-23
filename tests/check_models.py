import os
import logging
from typing import cast
from google import genai

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    logger.error("❌ API Key not found! Run 'export GEMINI_API_KEY=...' first.")
else:
    logger.info(f"🔑 Key found: {api_key[:5]}...{api_key[-3:]}")

    try:
        client = genai.Client(api_key=api_key)
        logger.info("\n📡 Connecting to Google AI...")

        # New SDK list call
        response = client.models.list()

        logger.info("\n✅ AVAILABLE MODELS:")
        found_flash = False

        # Loop through models and logger.info names safely
        if response:
            for m in response:
                # Check for 'generateContent' capability using the new attribute name
                # Some versions use 'supported_actions', others just let us check the name
                actions = cast(list[str], getattr(m, "supported_actions", [])) or cast(
                    list[str], getattr(m, "supported_generation_methods", [])
                )

                if "generateContent" in actions or not actions:
                    model_name = cast(str, getattr(m, "name", str(m)))
                    logger.info(f" - {model_name}")
                    if model_name and "flash" in model_name and "1.5" in model_name:
                        found_flash = True

        if not found_flash:
            logger.warning("\n⚠️ WARNING: No 'gemini-1.5-flash' alias found.")
            logger.info("👉 Try using one of the exact names listed above (e.g. 'gemini-1.5-flash-001').")

    except Exception as e:
        logger.error(f"\n❌ CONNECTION ERROR: {e}")
