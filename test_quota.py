import os
from google import genai

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

models_to_test = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite-001"
]

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
