import os

from google import genai

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("❌ API Key not found! Run 'export GEMINI_API_KEY=...' first.")
else:
    print(f"🔑 Key found: {api_key[:5]}...{api_key[-3:]}")

    try:
        client = genai.Client(api_key=api_key)
        print("\n📡 Connecting to Google AI...")

        # New SDK list call
        response = client.models.list()

        print("\n✅ AVAILABLE MODELS:")
        found_flash = False

        # Loop through models and print names safely
        for m in response:
            # Check for 'generateContent' capability using the new attribute name
            # Some versions use 'supported_actions', others just let us check the name
            actions = getattr(m, 'supported_actions', []) or getattr(m, 'supported_generation_methods', [])

            if "generateContent" in actions or not actions:
                print(f" - {m.name}")
                if "flash" in m.name and "1.5" in m.name:
                    found_flash = True

        if not found_flash:
            print("\n⚠️ WARNING: No 'gemini-1.5-flash' alias found.")
            print("👉 Try using one of the exact names listed above (e.g. 'gemini-1.5-flash-001').")

    except Exception as e:
        print(f"\n❌ CONNECTION ERROR: {e}")
