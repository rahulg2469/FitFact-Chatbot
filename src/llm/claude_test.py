"""
Test Claude API connection
Elenta Suzan Jacob
"""

import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

def test_claude_api():
    """Test basic Claude API call"""
    
    # Initialize client
    client = anthropic.Anthropic(
        api_key=os.getenv('CLAUDE_API_KEY')
    )
    
    # Test question
    question = "What are the benefits of creatine supplementation for muscle growth? Keep it brief."
    
    print("=" * 60)
    print("Claude API Test")
    print("=" * 60)
    print(f"\nQuestion: {question}\n")
    
    try:
        # Make API call
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": question
                }
            ]
        )
        
        # Extract response
        response = message.content[0].text
        
        print("Claude's Response:")
        print("-" * 60)
        print(response)
        print("-" * 60)
        print(f"\nTokens used: {message.usage.input_tokens} input, {message.usage.output_tokens} output")
        print("\n✓ Claude API is working!")
        
        return response
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("Check your CLAUDE_API_KEY in .env file")
        return None

if __name__ == "__main__":
    test_claude_api()