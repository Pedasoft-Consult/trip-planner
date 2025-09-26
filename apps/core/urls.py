"""
URL patterns for the core app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'drivers', views.DriverViewSet, basename='driver')
router.register(r'vehicles', views.VehicleViewSet, basename='vehicle')
router.register(r'companies', views.CompanyViewSet, basename='company')

app_name = 'core'

urlpatterns = [
    # Health check and basic endpoints
    path('', views.health_check, name='health_check'),
    path('geocode/', views.geocode_address, name='geocode'),

    # Enhanced REST API endpoints via ViewSets
    # These provide full CRUD operations plus custom actions:
    # - /api/drivers/ (GET, POST)
    # - /api/drivers/{id}/ (GET, PUT, PATCH, DELETE)
    # - /api/drivers/{id}/certify_logs/ (POST)
    # - /api/drivers/{id}/change_duty_status/ (POST)
    # - /api/drivers/{id}/hos_status/ (GET)
    # - /api/drivers/dashboard_stats/ (GET)
    # - /api/vehicles/ (GET, POST)
    # - /api/vehicles/{id}/ (GET, PUT, PATCH, DELETE)
    # - /api/vehicles/{id}/update_odometer/ (POST)
    # - /api/vehicles/{id}/vehicle_status/ (GET)
    # - /api/companies/ (GET, POST)
    # - /api/companies/{id}/ (GET, PUT, PATCH, DELETE)
    # - /api/companies/{id}/compliance_info/ (GET)
    path('api/', include(router.urls)),

    # ELD Compliance utility endpoints
    path('api/duty-status-options/', views.driver_duty_status_options, name='duty_status_options'),
    path('api/hos-rules/', views.hos_rules_info, name='hos_rules'),

    # Fleet Management endpoints
    path('api/fleet-dashboard/', views.fleet_dashboard, name='fleet_dashboard'),
    path('api/bulk-driver-operations/', views.bulk_driver_operations, name='bulk_driver_operations'),
    path('api/compliance-report/', views.compliance_report, name='compliance_report'),
    path('api/system-info/', views.system_info, name='system_info'),

    # Legacy endpoints (for backward compatibility)
    # These maintain the original simple list format
    path('drivers/', views.DriverListView.as_view(), name='driver_list'),
    path('vehicles/', views.VehicleListView.as_view(), name='vehicle_list'),
    path('companies/', views.CompanyListView.as_view(), name='company_list'),
]

# Additional URL patterns for different access patterns
# You can include these if you want alternative routing structures

# Direct action URLs (alternative to ViewSet actions)
action_urlpatterns = [
    # Driver actions (alternative to ViewSet actions)
    path('drivers/<int:driver_id>/certify/', views.DriverViewSet.as_view({'post': 'certify_logs'}),
         name='driver_certify'),
    path('drivers/<int:driver_id>/duty-status/', views.DriverViewSet.as_view({'post': 'change_duty_status'}),
         name='driver_duty_status'),
    path('drivers/<int:driver_id>/hos/', views.DriverViewSet.as_view({'get': 'hos_status'}), name='driver_hos'),

    # Vehicle actions (alternative to ViewSet actions)
    path('vehicles/<int:vehicle_id>/odometer/', views.VehicleViewSet.as_view({'post': 'update_odometer'}),
         name='vehicle_odometer'),
    path('vehicles/<int:vehicle_id>/status/', views.VehicleViewSet.as_view({'get': 'vehicle_status'}),
         name='vehicle_status'),

    # Company actions (alternative to ViewSet actions)
    path('companies/<int:company_id>/compliance/', views.CompanyViewSet.as_view({'get': 'compliance_info'}),
         name='company_compliance'),
]

# Optional: Include action patterns if you want both routing styles
# urlpatterns += action_urlpatterns
