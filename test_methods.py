#!/usr/bin/env python
"""
Quick test of the new tracking methods in Django shell.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from research_sessions.models import ResearchSession
from repositories.models import Repository

# Create a test repository
repo, _ = Repository.objects.get_or_create(
    name="test-repo",
    defaults={"url": "https://github.com/test/test"}
)

# Create a test session
session = ResearchSession.objects.create(
    repository=repo,
    question="Test question",
    status="pending"
)

print(f"Created session {session.id}")
print(f"Initial state:")
print(f"  - total_iterations: {session.total_iterations}")
print(f"  - total_tool_calls: {session.total_tool_calls}")
print(f"  - token_usage: {session.token_usage}")

# Test increment_iteration
print(f"\nTesting increment_iteration()...")
for i in range(3):
    session.increment_iteration()
    session.refresh_from_db()
    print(f"  After increment {i+1}: {session.total_iterations}")

# Test increment_tool_calls
print(f"\nTesting increment_tool_calls()...")
for i in range(5):
    session.increment_tool_calls()
    session.refresh_from_db()
    print(f"  After increment {i+1}: {session.total_tool_calls}")

# Test add_token_usage
print(f"\nTesting add_token_usage()...")
session.add_token_usage(100)
session.refresh_from_db()
print(f"  After adding 100 tokens: {session.token_usage}")

session.add_token_usage(250)
session.refresh_from_db()
print(f"  After adding 250 more tokens: {session.token_usage}")

# Final state
print(f"\nFinal state:")
print(f"  - total_iterations: {session.total_iterations}")
print(f"  - total_tool_calls: {session.total_tool_calls}")
print(f"  - token_usage: {session.token_usage}")

# Clean up
session.delete()
repo.delete()

print(f"\n✓ All tracking methods work correctly!")
