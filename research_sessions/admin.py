from django.contrib import admin
from research_sessions.models import ResearchSession, ToolCall, Finding


@admin.register(ResearchSession)
class ResearchSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'repository', 'question_short', 'status', 'total_iterations', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['question', 'final_answer']
    readonly_fields = ['created_at', 'started_at', 'completed_at']
    
    def question_short(self, obj):
        return obj.question[:50] + '...' if len(obj.question) > 50 else obj.question
    question_short.short_description = 'Question'


@admin.register(ToolCall)
class ToolCallAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'tool_name', 'iteration', 'execution_time_ms', 'created_at']
    list_filter = ['tool_name', 'created_at']
    search_fields = ['tool_name']
    readonly_fields = ['created_at']


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'file_path', 'relevance_score', 'created_at']
    list_filter = ['relevance_score', 'created_at']
    search_fields = ['file_path', 'note']
    readonly_fields = ['created_at']
