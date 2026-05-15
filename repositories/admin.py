from django.contrib import admin
from repositories.models import Repository


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'total_sessions', 'last_analyzed', 'created_at']
    search_fields = ['name', 'url']
    list_filter = ['created_at', 'last_analyzed']
    readonly_fields = ['created_at', 'last_updated']
