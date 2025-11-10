# test_env_config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Test loading environment variables
print("Testing .env configuration...")
print("=" * 60)

# Check Claude API
claude_key = os.getenv('CLAUDE_API_KEY')
if claude_key:
    print(f"✓ Claude API Key loaded: {claude_key[:20]}...")
else:
    print("✗ Claude API Key not found")

# Check PubMed config
pubmed_email = os.getenv('PUBMED_EMAIL')
pubmed_key = os.getenv('PUBMED_API_KEY')

if pubmed_email:
    print(f"✓ PubMed Email loaded: {pubmed_email}")
else:
    print("✗ PubMed Email not found")

if pubmed_key:
    print(f"✓ PubMed API Key loaded: {pubmed_key[:10]}...")
else:
    print("✗ PubMed API Key not found")

# Check DB config (if you have it)
db_name = os.getenv('DB_NAME')
if db_name:
    print(f"✓ Database configured: {db_name}")
else:
    print("✗ Database not configured")

print("=" * 60)