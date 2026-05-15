#!/usr/bin/env python
"""
Quick test script to verify the agent setup is working.
Run with: python test_agent.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from research_sessions.services import ResearchService


def test_agent():
    print("="*70)
    print("Codebase Research Agent - Installation Test")
    print("="*70)
    
    # Test 1: Check environment
    print("\n1. Checking environment configuration...")
    from django.conf import settings
    
    if not settings.LLM_API_KEY:
        print("❌ FAILED: LLM_API_KEY not configured in .env file")
        print("   Please add your Anthropic API key to .env")
        return False
    
    print(f"✓ LLM API URL: {settings.LLM_API_URL}")
    print(f"✓ LLM Model: {settings.LLM_MODEL}")
    print(f"✓ Repository Storage: {settings.REPO_STORAGE_PATH}")
    
    # Test 2: Check database
    print("\n2. Checking database...")
    from repositories.models import Repository
    from research_sessions.models import ResearchSession
    
    repo_count = Repository.objects.count()
    session_count = ResearchSession.objects.count()
    
    print(f"✓ Database connected")
    print(f"  - Repositories: {repo_count}")
    print(f"  - Sessions: {session_count}")
    
    # Test 3: Test LLM client
    print("\n3. Testing LLM client connection...")
    try:
        from agent.llm_client import get_llm_client
        client = get_llm_client()
        
        # Simple test call
        response = client.chat_completion(
            messages=[{"role": "user", "content": "Say 'test successful' and nothing else"}],
            system="You are a test assistant."
        )
        
        text = client.extract_text_response(response)
        
        if "test" in text.lower():
            print("✓ LLM client working correctly")
        else:
            print("⚠ LLM client returned unexpected response")
            print(f"  Response: {text}")
    
    except Exception as e:
        print(f"❌ LLM client test failed: {str(e)}")
        return False
    
    # Test 4: Test repository loader
    print("\n4. Testing repository loader...")
    try:
        from agent.repo_loader import get_repo_loader
        loader = get_repo_loader()
        print("✓ Repository loader initialized")
    except Exception as e:
        print(f"❌ Repository loader test failed: {str(e)}")
        return False
    
    print("\n" + "="*70)
    print("✓ ALL TESTS PASSED - Agent is ready to use!")
    print("="*70)
    print("\nNext steps:")
    print("1. Start server: python manage.py runserver")
    print("2. Create sample data: python manage.py create_sample_data")
    print("3. Or test API manually with curl/Postman")
    print("\nAPI endpoint: POST http://localhost:8000/api/research/start/")
    
    return True


if __name__ == "__main__":
    try:
        success = test_agent()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
