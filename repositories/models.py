from django.db import models
from django.utils import timezone


class Repository(models.Model):
    """
    Represents a GitHub repository that has been researched.
    """
    url = models.URLField(unique=True, max_length=500, db_index=True)
    name = models.CharField(max_length=255)
    local_path = models.CharField(max_length=500, blank=True, null=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    last_analyzed = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)
    
    total_sessions = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'repositories'
        verbose_name_plural = 'Repositories'
        ordering = ['-last_analyzed']
        indexes = [
            models.Index(fields=['url']),
            models.Index(fields=['-last_analyzed']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.url})"
    
    def update_last_analyzed(self):
        """Update last analyzed timestamp"""
        self.last_analyzed = timezone.now()
        self.save(update_fields=['last_analyzed'])
    
    def increment_session_count(self):
        """Increment total sessions counter"""
        self.total_sessions += 1
        self.save(update_fields=['total_sessions'])
