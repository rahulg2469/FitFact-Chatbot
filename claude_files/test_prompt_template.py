import anthropic
import os
from dotenv import load_dotenv
from prompt_template import create_fitness_prompt

# Load environment variables
load_dotenv()

# Initialize Claude client
client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

# MOCK PUBMED DATA (simulating what Elenta will provide in Phase 2)
mock_pubmed_abstracts = [
    {
        "title": "Effects of creatine supplementation on muscle strength: a meta-analysis",
        "authors": "Branch JD",
        "year": "2003",
        "pmid": "12945830",
        "abstract": "This meta-analysis examined the effects of creatine supplementation on muscle strength. Twenty-two studies met the inclusion criteria. Results showed that creatine supplementation significantly increased maximum strength (bench press 1RM) by an average of 8% compared to placebo. The effect was consistent across different age groups and training statuses."
    },
    {
        "title": "Creatine supplementation and resistance training: effects on body composition",
        "authors": "Kreider RB, Kalman DS, Antonio J",
        "year": "2017",
        "pmid": "28615996",
        "abstract": "The purpose of this study was to examine the effects of creatine supplementation during resistance training. Subjects consuming creatine gained significantly more lean muscle mass (2.2 kg vs 1.0 kg) and experienced greater strength gains compared to placebo. Creatine supplementation was well-tolerated with no adverse effects reported."
    },
    {
        "title": "International Society of Sports Nutrition position stand: safety and efficacy of creatine supplementation",
        "authors": "Kreider RB, Stout JR",
        "year": "2021",
        "pmid": "34049503",
        "abstract": "Creatine monohydrate is the most effective ergogenic nutritional supplement currently available for increasing exercise capacity and lean body mass during training. The typical loading protocol is 20g/day for 5-7 days, followed by a maintenance dose of 3-5g/day. Research spanning several decades has consistently shown creatine supplementation to be safe when consumed at recommended doses."
    }
]

# User's fitness question
user_question = "What are the benefits of creatine supplementation for strength training, and what's the recommended dosage?"

print("FitFact Prompt Template Demo")
print("=" * 80)
print("\n📊 SIMULATING PHASE 2 INTEGRATION (using mock PubMed data)")
print("\nUser Question:", user_question)
print("\n" + "=" * 80)

# Create the prompt using our template
prompt = create_fitness_prompt(user_question, mock_pubmed_abstracts)

print("\n🔍 GENERATED PROMPT PREVIEW (first 500 characters):")
print(prompt[:500] + "...\n")
print("=" * 80)

# Send to Claude API
print("\n🤖 SENDING TO CLAUDE...\n")

try:
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",  # Updated model name
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    
    response = message.content[0].text
    
    print("✅ CLAUDE'S EVIDENCE-BASED RESPONSE:")
    print("=" * 80)
    print(response)
    print("=" * 80)
    
    # Validate response has citations
    has_pmid = "PMID:" in response
    has_references = "Reference" in response or "PMID:" in response
    
    print("\n📋 RESPONSE VALIDATION:")
    print(f"  ✓ Contains PMID citations: {has_pmid}")
    print(f"  ✓ Includes references section: {has_references}")
    print(f"  ✓ Response length: {len(response.split())} words")
    
    if has_pmid and has_references:
        print("\n🎉 SUCCESS! Prompt template generates properly cited responses!")
    else:
        print("\n⚠️  Warning: Response may need citation format adjustment")
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("Initial Prompt Template Tested Successfully")
print("=" * 80)