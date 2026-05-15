#!/usr/bin/env python
"""
Test script to verify iteration, tool call, and token usage tracking.
Run with: python test_tracking.py
"""
import os
import sys
import django
import json

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from research_sessions.services import ResearchService
from research_sessions.models import ResearchSession, ToolCall


def test_tracking():
    """Test that tracking metrics are properly recorded"""
    print("="*70)
    print("Testing Tracking: Iterations, Tool Calls, and Token Usage")
    print("="*70)
    
    # Use a small local repository for testing
    test_repo = "https://github.com/Fahad0907/django-htmx.git"
    test_question = "What Python version is required?"
    
    print(f"\nStarting research session...")
    print(f"  Repository: {test_repo}")
    print(f"  Question: {test_question}")
    print(f"\nProcessing...")
    
    try:
        # Run the research
        result = ResearchService.start_research(test_repo, test_question)
        
        session_id = result['session_id']
        print(f"\n✓ Session completed: ID={session_id}")
        
        # Check the metrics in the response
        metadata = result['metadata']
        print(f"\nMetrics from API response:")
        print(f"  - Total Iterations: {metadata['total_iterations']}")
        print(f"  - Total Tool Calls: {metadata['total_tool_calls']}")
        print(f"  - Token Usage: {metadata['token_usage']}")
        print(f"  - Created At: {metadata['created_at']}")
        print(f"  - Completed At: {metadata['completed_at']}")
        
        # Verify by checking database directly
        session = ResearchSession.objects.get(id=session_id)
        tool_calls = ToolCall.objects.filter(session_id=session_id)
        
        print(f"\nVerifying against database:")
        print(f"  - Session.total_iterations: {session.total_iterations}")
        print(f"  - Session.total_tool_calls: {session.total_tool_calls}")
        print(f"  - Session.token_usage: {session.token_usage}")
        print(f"  - Actual ToolCall records in DB: {tool_calls.count()}")
        
        # Show tool calls
        if tool_calls.count() > 0:
            print(f"\nTool calls recorded:")
            for tc in tool_calls[:10]:  # Show first 10
                print(f"  - {tc.tool_name} (Iteration {tc.iteration})")
            if tool_calls.count() > 10:
                print(f"  ... and {tool_calls.count() - 10} more")
        
        # Verify tracking is working
        print(f"\nValidation:")
        checks = [
            ("Iterations tracked", session.total_iterations > 0),
            ("Tool calls tracked", session.total_tool_calls > 0),
            ("Tool call records exist", tool_calls.count() > 0),
            ("API response matches DB", metadata['total_tool_calls'] == tool_calls.count()),
        ]
        
        all_pass = True
        for check_name, result in checks:
            status_icon = "✓" if result else "❌"
            print(f"  {status_icon} {check_name}: {result}")
            if not result:
                all_pass = False
        
        print("\n" + "="*70)
        if all_pass:
            print("✓ ALL TRACKING TESTS PASSED!")
            print("="*70)
            return True
        else:
            print("❌ SOME TRACKING TESTS FAILED!")
            print("="*70)
            return False
    
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = test_tracking()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
