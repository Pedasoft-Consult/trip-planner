"""
URL patterns for the routes app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'templates', views.RouteTemplateViewSet, basename='route-template')
router.register(r'rest-areas', views.RestAreaViewSet, basename='rest-area')
router.register(r'alerts', views.RouteAlertViewSet, basename='route-alert')

app_name = 'routes'

urlpatterns = [
    path('', include(router.urls)),
    path('calculate/', views.calculate_route, name='calculate_route'),
    path('optimize/', views.optimize_route, name='optimize_route'),
    path('traffic/', views.get_traffic_data, name='traffic_data'),
    path('restrictions/', views.check_restrictions, name='check_restrictions'),
]
