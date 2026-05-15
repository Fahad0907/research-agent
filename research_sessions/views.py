"""
API Views
"""
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from research_sessions.services import ResearchService
from research_sessions.serializers import (
    StartResearchSerializer,
    SessionDetailSerializer,
    SessionListSerializer
)


@api_view(['POST'])
def start_research(request):
    """
    Start a new research session.
    
    POST /api/research/start/
    
    Body:
    {
        "repo_url": "https://github.com/user/repo",
        "question": "How does X work?"
    }
    
    Returns:
    {
        "session_id": 123,
        "status": "completed",
        "question": "...",
        "answer": "...",
        "repository": {...},
        "metadata": {...}
    }
    """
    serializer = StartResearchSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid input', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    repo_url = serializer.validated_data['repo_url']
    question = serializer.validated_data['question']
    
    try:
        result = ResearchService.start_research(repo_url, question)
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_session(request, session_id):
    """
    Get detailed information about a research session.
    
    GET /api/research/<session_id>/
    
    Returns:
    {
        "session_id": 123,
        "status": "completed",
        "question": "...",
        "answer": "...",
        "repository": {...},
        "metadata": {...},
        "tool_calls": [...],
        "findings": [...],
        "referenced_files": [...]
    }
    """
    try:
        result = ResearchService.get_session_details(session_id)
        return Response(result, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def list_repository_sessions(request):
    """
    List all research sessions for a repository.
    
    GET /api/repositories/sessions/?repo_url=https://github.com/user/repo
    
    Returns:
    {
        "repository": {...},
        "sessions": [...]
    }
    """
    repo_url = request.query_params.get('repo_url')
    
    if not repo_url:
        return Response(
            {'error': 'repo_url parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        result = ResearchService.list_repository_sessions(repo_url)
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
