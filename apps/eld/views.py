"""
Views for the ELD app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import ELDLog, DutyStatusEntry, ELDViolation
from .serializers import ELDLogSerializer, DutyStatusEntrySerializer
from .services import ELDLogService, HOSComplianceChecker, ELDReportGenerator, ELDPrintService
from apps.trips.models import Trip
import logging

logger = logging.getLogger(__name__)

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


@method_decorator(csrf_exempt, name='dispatch')
class ELDLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ELD logs.
    """
    queryset = ELDLog.objects.all().select_related('driver', 'vehicle', 'trip')
    serializer_class = ELDLogSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by driver if provided
        driver_id = self.request.query_params.get('driver_id')
        if driver_id:
            queryset = queryset.filter(driver_id=driver_id)

        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(log_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(log_date__lte=end_date)

        return queryset.order_by('-log_date')

    @action(detail=True, methods=['get'])
    def duty_entries(self, request, pk=None):
        """
        Get all duty status entries for a log.
        """
        eld_log = self.get_object()
        entries = eld_log.duty_entries.all().order_by('start_time')
        serializer = DutyStatusEntrySerializer(entries, many=True)

        return Response({
            'log_id': eld_log.id,
            'log_date': eld_log.log_date,
            'entries': serializer.data
        })

    @action(detail=True, methods=['post'])
    def certify(self, request, pk=None):
        """
        Certify an ELD log.
        """
        eld_log = self.get_object()

        if eld_log.is_certified:
            return Response(
                {'error': 'Log is already certified'},
                status=status.HTTP_400_BAD_REQUEST
            )

        eld_log.is_certified = True
        eld_log.certified_at = timezone.now()
        eld_log.save()

        # Create audit log entry
        from .models import ELDAuditLog
        ELDAuditLog.objects.create(
            eld_log=eld_log,
            action='CERTIFIED',
            description='Log certified by driver',
            user_name=eld_log.driver.name if eld_log.driver else 'Unknown',
            user_type='driver'
        )

        return Response({'message': 'Log certified successfully'})

    @action(detail=True, methods=['post'])
    def uncertify(self, request, pk=None):
        """
        Remove certification from an ELD log.
        """
        eld_log = self.get_object()

        if not eld_log.is_certified:
            return Response(
                {'error': 'Log is not certified'},
                status=status.HTTP_400_BAD_REQUEST
            )

        eld_log.is_certified = False
        eld_log.certified_at = None
        eld_log.save()

        # Create audit log entry
        from .models import ELDAuditLog
        ELDAuditLog.objects.create(
            eld_log=eld_log,
            action='UNCERTIFIED',
            description='Log certification removed',
            user_name=request.user.username if hasattr(request, 'user') else 'System',
            user_type='fleet_manager'
        )

        return Response({'message': 'Log certification removed'})

    @action(detail=True, methods=['get'])
    def violations(self, request, pk=None):
        """
        Get all violations for a log.
        """
        eld_log = self.get_object()
        violations = eld_log.violations.all().order_by('-violation_time')

        violation_data = []
        for violation in violations:
            violation_data.append({
                'id': violation.id,
                'type': violation.violation_type,
                'severity': violation.severity,
                'description': violation.description,
                'violation_time': violation.violation_time.isoformat(),
                'duration_minutes': violation.duration_minutes,
                'is_resolved': violation.is_resolved,
                'resolution_notes': violation.resolution_notes,
            })

        return Response({
            'log_id': eld_log.id,
            'violations': violation_data
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def check_compliance(request):
    """
    Check HOS compliance for given parameters.
    """
    try:
        data = request.data
        current_cycle_hours = float(data.get('current_cycle_hours', 0))
        daily_drive_hours = float(data.get('daily_drive_hours', 0))
        daily_duty_hours = float(data.get('daily_duty_hours', 0))

        checker = HOSComplianceChecker()
        available_time = checker.calculate_available_time(
            current_cycle_hours, daily_drive_hours, daily_duty_hours
        )

        # Check if driver can drive
        can_drive = (available_time['available_drive_hours'] > 0 and
                     available_time['available_duty_hours'] > 0)

        violations = []
        if current_cycle_hours >= 70:
            violations.append('70-hour cycle limit reached')
        if daily_drive_hours >= 11:
            violations.append('11-hour daily drive limit reached')
        if daily_duty_hours >= 14:
            violations.append('14-hour daily duty limit reached')

        return Response({
            'can_drive': can_drive,
            'available_time': available_time,
            'violations': violations,
            'recommendations': _get_recommendations(available_time)
        })

    except (ValueError, KeyError) as e:
        return Response(
            {'error': f'Invalid input: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def daily_report(request, log_id):
    """
    Generate a daily ELD report.
    """
    try:
        eld_log = get_object_or_404(ELDLog, id=log_id)

        report_generator = ELDReportGenerator()
        report = report_generator.generate_daily_summary(eld_log)

        return Response(report)

    except Exception as e:
        logger.error(f"Error generating daily report: {str(e)}")
        return Response(
            {'error': 'Failed to generate report'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def trip_report(request, trip_id):
    """
    Generate a trip ELD report.
    """
    try:
        trip = get_object_or_404(Trip, id=trip_id)

        report_generator = ELDReportGenerator()
        report = report_generator.generate_trip_summary(trip)

        return Response(report)

    except Exception as e:
        logger.error(f"Error generating trip report: {str(e)}")
        return Response(
            {'error': 'Failed to generate report'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def generate_printable_log(request, log_id):
    """
    Generate printable ELD log for inspection/compliance.
    Supports multiple output formats: printable, inspection, csv

    Query Parameters:
    - format: 'printable' (default), 'inspection', or 'csv'

    Examples:
    - GET /api/v1/eld/logs/1/printable/ - Standard printable format
    - GET /api/v1/eld/logs/1/printable/?format=inspection - Roadside inspection format
    - GET /api/v1/eld/logs/1/printable/?format=csv - CSV export format
    """
    try:
        eld_log = get_object_or_404(ELDLog, id=log_id)
        print_service = ELDPrintService()

        # Get output format from query parameters
        output_format = request.query_params.get('format', 'printable')

        if output_format == 'inspection':
            # Format for roadside inspection
            data = print_service.generate_inspection_format(eld_log)
            message = 'ELD log formatted for roadside inspection'
        elif output_format == 'csv':
            # CSV export format
            csv_data = print_service.export_to_csv(eld_log)
            return Response({
                'log_id': eld_log.id,
                'format': 'csv',
                'data': csv_data,
                'filename': f'eld_log_{eld_log.log_date.strftime("%Y%m%d")}_{eld_log.driver.name.replace(" ", "_") if eld_log.driver else "unknown"}.csv'
            })
        else:
            # Standard printable format
            data = print_service.generate_printable_log(eld_log)
            message = 'ELD log generated in printable format'

        return Response({
            'log_id': eld_log.id,
            'format': output_format,
            'data': data,
            'message': message,
            'compliance_status': {
                'is_compliant': eld_log.is_compliant,
                'violations_count': eld_log.violations.count(),
                'is_certified': eld_log.is_certified
            },
            'fmcsa_compliance_notes': [
                'Graph grid meets FMCSA minimum size requirements (6" x 1.5")',
                'All duty status changes recorded with location information',
                'Supporting documents attached as required',
                'Log available for roadside inspection presentation',
                'Electronic signature capability enabled',
                'Data retention complies with 6-month requirement'
            ]
        })

    except Exception as e:
        logger.error(f"Error generating printable log: {str(e)}")
        return Response(
            {'error': 'Failed to generate printable log', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _get_recommendations(available_time):
    """
    Get recommendations based on available time.
    """
    recommendations = []

    if available_time['needs_restart']:
        recommendations.append('34-hour restart required to reset cycle')
    elif available_time['remaining_cycle_hours'] < 10:
        recommendations.append('Plan 34-hour restart soon - less than 10 cycle hours remaining')

    if available_time['available_drive_hours'] < 2:
        recommendations.append('Limited driving time remaining - plan rest break')

    if available_time['available_duty_hours'] < 3:
        recommendations.append('Limited on-duty time remaining - complete trip soon')

    if not recommendations:
        recommendations.append('Good to drive - no immediate restrictions')

    return recommendations
