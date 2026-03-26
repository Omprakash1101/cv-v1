from django.urls import path
from .views import ProjectDiagramView, FrontendPageView

urlpatterns = [
    path('', FrontendPageView.as_view(), name='frontend'),
    path('diagram/', ProjectDiagramView.as_view(), name='project-diagram'),
]