"""
URL patterns for the trips app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.TripViewSet, basename='trip')

app_name = 'trips'

urlpatterns = [
    path('', include(router.urls)),
]
