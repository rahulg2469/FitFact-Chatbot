from anthropic import Anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.environ.get("CLAUDE_API_KEY"))

try:
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=2048,
        messages=[{"role": "user", "content": "Say hello"}]
    )
    print("✅ API Key Works!")
    print(f"Response: {message.content[0].text}")
except Exception as e:
    print(f"❌ API Key Failed: {e}")