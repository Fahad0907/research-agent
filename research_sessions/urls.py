"""
Sessions URL Configuration
"""
from django.urls import path
from research_sessions import views

urlpatterns = [
    path('start/', views.start_research, name='start_research'),
    path('<int:session_id>/', views.get_session, name='get_session'),
]
