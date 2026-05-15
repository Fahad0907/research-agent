from django.db import models
from django.utils import timezone
from repositories.models import Repository


class ResearchSession(models.Model):
    """
    Represents a single research question asked about a repository.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    question = models.TextField()
    final_answer = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    total_iterations = models.IntegerField(default=0)
    total_tool_calls = models.IntegerField(default=0)
    token_usage = models.IntegerField(default=0, help_text="Total tokens used")
    
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'research_sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['repository', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Session {self.id}: {self.question[:50]}..."
    
    def mark_processing(self):
        """Mark session as processing"""
        self.status = 'processing'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def mark_completed(self, final_answer):
        """Mark session as completed"""
        self.status = 'completed'
        self.final_answer = final_answer
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'final_answer', 'completed_at'])
    
    def mark_failed(self, error_message):
        """Mark session as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at'])
    
    def increment_iteration(self):
        """Increment iteration counter"""
        self.total_iterations += 1
        self.save(update_fields=['total_iterations'])
    
    def increment_tool_calls(self):
        """Increment tool calls counter"""
        self.total_tool_calls += 1
        self.save(update_fields=['total_tool_calls'])
    
    def add_token_usage(self, tokens):
        """Add tokens to the session's total"""
        self.token_usage += tokens
        self.save(update_fields=['token_usage'])


class ToolCall(models.Model):
    """
    Logs every tool call made by the agent during a research session.
    """
    session = models.ForeignKey(
        ResearchSession,
        on_delete=models.CASCADE,
        related_name='tool_calls'
    )
    
    tool_name = models.CharField(max_length=100)
    tool_input = models.JSONField()
    tool_output = models.TextField()
    
    iteration = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    
    execution_time_ms = models.IntegerField(default=0, help_text="Execution time in milliseconds")
    
    class Meta:
        db_table = 'tool_calls'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['tool_name']),
        ]
    
    def __str__(self):
        return f"{self.tool_name} (Session {self.session_id})"


class Finding(models.Model):
    """
    Represents a specific finding or insight discovered by the agent.
    Linked to files and code locations.
    """
    session = models.ForeignKey(
        ResearchSession,
        on_delete=models.CASCADE,
        related_name='findings'
    )
    
    file_path = models.CharField(max_length=500)
    line_start = models.IntegerField(null=True, blank=True)
    line_end = models.IntegerField(null=True, blank=True)
    
    note = models.TextField(help_text="Agent's insight or observation")
    relevance_score = models.FloatField(default=0.0, help_text="How relevant this finding is (0-1)")
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'findings'
        ordering = ['-relevance_score', 'created_at']
        indexes = [
            models.Index(fields=['session', '-relevance_score']),
        ]
    
    def __str__(self):
        return f"Finding in {self.file_path} (Session {self.session_id})"
