"""
Research Service Layer
Handles business logic for research sessions.
"""
from typing import Dict, Any
from django.utils import timezone
from repositories.models import Repository
from research_sessions.models import ResearchSession
from agent.repo_loader import get_repo_loader
from agent.core import CodebaseResearchAgent


class ResearchService:
    """
    Service for managing research sessions.
    """
    
    @staticmethod
    def start_research(repo_url: str, question: str) -> Dict[str, Any]:
        """
        Start a new research session.
        
        Args:
            repo_url: GitHub repository URL
            question: Research question
            
        Returns:
            Dict with session info and answer
        """
        # Get or create repository
        repo_loader = get_repo_loader()
        
        # Extract repo name from URL
        repo_name = repo_url.rstrip('/').split('/')[-1]
        
        # Get or create repository record
        repository, created = Repository.objects.get_or_create(
            url=repo_url,
            defaults={'name': repo_name}
        )
        
        # Clone/update repository
        try:
            local_path = repo_loader.get_or_clone(repo_url)
            repository.local_path = local_path
            repository.update_last_analyzed()
        except Exception as e:
            raise Exception(f"Failed to load repository: {str(e)}")
        
        # Create research session
        session = ResearchSession.objects.create(
            repository=repository,
            question=question,
            status='pending'
        )
        
        repository.increment_session_count()
        
        # Run agent
        try:
            agent = CodebaseResearchAgent(
                session_id=session.id,
                repo_local_path=local_path
            )
            
            final_answer = agent.research(question)
            
            # Refresh session from DB to get updated counts
            session.refresh_from_db()
            
            return {
                'session_id': session.id,
                'status': 'completed',
                'question': question,
                'answer': final_answer,
                'repository': {
                    'name': repository.name,
                    'url': repository.url
                },
                'metadata': {
                    'total_iterations': session.total_iterations,
                    'total_tool_calls': session.tool_calls.count(),  # Count actual DB records
                    'token_usage': session.token_usage or 0,  # Show 0 if None
                    'created_at': session.created_at.isoformat(),
                    'completed_at': session.completed_at.isoformat() if session.completed_at else None
                }
            }
            
        except Exception as e:
            session.mark_failed(str(e))
            raise
    
    @staticmethod
    def get_session_details(session_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a research session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Dict with session details including tool calls and findings
        """
        try:
            session = ResearchSession.objects.select_related('repository').get(id=session_id)
        except ResearchSession.DoesNotExist:
            raise ValueError(f"Session {session_id} not found")
        
        # Get tool calls
        tool_calls = list(session.tool_calls.all().order_by('created_at').values(
            'tool_name', 'tool_input', 'tool_output', 'iteration', 
            'execution_time_ms', 'created_at'
        ))
        
        # Get findings
        findings = list(session.findings.all().order_by('-relevance_score').values(
            'file_path', 'line_start', 'line_end', 'note', 'relevance_score'
        ))
        
        # Get referenced files (from tool calls)
        referenced_files = set()
        for tc in tool_calls:
            if tc['tool_name'] == 'read_file':
                referenced_files.add(tc['tool_input'].get('file_path'))
            elif tc['tool_name'] == 'save_finding':
                referenced_files.add(tc['tool_input'].get('file_path'))
        
        return {
            'session_id': session.id,
            'status': session.status,
            'question': session.question,
            'answer': session.final_answer,
            'repository': {
                'id': session.repository.id,
                'name': session.repository.name,
                'url': session.repository.url
            },
            'metadata': {
                'total_iterations': session.total_iterations,
                'total_tool_calls': len(tool_calls),  # Use actual count from query
                'token_usage': session.token_usage or 0,
                'created_at': session.created_at.isoformat(),
                'started_at': session.started_at.isoformat() if session.started_at else None,
                'completed_at': session.completed_at.isoformat() if session.completed_at else None
            },
            'tool_calls': tool_calls,
            'findings': findings,
            'referenced_files': list(referenced_files),
            'error_message': session.error_message
        }
    
    @staticmethod
    def list_repository_sessions(repo_url: str) -> Dict[str, Any]:
        """
        List all sessions for a repository.
        
        Args:
            repo_url: Repository URL
            
        Returns:
            Dict with repository info and sessions list
        """
        try:
            repository = Repository.objects.get(url=repo_url)
        except Repository.DoesNotExist:
            return {
                'repository': None,
                'sessions': []
            }
        
        sessions = list(repository.sessions.all().order_by('-created_at').values(
            'id', 'question', 'status', 'created_at', 'completed_at',
            'total_iterations', 'total_tool_calls', 'token_usage'
        ))
        
        return {
            'repository': {
                'id': repository.id,
                'name': repository.name,
                'url': repository.url,
                'total_sessions': repository.total_sessions,
                'last_analyzed': repository.last_analyzed.isoformat()
            },
            'sessions': sessions
        }