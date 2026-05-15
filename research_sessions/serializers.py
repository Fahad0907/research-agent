"""
API Serializers
"""
from rest_framework import serializers
from research_sessions.models import ResearchSession, ToolCall, Finding
from repositories.models import Repository


class StartResearchSerializer(serializers.Serializer):
    """Serializer for starting a new research session"""
    repo_url = serializers.URLField(required=True, max_length=500)
    question = serializers.CharField(required=True, max_length=2000)
    
    def validate_repo_url(self, value):
        """Validate GitHub URL"""
        if not ('github.com' in value or 'gitlab.com' in value):
            raise serializers.ValidationError(
                "Only GitHub and GitLab repositories are supported"
            )
        return value


class RepositorySerializer(serializers.ModelSerializer):
    """Serializer for Repository model"""
    class Meta:
        model = Repository
        fields = ['id', 'name', 'url', 'created_at', 'last_analyzed', 'total_sessions']


class ToolCallSerializer(serializers.ModelSerializer):
    """Serializer for ToolCall model"""
    class Meta:
        model = ToolCall
        fields = [
            'id', 'tool_name', 'tool_input', 'tool_output',
            'iteration', 'execution_time_ms', 'created_at'
        ]


class FindingSerializer(serializers.ModelSerializer):
    """Serializer for Finding model"""
    class Meta:
        model = Finding
        fields = [
            'id', 'file_path', 'line_start', 'line_end',
            'note', 'relevance_score', 'created_at'
        ]


class SessionDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for ResearchSession with related data"""
    repository = RepositorySerializer(read_only=True)
    tool_calls = ToolCallSerializer(many=True, read_only=True)
    findings = FindingSerializer(many=True, read_only=True)
    
    class Meta:
        model = ResearchSession
        fields = [
            'id', 'repository', 'question', 'final_answer', 'status',
            'created_at', 'started_at', 'completed_at',
            'total_iterations', 'total_tool_calls', 'token_usage',
            'error_message', 'tool_calls', 'findings'
        ]


class SessionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing sessions"""
    repository_name = serializers.CharField(source='repository.name', read_only=True)
    
    class Meta:
        model = ResearchSession
        fields = [
            'id', 'repository_name', 'question', 'status',
            'created_at', 'completed_at', 'total_iterations', 'total_tool_calls'
        ]
