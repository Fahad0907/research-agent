#!/usr/bin/env python
"""
Test that token usage is now properly tracked with Ollama token estimation.
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from research_sessions.models import ResearchSession, ToolCall
from repositories.models import Repository
from agent.llm_client import get_llm_client


def test_token_tracking():
    print("="*80)
    print("TESTING TOKEN USAGE TRACKING WITH OLLAMA ESTIMATION")
    print("="*80)
    
    # Test 1: Token estimation from response
    print("\n1. Testing token estimation from simulated Ollama response...")
    
    client = get_llm_client()
    
    # Simulate responses of different lengths
    test_responses = [
        ("Short response", "This is short."),  # ~3 chars / 4 = ~1 token
        ("Medium response", "This is a medium length response with some additional content to make it longer."),  # ~82 chars / 4 = ~20 tokens
        ("Long response", "This is a much longer response that contains a lot of text content. We need to test that token estimation scales properly with longer responses. The more characters, the more tokens we estimate."),  # ~197 chars / 4 = ~49 tokens
    ]
    
    for desc, text in test_responses:
        response = {
            'content': [{'type': 'text', 'text': text}],
            'usage': {'input_tokens': 0, 'output_tokens': 0}
        }
        tokens = client.count_tokens(response)
        print(f"   {desc}: {len(text)} chars → {tokens} tokens")
    
    # Test 2: Session tracking with estimated tokens
    print("\n2. Testing token tracking in a session...")
    
    repo, _ = Repository.objects.get_or_create(
        name="token-test-repo",
        defaults={"url": "https://github.com/test/token-test"}
    )
    
    session = ResearchSession.objects.create(
        repository=repo,
        question="Token tracking test",
        status="pending"
    )
    print(f"   Created session {session.id}")
    
    # Simulate adding tokens from multiple LLM calls
    print("\n3. Simulating multiple LLM calls with token estimation...")
    
    estimated_tokens = []
    for i in range(5):
        # Simulate different response lengths
        response_length = 50 + (i * 30)  # Increasing length
        response = {
            'content': [{'type': 'text', 'text': 'x' * response_length}],
            'usage': {'input_tokens': 0, 'output_tokens': 0}
        }
        tokens = client.count_tokens(response)
        estimated_tokens.append(tokens)
        session.add_token_usage(tokens)
        print(f"   LLM Call {i+1}: {response_length} chars → {tokens} tokens (session total: {session.token_usage})")
    
    # Verify
    print("\n4. Validation...")
    expected_total = sum(estimated_tokens)
    
    session.refresh_from_db()
    actual_total = session.token_usage
    
    print(f"   Expected total tokens: {expected_total}")
    print(f"   Actual total tokens: {actual_total}")
    print(f"   Match: {'✓' if expected_total == actual_total else '❌'}")
    
    # Final check
    print("\n5. Verification against database...")
    db_session = ResearchSession.objects.get(id=session.id)
    print(f"   Database token_usage: {db_session.token_usage}")
    print(f"   Tokens tracked: {'✓ YES' if db_session.token_usage > 0 else '❌ NO'}")
    
    # Cleanup
    session.delete()
    repo.delete()
    
    print("\n" + "="*80)
    if actual_total == expected_total and db_session.token_usage > 0:
        print("✓✓✓ TOKEN USAGE TRACKING WORKING CORRECTLY ✓✓✓")
        print("="*80)
        print("\nToken estimation formula: 1 token per 4 characters (minimum 1)")
        print("Ollama responses will now show non-zero token_usage!")
        return True
    else:
        print("❌ TOKEN TRACKING ISSUE DETECTED")
        print("="*80)
        return False


if __name__ == "__main__":
    try:
        success = test_token_tracking()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
