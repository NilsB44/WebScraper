import os

import pytest
from google import genai


@pytest.mark.skip(reason="Requires real API key")
def test_quota_check():
    api_key = os.environ.get("GEMINI_API_KEY", "dummy_key")
    client = genai.Client(api_key=api_key)

    models_to_test = ["gemini-2.0-flash", "gemini-2.0-flash-lite-001"]

    for model in models_to_test:
        print(f"Testing model: {model}")
        try:
            response = client.models.generate_content(
                model=model,
                contents="Say 'Hello'",
            )
            print(f"✅ {model} works: {response.text}")
        except Exception as e:
            print(f"❌ {model} failed: {e}")
        print("-" * 20)


if __name__ == "__main__":
    test_quota_check()
