"""
Enhanced core views with ELD compliance functionality.
Update apps/core/views.py with these enhancements.
"""
import json
from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count, Avg
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from .models import Driver, Vehicle, Company, Location
from .serializers import (
    LocationSerializer, DriverSerializer, VehicleSerializer, CompanySerializer,
    DriverCertificationSerializer, DutyStatusChangeSerializer,
    VehicleOdometerUpdateSerializer, DriverSummarySerializer,
    VehicleSummarySerializer, CompanySummarySerializer
)
from mapping.services import geocode_address_service
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint to verify the API is running.
    """
    return Response({
        'status': 'healthy',
        'message': 'ELD Trip Planner API is running',
        'version': '1.0.0',
        'timestamp': timezone.now().isoformat(),
        'features': [
            'Trip Planning',
            'ELD Log Generation',
            'Hours of Service Compliance',
            'Route Optimization',
            'Driver Management',
            'Vehicle Tracking'
        ]
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def fleet_dashboard(request):
    """
    Get comprehensive fleet dashboard statistics.
    """
    try:
        # Driver statistics
        total_drivers = Driver.objects.count()
        active_drivers = Driver.objects.filter(is_active=True).count()
        available_drivers = Driver.objects.filter(
            is_active=True,
            current_cycle_hours__lt=70,
            current_daily_drive_hours__lt=11,
            current_daily_duty_hours__lt=14
        ).count()

        # Vehicle statistics
        total_vehicles = Vehicle.objects.count()
        active_vehicles = Vehicle.objects.filter(is_active=True).count()

        # Company statistics
        total_companies = Company.objects.count()
        active_companies = Company.objects.filter(is_active=True).count()

        # Recent activity (last 24 hours)
        yesterday = timezone.now() - timedelta(hours=24)
        recent_certifications = Driver.objects.filter(
            last_certification_date__gte=yesterday
        ).count()

        # Compliance alerts
        cycle_warnings = Driver.objects.filter(current_cycle_hours__gte=60).count()
        cycle_violations = Driver.objects.filter(current_cycle_hours__gte=70).count()

        return Response({
            'dashboard_data': {
                'totals': {
                    'drivers': total_drivers,
                    'vehicles': total_vehicles,
                    'companies': total_companies
                },
                'active': {
                    'drivers': active_drivers,
                    'vehicles': active_vehicles,
                    'companies': active_companies
                },
                'availability': {
                    'available_drivers': available_drivers,
                    'utilization_rate': round((available_drivers / max(active_drivers, 1)) * 100, 1)
                },
                'compliance': {
                    'cycle_warnings': cycle_warnings,
                    'cycle_violations': cycle_violations,
                    'compliance_rate': round(((active_drivers - cycle_violations) / max(active_drivers, 1)) * 100, 1)
                },
                'recent_activity': {
                    'certifications_24h': recent_certifications,
                },
                'alerts': {
                    'high_priority': cycle_violations,
                    'medium_priority': cycle_warnings,
                    'needs_attention': Driver.objects.filter(
                        last_certification_date__lt=timezone.now() - timedelta(days=1)
                    ).count()
                }
            },
            'generated_at': timezone.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error generating fleet dashboard: {str(e)}")
        return Response(
            {'error': 'Failed to generate dashboard data'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def bulk_driver_operations(request):
    """
    Perform bulk operations on multiple drivers.
    """
    try:
        operation = request.data.get('operation')
        driver_ids = request.data.get('driver_ids', [])

        if not operation or not driver_ids:
            return Response(
                {'error': 'Operation and driver_ids are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        drivers = Driver.objects.filter(id__in=driver_ids)
        if not drivers.exists():
            return Response(
                {'error': 'No drivers found with provided IDs'},
                status=status.HTTP_404_NOT_FOUND
            )

        results = {'success': 0, 'failed': 0, 'errors': []}

        if operation == 'certify_logs':
            for driver in drivers:
                try:
                    driver.certify_logs()
                    results['success'] += 1
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"Driver {driver.id}: {str(e)}")

        elif operation == 'reset_daily_hours':
            # CAUTION: This should only be used in specific circumstances
            drivers.update(
                current_daily_drive_hours=0,
                current_daily_duty_hours=0
            )
            results['success'] = drivers.count()

        elif operation == 'activate':
            drivers.update(is_active=True)
            results['success'] = drivers.count()

        elif operation == 'deactivate':
            drivers.update(is_active=False)
            results['success'] = drivers.count()

        else:
            return Response(
                {'error': f'Unknown operation: {operation}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'message': f'Bulk operation {operation} completed',
            'results': results
        })

    except Exception as e:
        logger.error(f"Error in bulk driver operations: {str(e)}")
        return Response(
            {'error': 'Bulk operation failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def compliance_report(request):
    """
    Generate compliance report for the fleet.
    """
    try:
        # Get date range from query parameters
        days = int(request.query_params.get('days', 7))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        # Driver compliance stats
        total_drivers = Driver.objects.filter(is_active=True).count()

        compliance_data = {
            'report_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'fleet_overview': {
                'total_active_drivers': total_drivers,
                'total_active_vehicles': Vehicle.objects.filter(is_active=True).count(),
            },
            'hos_compliance': {
                'cycle_compliant': Driver.objects.filter(
                    current_cycle_hours__lt=70,
                    is_active=True
                ).count(),
                'daily_drive_compliant': Driver.objects.filter(
                    current_daily_drive_hours__lt=11,
                    is_active=True
                ).count(),
                'daily_duty_compliant': Driver.objects.filter(
                    current_daily_duty_hours__lt=14,
                    is_active=True
                ).count(),
                'overall_compliance_rate': 0  # Will be calculated below
            },
            'violations': {
                'cycle_violations': Driver.objects.filter(current_cycle_hours__gte=70).count(),
                'daily_drive_violations': Driver.objects.filter(current_daily_drive_hours__gte=11).count(),
                'daily_duty_violations': Driver.objects.filter(current_daily_duty_hours__gte=14).count(),
            },
            'certification_status': {
                'certified_today': Driver.objects.filter(
                    last_certification_date__date=timezone.now().date()
                ).count(),
                'certified_this_week': Driver.objects.filter(
                    last_certification_date__gte=timezone.now() - timedelta(days=7)
                ).count(),
                'never_certified': Driver.objects.filter(
                    last_certification_date__isnull=True
                ).count(),
            }
        }

        # Calculate overall compliance rate
        if total_drivers > 0:
            compliant_drivers = Driver.objects.filter(
                current_cycle_hours__lt=70,
                current_daily_drive_hours__lt=11,
                current_daily_duty_hours__lt=14,
                is_active=True
            ).count()
            compliance_data['hos_compliance']['overall_compliance_rate'] = round(
                (compliant_drivers / total_drivers) * 100, 2
            )

        return Response(compliance_data)

    except Exception as e:
        logger.error(f"Error generating compliance report: {str(e)}")
        return Response(
            {'error': 'Failed to generate compliance report'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def system_info(request):
    """
    Get system information and API capabilities.
    """
    return Response({
        'system': {
            'name': 'ELD Trip Planner API',
            'version': '1.0.0',
            'description': 'Comprehensive ELD compliance and trip planning system',
            'timestamp': timezone.now().isoformat(),
        },
        'capabilities': {
            'trip_planning': True,
            'eld_compliance': True,
            'hours_of_service': True,
            'route_optimization': True,
            'driver_management': True,
            'vehicle_tracking': True,
            'digital_certification': True,
            'bulk_operations': True,
            'compliance_reporting': True,
        },
        'api_endpoints': {
            'drivers': '/api/drivers/',
            'vehicles': '/api/vehicles/',
            'companies': '/api/companies/',
            'trips': '/api/v1/trips/',
            'routes': '/api/v1/routes/',
            'eld': '/api/v1/eld/',
            'utilities': {
                'geocode': '/geocode/',
                'duty_status_options': '/api/duty-status-options/',
                'hos_rules': '/api/hos-rules/',
                'fleet_dashboard': '/api/fleet-dashboard/',
                'compliance_report': '/api/compliance-report/',
            }
        },
        'compliance_features': {
            'fmcsa_hours_of_service': True,
            'electronic_logging': True,
            'digital_signatures': True,
            'audit_trails': True,
            'roadside_inspection_ready': True,
            'dot_compliance': True,
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def geocode_address(request):
    """
    Geocode an address to get latitude and longitude coordinates.
    """
    try:
        address = request.data.get('address')
        if not address:
            return Response(
                {'error': 'Address is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        location_data = geocode_address_service(address)
        if location_data:
            # Save location to database
            location = Location.objects.create(**location_data)
            serializer = LocationSerializer(location)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'Unable to geocode address'},
                status=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        logger.error(f"Error geocoding address: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class DriverViewSet(ModelViewSet):
    """
    Enhanced ViewSet for managing drivers with ELD compliance.
    """
    queryset = Driver.objects.all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'list':
            return DriverSummarySerializer
        return DriverSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # Filter by duty status
        duty_status = self.request.query_params.get('duty_status')
        if duty_status:
            queryset = queryset.filter(current_duty_status=duty_status)

        # Filter by can drive status
        can_drive = self.request.query_params.get('can_drive')
        if can_drive is not None:
            if can_drive.lower() == 'true':
                queryset = queryset.filter(
                    current_cycle_hours__lt=70,
                    current_daily_drive_hours__lt=11,
                    current_daily_duty_hours__lt=14,
                    is_active=True
                )
            else:
                # Drivers who cannot drive
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(current_cycle_hours__gte=70) |
                    Q(current_daily_drive_hours__gte=11) |
                    Q(current_daily_duty_hours__gte=14) |
                    Q(is_active=False)
                )

        return queryset.order_by('name')

    @action(detail=True, methods=['post'])
    def certify_logs(self, request, pk=None):
        """
        Certify driver's ELD logs.
        """
        driver = self.get_object()
        serializer = DriverCertificationSerializer(data=request.data)

        if serializer.is_valid():
            try:
                driver.certify_logs(
                    signature_data=serializer.validated_data.get('signature_data'),
                    method=serializer.validated_data.get('certification_method', 'ELECTRONIC')
                )

                return Response({
                    'message': 'Logs certified successfully',
                    'certification_time': driver.last_certification_date.isoformat(),
                    'method': driver.certification_method
                })

            except Exception as e:
                logger.error(f"Error certifying logs for driver {pk}: {str(e)}")
                return Response(
                    {'error': f'Certification failed: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def change_duty_status(self, request, pk=None):
        """
        Change driver's duty status.
        """
        driver = self.get_object()
        serializer = DutyStatusChangeSerializer(data=request.data)

        if serializer.is_valid():
            try:
                # Build location string
                location_parts = []
                if serializer.validated_data.get('location'):
                    location_parts.append(serializer.validated_data['location'])

                lat = serializer.validated_data.get('latitude')
                lng = serializer.validated_data.get('longitude')
                if lat is not None and lng is not None:
                    location_parts.append(f"({lat:.6f}, {lng:.6f})")

                location_str = ' '.join(location_parts) if location_parts else None

                # Update duty status
                status_change = driver.update_duty_status(
                    new_status=serializer.validated_data['new_status'],
                    location=location_str
                )

                # Create ELD log entry (integrate with ELD app if available)
                try:
                    from apps.eld.models import ELDAuditLog
                    # Get the current ELD log for the driver (if exists)
                    # This is a simplified version - in production you'd need proper ELD log handling
                    ELDAuditLog.objects.create(
                        eld_log=None,  # Would need to be determined based on current trip/log
                        action='DUTY_CHANGE',
                        description=f"Duty status changed from {status_change['old_status']} to {status_change['new_status']}",
                        user_name=driver.name,
                        user_type='driver'
                    )
                except ImportError:
                    # ELD app not available, just log the change
                    logger.info(f"Duty status change logged for driver {driver.name}: {status_change}")
                except Exception as eld_error:
                    logger.warning(f"Could not create ELD audit log: {str(eld_error)}")

                return Response({
                    'message': 'Duty status changed successfully',
                    'status_change': status_change,
                    'driver_status': {
                        'current_duty_status': driver.current_duty_status,
                        'last_change_time': driver.last_duty_change_time.isoformat(),
                        'location': driver.last_duty_change_location
                    }
                })

            except Exception as e:
                logger.error(f"Error changing duty status for driver {pk}: {str(e)}")
                return Response(
                    {'error': f'Status change failed: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def hos_status(self, request, pk=None):
        """
        Get detailed Hours of Service status for driver.
        """
        driver = self.get_object()
        can_drive, reason = driver.can_drive()

        return Response({
            'driver_id': driver.id,
            'driver_name': driver.name,
            'current_status': {
                'duty_status': driver.current_duty_status,
                'can_drive': can_drive,
                'reason': reason,
                'last_change': driver.last_duty_change_time.isoformat() if driver.last_duty_change_time else None
            },
            'hours': {
                'cycle_hours_used': float(driver.current_cycle_hours),
                'daily_drive_hours': float(driver.current_daily_drive_hours),
                'daily_duty_hours': float(driver.current_daily_duty_hours),
                'available_drive_hours': max(0, min(70 - float(driver.current_cycle_hours),
                                                    11 - float(driver.current_daily_drive_hours))),
                'available_duty_hours': max(0, min(70 - float(driver.current_cycle_hours),
                                                   14 - float(driver.current_daily_duty_hours))),
                'remaining_cycle_hours': max(0, 70 - float(driver.current_cycle_hours))
            },
            'compliance': {
                'needs_restart': float(driver.current_cycle_hours) >= 60,  # Warning at 60 hours
                'restart_required': float(driver.current_cycle_hours) >= 70,
                'daily_limits_reached': {
                    'driving': float(driver.current_daily_drive_hours) >= 11,
                    'duty': float(driver.current_daily_duty_hours) >= 14
                }
            },
            'certification': {
                'last_certified': driver.last_certification_date.isoformat() if driver.last_certification_date else None,
                'method': driver.certification_method,
                'needs_certification': not driver.last_certification_date or
                                       (timezone.now() - driver.last_certification_date).days > 0
            }
        })

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """
        Get driver dashboard statistics.
        """
        queryset = self.get_queryset()

        stats = {
            'total_drivers': queryset.count(),
            'active_drivers': queryset.filter(is_active=True).count(),
            'drivers_on_duty': queryset.filter(current_duty_status__in=['D', 'ON']).count(),
            'drivers_available': queryset.filter(
                is_active=True,
                current_cycle_hours__lt=70,
                current_daily_drive_hours__lt=11,
                current_daily_duty_hours__lt=14
            ).count(),
            'duty_status_breakdown': {
                'off_duty': queryset.filter(current_duty_status='OFF').count(),
                'sleeper_berth': queryset.filter(current_duty_status='SB').count(),
                'driving': queryset.filter(current_duty_status='D').count(),
                'on_duty': queryset.filter(current_duty_status='ON').count(),
            },
            'compliance_alerts': {
                'cycle_warnings': queryset.filter(current_cycle_hours__gte=60).count(),
                'cycle_violations': queryset.filter(current_cycle_hours__gte=70).count(),
                'daily_drive_violations': queryset.filter(current_daily_drive_hours__gte=11).count(),
                'daily_duty_violations': queryset.filter(current_daily_duty_hours__gte=14).count(),
            },
            'certification_status': {
                'certified_today': queryset.filter(
                    last_certification_date__date=timezone.now().date()
                ).count(),
                'needs_certification': queryset.filter(
                    Q(last_certification_date__isnull=True) |
                    Q(last_certification_date__date__lt=timezone.now().date())
                ).count(),
            }
        }

        return Response(stats)


class VehicleViewSet(ModelViewSet):
    """
    Enhanced ViewSet for managing vehicles with ELD compliance.
    """
    queryset = Vehicle.objects.all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'list':
            return VehicleSummarySerializer
        return VehicleSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # Filter by vehicle type
        vehicle_type = self.request.query_params.get('vehicle_type')
        if vehicle_type:
            queryset = queryset.filter(vehicle_type=vehicle_type)

        return queryset.order_by('license_plate')

    @action(detail=True, methods=['post'])
    def update_odometer(self, request, pk=None):
        """
        Update vehicle odometer reading.
        """
        vehicle = self.get_object()
        serializer = VehicleOdometerUpdateSerializer(data=request.data, instance=vehicle)

        if serializer.is_valid():
            try:
                new_reading = serializer.validated_data['new_reading']
                location = serializer.validated_data.get('location', '')

                miles_driven = vehicle.update_odometer(new_reading)

                return Response({
                    'message': 'Odometer updated successfully',
                    'previous_reading': new_reading - miles_driven,
                    'new_reading': new_reading,
                    'miles_driven': miles_driven,
                    'location': location,
                    'updated_at': timezone.now().isoformat(),
                    'current_engine_hours': float(vehicle.current_engine_hours)
                })

            except Exception as e:
                logger.error(f"Error updating odometer for vehicle {pk}: {str(e)}")
                return Response(
                    {'error': f'Odometer update failed: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def vehicle_status(self, request, pk=None):
        """
        Get comprehensive vehicle status information.
        """
        vehicle = self.get_object()

        return Response({
            'vehicle_id': vehicle.id,
            'identification': vehicle.get_vehicle_identification(),
            'status': {
                'is_active': vehicle.is_active,
                'current_odometer': vehicle.current_odometer,
                'engine_hours': float(vehicle.current_engine_hours),
                'fuel_level_estimate': 'Unknown',  # Would need integration with vehicle systems
            },
            'eld_connection': {
                'device_id': vehicle.eld_device_id,
                'connection_type': vehicle.eld_connection_type,
                'status': 'Connected' if vehicle.eld_device_id else 'Not Connected'
            },
            'specifications': {
                'gvwr': vehicle.gvwr,
                'vehicle_type': vehicle.vehicle_type,
                'fuel_capacity': float(vehicle.fuel_capacity),
                'mpg': float(vehicle.mpg)
            }
        })


class CompanyViewSet(ModelViewSet):
    """
    Enhanced ViewSet for managing companies with ELD compliance.
    """
    queryset = Company.objects.all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'list':
            return CompanySummarySerializer
        return CompanySerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset.order_by('name')

    @action(detail=True, methods=['get'])
    def compliance_info(self, request, pk=None):
        """
        Get company's ELD compliance information.
        """
        company = self.get_object()

        # Get related drivers and vehicles count
        active_drivers = Driver.objects.filter(carrier_name=company.name, is_active=True).count()
        active_vehicles = Vehicle.objects.filter(is_active=True).count()  # You might want to add company relation

        return Response({
            'company_id': company.id,
            'carrier_info': company.get_full_carrier_info(),
            'compliance_status': {
                'fmcsa_registered': bool(company.fmcsa_registration_date),
                'registration_date': company.fmcsa_registration_date.isoformat() if company.fmcsa_registration_date else None,
                'eld_provider': company.eld_provider,
                'eld_registration_id': company.eld_registration_id
            },
            'fleet_stats': {
                'active_drivers': active_drivers,
                'active_vehicles': active_vehicles
            },
            'contact_info': {
                'main_office': company.main_office_address,
                'home_terminal': company.home_terminal_address,
                'inspection_contact': {
                    'name': company.inspection_contact_name,
                    'phone': company.inspection_contact_phone
                }
            }
        })


# Legacy view functions for backward compatibility
class DriverListView(ListView):
    """
    Legacy list view for active drivers (kept for backward compatibility).
    """
    model = Driver
    queryset = Driver.objects.filter(is_active=True)
    context_object_name = 'drivers'

    def get(self, request, *args, **kwargs):
        drivers = self.get_queryset()
        data = [
            {
                'id': driver.id,
                'name': driver.name,
                'full_display_name': driver.get_full_display_name(),
                'license_number': driver.license_number,
                'license_state': driver.license_state,
                'current_duty_status': driver.current_duty_status,
                'can_drive': driver.can_drive()[0],
                'current_cycle_hours': float(driver.current_cycle_hours)
            }
            for driver in drivers
        ]
        return JsonResponse({'drivers': data})


class VehicleListView(ListView):
    """
    Legacy list view for active vehicles (kept for backward compatibility).
    """
    model = Vehicle
    queryset = Vehicle.objects.filter(is_active=True)
    context_object_name = 'vehicles'

    def get(self, request, *args, **kwargs):
        vehicles = self.get_queryset()
        data = [
            {
                'id': vehicle.id,
                'display_name': str(vehicle),
                'vin': vehicle.vin,
                'license_plate': vehicle.license_plate,
                'make': vehicle.make,
                'model': vehicle.model,
                'year': vehicle.year,
                'vehicle_number': vehicle.vehicle_number,
                'current_odometer': vehicle.current_odometer
            }
            for vehicle in vehicles
        ]
        return JsonResponse({'vehicles': data})


class CompanyListView(ListView):
    """
    Legacy list view for active companies (kept for backward compatibility).
    """
    model = Company
    queryset = Company.objects.filter(is_active=True)
    context_object_name = 'companies'

    def get(self, request, *args, **kwargs):
        companies = self.get_queryset()
        data = [
            {
                'id': company.id,
                'name': company.name,
                'dot_number': company.dot_number,
                'mc_number': company.mc_number,
                'carrier_name': company.carrier_name,
                'full_carrier_info': company.get_full_carrier_info()
            }
            for company in companies
        ]
        return JsonResponse({'companies': data})


# Utility API endpoints
@api_view(['GET'])
@permission_classes([AllowAny])
def driver_duty_status_options(request):
    """
    Get available duty status options with descriptions.
    """
    return Response({
        'duty_status_options': [
            {
                'code': 'OFF',
                'display': 'Off Duty',
                'description': 'Driver is off duty and not available for work',
                'graph_line': 1
            },
            {
                'code': 'SB',
                'display': 'Sleeper Berth',
                'description': 'Driver is resting in sleeper berth',
                'graph_line': 2
            },
            {
                'code': 'D',
                'display': 'Driving',
                'description': 'Driver is driving the vehicle',
                'graph_line': 4
            },
            {
                'code': 'ON',
                'display': 'On Duty (Not Driving)',
                'description': 'Driver is on duty but not driving',
                'graph_line': 3
            }
        ]
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def hos_rules_info(request):
    """
    Get information about Hours of Service rules.
    """
    return Response({
        'hos_rules': {
            'property_carrying': {
                'max_drive_hours_daily': 11,
                'max_duty_hours_daily': 14,
                'max_cycle_hours': 70,
                'cycle_period_days': 8,
                'min_off_duty_hours': 10,
                'restart_hours': 34
            },
            'passenger_carrying': {
                'max_drive_hours_daily': 10,
                'max_duty_hours_daily': 15,
                'max_cycle_hours': 70,
                'cycle_period_days': 8,
                'min_off_duty_hours': 8,
                'restart_hours': 34
            }
        },
        'violation_types': [
            {
                'type': 'CYCLE_EXCEEDED',
                'description': '70-hour cycle exceeded',
                'severity': 'CRITICAL'
            },
            {
                'type': 'DAILY_DRIVE_EXCEEDED',
                'description': '11-hour daily drive limit exceeded',
                'severity': 'HIGH'
            },
            {
                'type': 'DAILY_DUTY_EXCEEDED',
                'description': '14-hour daily duty limit exceeded',
                'severity': 'HIGH'
            },
            {
                'type': 'INSUFFICIENT_REST',
                'description': 'Insufficient off-duty time',
                'severity': 'MEDIUM'
            }
        ]
    })


# Error handlers
def bad_request(request, exception):
    """400 Bad Request error handler"""
    return JsonResponse(
        {'error': 'Bad request', 'status': 400},
        status=400
    )


def permission_denied(request, exception):
    """403 Permission Denied error handler"""
    return JsonResponse(
        {'error': 'Permission denied', 'status': 403},
        status=403
    )


def page_not_found(request, exception):
    """404 Not Found error handler"""
    return JsonResponse(
        {'error': 'Resource not found', 'status': 404},
        status=404
    )


def server_error(request):
    """500 Internal Server Error handler"""
    return JsonResponse(
        {'error': 'Internal server error', 'status': 500},
        status=500
    )
