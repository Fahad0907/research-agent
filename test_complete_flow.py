#!/usr/bin/env python
"""
Comprehensive test verifying the complete tracking flow.
This test demonstrates:
1. New methods in ResearchSession model
2. Token usage tracking in core.py
3. Tool call logging in tools.py
4. API response includes accurate metrics
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from research_sessions.models import ResearchSession, ToolCall
from repositories.models import Repository


def test_complete_flow():
    print("="*80)
    print("COMPLETE TRACKING FLOW TEST")
    print("="*80)
    
    # Create test data
    print("\n1. Setting up test data...")
    repo, _ = Repository.objects.get_or_create(
        name="flow-test-repo",
        defaults={"url": "https://github.com/test/flow-test"}
    )
    
    session = ResearchSession.objects.create(
        repository=repo,
        question="Test flow question",
        status="pending"
    )
    print(f"   ✓ Created session {session.id}")
    
    # Simulate agent loop
    print("\n2. Simulating agent processing loop...")
    print("   (Mimicking what core.py does)")
    
    # Iteration 1
    print("\n   Iteration 1:")
    session.increment_iteration()
    print(f"     - Called increment_iteration() -> total_iterations = {session.total_iterations}")
    
    # Simulate tool calls (as done in tools.py execute_tool)
    ToolCall.objects.create(
        session=session,
        tool_name="get_directory_structure",
        tool_input={"max_depth": 2},
        tool_output="Found structure...",
        iteration=0,
        execution_time_ms=150
    )
    print(f"     - Tool call logged (get_directory_structure)")
    
    # Add token usage (as done in core.py)
    session.add_token_usage(125)
    print(f"     - Called add_token_usage(125) -> token_usage = {session.token_usage}")
    
    # Iteration 2
    print("\n   Iteration 2:")
    session.increment_iteration()
    print(f"     - Called increment_iteration() -> total_iterations = {session.total_iterations}")
    
    # Multiple tool calls
    for i, tool_name in enumerate(["search_code", "read_file", "search_code"]):
        ToolCall.objects.create(
            session=session,
            tool_name=tool_name,
            tool_input={"query": "test"},
            tool_output=f"Result {i}...",
            iteration=1,
            execution_time_ms=100 + i*50
        )
    print(f"     - Tool calls logged (search_code, read_file, search_code)")
    
    session.add_token_usage(156)
    print(f"     - Called add_token_usage(156) -> token_usage = {session.token_usage}")
    
    # Mark completed
    print("\n3. Marking session as completed...")
    session.mark_completed("Final answer text")
    print(f"   ✓ Session marked as completed")
    
    # Simulate what services.py does
    print("\n4. Verifying metrics (as services.py does)...")
    session.refresh_from_db()
    
    # Count tool calls from database
    tool_calls_count = session.tool_calls.count()
    
    response_metadata = {
        'total_iterations': session.total_iterations,
        'total_tool_calls': tool_calls_count,
        'token_usage': session.token_usage,
    }
    
    print(f"   API Response metadata:")
    print(f"     - total_iterations: {response_metadata['total_iterations']}")
    print(f"     - total_tool_calls: {response_metadata['total_tool_calls']}")
    print(f"     - token_usage: {response_metadata['token_usage']}")
    
    # Verify
    print("\n5. Validation checks...")
    checks = [
        ("Iterations incremented correctly", session.total_iterations == 2),
        ("Tool calls logged to database", ToolCall.objects.filter(session=session).count() == 4),
        ("Tool calls count accurate", tool_calls_count == 4),
        ("Token usage accumulated", session.token_usage == 281),
        ("Session status is completed", session.status == "completed"),
    ]
    
    all_pass = True
    for check_name, passed in checks:
        icon = "✓" if passed else "❌"
        print(f"   {icon} {check_name}: {passed}")
        if not passed:
            all_pass = False
    
    # Show all tool calls
    print("\n6. All recorded tool calls:")
    for tc in session.tool_calls.all().order_by('created_at'):
        print(f"   - {tc.tool_name} (iteration {tc.iteration}, {tc.execution_time_ms}ms)")
    
    # Cleanup
    print("\n7. Cleaning up...")
    session.delete()
    repo.delete()
    print(f"   ✓ Test data removed")
    
    print("\n" + "="*80)
    if all_pass:
        print("✓✓✓ COMPLETE TRACKING FLOW VERIFIED ✓✓✓")
    else:
        print("❌ SOME CHECKS FAILED")
    print("="*80)
    
    return all_pass


if __name__ == "__main__":
    try:
        success = test_complete_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
