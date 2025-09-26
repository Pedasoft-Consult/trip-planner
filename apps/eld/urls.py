"""
URL patterns for the ELD app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'logs', views.ELDLogViewSet, basename='eld-log')

app_name = 'eld'

urlpatterns = [
    path('', include(router.urls)),
    path('compliance/check/', views.check_compliance, name='check_compliance'),
    path('reports/daily/<int:log_id>/', views.daily_report, name='daily_report'),
    path('reports/trip/<int:trip_id>/', views.trip_report, name='trip_report'),
    path('logs/<int:log_id>/printable/', views.generate_printable_log, name='generate_printable_log'),
]
