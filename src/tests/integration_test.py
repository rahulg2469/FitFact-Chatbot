"""
Integration Testing - Complete Pipeline Tests
Week 4
Tests 20+ different fitness questions through the complete system
"""

import sys
sys.path.append('src/llm')
sys.path.append('database_files')
from query_processor import QueryProcessor
import time

# 20+ Test Questions covering various fitness topics
TEST_QUESTIONS = [
    # Creatine questions
    "What are the benefits of creatine for muscle growth?",
    "Is creatine safe for long-term use?",
    "How much creatine should I take daily?",
    
    # Protein questions
    "How much protein do I need to build muscle?",
    "Is whey protein better than plant protein?",
    "When should I consume protein after workout?",
    
    # Resistance training questions
    "How often should I train each muscle group?",
    "What's better for hypertrophy: high reps or heavy weight?",
    "How long should rest periods be between sets?",
    
    # Cardio questions
    "Is HIIT better than steady-state cardio?",
    "How does cardio affect muscle growth?",
    "What's the best cardio for fat loss?",
    
    # Recovery questions
    "How important is sleep for muscle recovery?",
    "What should I eat after a workout?",
    "How long should I rest between workouts?",
    
    # Supplements questions
    "Do I need supplements to build muscle?",
    "What are the best supplements for beginners?",
    
    # Training questions
    "Should beginners do full body or split workouts?",
    "How long does it take to see muscle growth?",
    "Can I build muscle and lose fat at the same time?",
    
    # Edge cases
    "What is the best exercise?",  # Vague
    "Tell me about fitness",  # Very broad
    "Should I eat pizza before gym?"  # Silly question
]

def run_integration_tests():
    """Run all test questions through the system"""
    
    print("\n" + "="*70)
    print("INTEGRATION TESTING - 20+ FITNESS QUESTIONS")
    print("="*70)
    
    processor = QueryProcessor()
    
    results = []
    successful = 0
    failed = 0
    no_papers = 0
    
    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}/{len(TEST_QUESTIONS)}")
        print(f"{'='*70}")
        print(f"Question: {question}\n")
        
        start_time = time.time()
        
        try:
            response = processor.process_query(question)
            response_time = time.time() - start_time
            
            # Check if successful
            if "couldn't find relevant" in response:
                status = "NO_PAPERS"
                no_papers += 1
            elif "Error:" in response:
                status = "ERROR"
                failed += 1
            else:
                status = "SUCCESS"
                successful += 1
            
            results.append({
                'question': question,
                'status': status,
                'response_time': response_time,
                'response_length': len(response)
            })
            
            print(f"\nStatus: {status}")
            print(f"Response time: {response_time:.2f}s")
            print(f"Response length: {len(response)} chars")
            
            # Show first 200 chars of response
            print(f"\nResponse preview:")
            print(response[:200] + "...")
            
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            failed += 1
            results.append({
                'question': question,
                'status': 'EXCEPTION',
                'response_time': 0,
                'error': str(e)
            })
        
        # Small delay between tests
        time.sleep(0.5)
    
    # Summary Report
    print("\n" + "="*70)
    print("INTEGRATION TEST SUMMARY")
    print("="*70)
    print(f"Total questions tested: {len(TEST_QUESTIONS)}")
    print(f"✓ Successful responses: {successful}")
    print(f"⚠ No papers found: {no_papers}")
    print(f"✗ Failed/Errors: {failed}")
    print(f"Success rate: {(successful/len(TEST_QUESTIONS)*100):.1f}%")
    print("="*70)
    
    # Detailed results
    print("\nDETAILED RESULTS:")
    print("-"*70)
    for i, result in enumerate(results, 1):
        status_symbol = "✓" if result['status'] == "SUCCESS" else "✗" if result['status'] == "ERROR" else "⚠"
        print(f"{i:2d}. {status_symbol} {result['status']:12s} | {result['response_time']:5.2f}s | {result['question']}")
    
    processor.close()
    
    return results

if __name__ == "__main__":
    results = run_integration_tests()
    
    # Save results to file
    import json
    with open('test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n✓ Test results saved to test_results.json")