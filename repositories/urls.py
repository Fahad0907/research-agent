"""
Repositories URL Configuration
"""
from django.urls import path
from research_sessions.views import list_repository_sessions

urlpatterns = [
    path('sessions/', list_repository_sessions, name='list_repository_sessions'),
]
