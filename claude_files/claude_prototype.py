import anthropic
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the Claude API client
client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

print("Testing Claude API connection...\n")

# Test 1: Simple connection test
try:
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",  # Updated to correct model name
        max_tokens=1024,
        messages=[
            {
                "role": "user", 
                "content": "Hello! Please respond with 'Connection successful' if you receive this."
            }
        ]
    )
    
    print("✓ Connection Test Passed!")
    print(f"Claude's response: {message.content[0].text}\n")
    
except Exception as e:
    print(f"✗ Connection Test Failed: {e}\n")
    exit(1)

# Test 2: Fitness-related query (relevant to FitFact)
print("Testing fitness-related query...\n")

try:
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",  # Updated model name
        max_tokens=1024,
        messages=[
            {
                "role": "user", 
                "content": "What are the benefits of creatine supplementation for strength training? Keep your answer brief (2-3 sentences)."
            }
        ]
    )
    
    print("✓ Fitness Query Test Passed!")
    print(f"Claude's response: {message.content[0].text}\n")
    
except Exception as e:
    print(f"✗ Fitness Query Test Failed: {e}\n")
    exit(1)

print("=" * 60)
print("All tests passed! Claude API integration successful!")
print("=" * 60)