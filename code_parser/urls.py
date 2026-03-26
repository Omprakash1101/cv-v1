from django.urls import path
from .views import ProjectDiagramView, FrontendPageView, HealthCheckView

urlpatterns = [
    path("healthcheck/", HealthCheckView.as_view()),
    path('', FrontendPageView.as_view(), name='frontend'),
    path('diagram/', ProjectDiagramView.as_view(), name='project-diagram'),
]