from django.urls import path
from .views import index, generate, example, download

urlpatterns = [
    path('', index),
    path('generate/', generate),
    path('example/<str:name>/', example),
    path('download/', download),
]