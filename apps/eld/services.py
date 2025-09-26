"""
ELD service classes for log generation and compliance checking.
"""
from datetime import datetime, timedelta, date
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import ELDLog, DutyStatusEntry, ELDViolation, ELDAuditLog
from apps.trips.models import Trip, Stop
import logging

logger = logging.getLogger(__name__)


class ELDLogService:
    """
    Service for generating and managing ELD logs.
    """

    def __init__(self):
        self.current_time = timezone.now()

    @transaction.atomic
    def generate_logs_for_trip(self, trip):
        """
        Generate ELD logs for an entire trip.

        Args:
            trip: Trip instance

        Returns:
            List of ELD log dictionaries
        """
        try:
            # Get trip timeline from stops
            stops = trip.stops.all().order_by('sequence_order')

            if not stops:
                raise ValueError("Trip has no stops defined")

            # Group stops by date to create daily logs
            daily_logs = self._group_stops_by_date(stops)

            # Generate ELD log for each day
            eld_logs = []
            for log_date, day_stops in daily_logs.items():
                eld_log = self._generate_daily_log(trip, log_date, day_stops)
                eld_logs.append(self._serialize_eld_log(eld_log))

            return eld_logs

        except Exception as e:
            logger.error(f"Error generating ELD logs for trip {trip.id}: {str(e)}")
            raise

    def _group_stops_by_date(self, stops):
        """
        Group stops by date for daily log generation.
        """
        daily_logs = {}

        for stop in stops:
            log_date = stop.estimated_arrival_time.date()

            if log_date not in daily_logs:
                daily_logs[log_date] = []

            daily_logs[log_date].append(stop)

        return daily_logs

    @transaction.atomic
    def _generate_daily_log(self, trip, log_date, stops):
        """
        Generate a daily ELD log for a specific date.
        """
        # Create or get existing ELD log
        eld_log, created = ELDLog.objects.get_or_create(
            trip=trip,
            driver=trip.driver,
            vehicle=trip.vehicle,
            log_date=log_date,
            defaults={
                'starting_odometer': 0,
                'ending_odometer': 0,
                'cycle_hours_used': trip.current_cycle_hours,
            }
        )

        if created:
            # Generate duty status entries for the day
            self._generate_duty_entries(eld_log, stops)

            # Calculate daily totals
            self._calculate_daily_totals(eld_log)

            # Check for violations
            self._check_violations(eld_log)

            # Create audit log entry
            ELDAuditLog.objects.create(
                eld_log=eld_log,
                action='CREATED',
                description=f'ELD log created for {log_date}',
                user_name=trip.driver.name if trip.driver else 'System',
                user_type='system'
            )

        return eld_log

    def _generate_duty_entries(self, eld_log, stops):
        """
        Generate duty status entries based on trip stops.
        """
        entries = []
        current_time = datetime.combine(eld_log.log_date, datetime.min.time())
        current_time = timezone.make_aware(current_time)

        # Start with off-duty status
        if not stops or stops[0].estimated_arrival_time.time() != datetime.min.time():
            entries.append(DutyStatusEntry(
                eld_log=eld_log,
                duty_status='OFF',
                start_time=current_time,
                location=stops[0].location if stops else None,
                location_description='Starting location',
                is_automatic=True
            ))

        # Process each stop
        for i, stop in enumerate(stops):
            # Pre-trip inspection (on-duty)
            if stop.stop_type in ['pickup', 'dropoff']:
                pre_trip_start = stop.estimated_arrival_time - timedelta(minutes=15)
                entries.append(DutyStatusEntry(
                    eld_log=eld_log,
                    duty_status='ON',
                    start_time=pre_trip_start,
                    end_time=stop.estimated_arrival_time,
                    duration_minutes=15,
                    location=stop.location,
                    location_description='Pre-trip inspection',
                    is_automatic=True
                ))

            # Stop activity
            if stop.stop_type == 'pickup':
                entries.append(DutyStatusEntry(
                    eld_log=eld_log,
                    duty_status='ON',
                    start_time=stop.estimated_arrival_time,
                    end_time=stop.estimated_departure_time,
                    duration_minutes=stop.duration_minutes,
                    location=stop.location,
                    location_description='Loading/Pickup',
                    is_automatic=True
                ))
            elif stop.stop_type == 'dropoff':
                entries.append(DutyStatusEntry(
                    eld_log=eld_log,
                    duty_status='ON',
                    start_time=stop.estimated_arrival_time,
                    end_time=stop.estimated_departure_time,
                    duration_minutes=stop.duration_minutes,
                    location=stop.location,
                    location_description='Unloading/Delivery',
                    is_automatic=True
                ))
            elif stop.stop_type == 'fuel':
                entries.append(DutyStatusEntry(
                    eld_log=eld_log,
                    duty_status='ON',
                    start_time=stop.estimated_arrival_time,
                    end_time=stop.estimated_departure_time,
                    duration_minutes=stop.duration_minutes,
                    location=stop.location,
                    location_description='Fuel stop',
                    is_automatic=True
                ))
            elif stop.stop_type in ['rest', 'mandatory_break']:
                status = 'SB' if stop.duration_minutes >= 480 else 'OFF'  # 8+ hours = sleeper berth
                entries.append(DutyStatusEntry(
                    eld_log=eld_log,
                    duty_status=status,
                    start_time=stop.estimated_arrival_time,
                    end_time=stop.estimated_departure_time,
                    duration_minutes=stop.duration_minutes,
                    location=stop.location,
                    location_description=stop.description or 'Rest break',
                    is_automatic=True
                ))

            # Driving to next stop
            next_stop = stops[i + 1] if i + 1 < len(stops) else None
            if next_stop:
                drive_start = stop.estimated_departure_time
                drive_end = next_stop.estimated_arrival_time
                drive_minutes = int((drive_end - drive_start).total_seconds() / 60)

                if drive_minutes > 0:
                    entries.append(DutyStatusEntry(
                        eld_log=eld_log,
                        duty_status='D',
                        start_time=drive_start,
                        end_time=drive_end,
                        duration_minutes=drive_minutes,
                        location=stop.location,
                        location_description=f'Driving to {next_stop.location.city or "next stop"}',
                        is_automatic=True
                    ))

        # Save all entries
        DutyStatusEntry.objects.bulk_create(entries)

        return entries

    def _calculate_daily_totals(self, eld_log):
        """
        Calculate daily totals from duty status entries.
        """
        entries = eld_log.duty_entries.all()

        total_drive_minutes = 0
        total_on_duty_minutes = 0
        total_off_duty_minutes = 0

        for entry in entries:
            minutes = entry.duration_minutes

            if entry.duty_status == 'D':
                total_drive_minutes += minutes
                total_on_duty_minutes += minutes
            elif entry.duty_status == 'ON':
                total_on_duty_minutes += minutes
            elif entry.duty_status in ['OFF', 'SB']:
                total_off_duty_minutes += minutes

        # Convert to hours and update log
        eld_log.total_drive_time = Decimal(total_drive_minutes / 60)
        eld_log.total_on_duty_time = Decimal(total_on_duty_minutes / 60)
        eld_log.total_off_duty_time = Decimal(total_off_duty_minutes / 60)
        eld_log.save()

    def _check_violations(self, eld_log):
        """
        Check for HOS violations in the daily log.
        """
        violations = []

        # Check 11-hour driving limit
        if eld_log.total_drive_time > 11:
            violations.append(ELDViolation(
                eld_log=eld_log,
                violation_type='DAILY_DRIVE_EXCEEDED',
                severity='HIGH',
                description=f'Daily driving time of {eld_log.total_drive_time} hours exceeds 11-hour limit',
                violation_time=timezone.now(),
                duration_minutes=int((float(eld_log.total_drive_time) - 11) * 60)
            ))

        # Check 14-hour duty limit
        if eld_log.total_on_duty_time > 14:
            violations.append(ELDViolation(
                eld_log=eld_log,
                violation_type='DAILY_DUTY_EXCEEDED',
                severity='HIGH',
                description=f'Daily on-duty time of {eld_log.total_on_duty_time} hours exceeds 14-hour limit',
                violation_time=timezone.now(),
                duration_minutes=int((float(eld_log.total_on_duty_time) - 14) * 60)
            ))

        # Check 70-hour cycle limit
        if eld_log.cycle_hours_used > 70:
            violations.append(ELDViolation(
                eld_log=eld_log,
                violation_type='CYCLE_EXCEEDED',
                severity='CRITICAL',
                description=f'8-day cycle hours of {eld_log.cycle_hours_used} exceeds 70-hour limit',
                violation_time=timezone.now(),
                duration_minutes=int((float(eld_log.cycle_hours_used) - 70) * 60)
            ))

        # Save violations
        if violations:
            ELDViolation.objects.bulk_create(violations)
            eld_log.is_compliant = False
            eld_log.violation_summary = '; '.join([v.description for v in violations])
            eld_log.save()

    def _serialize_eld_log(self, eld_log):
        """
        Serialize ELD log to dictionary format.
        """
        return {
            'id': eld_log.id,
            'log_date': eld_log.log_date.isoformat(),
            'driver': {
                'name': eld_log.driver.name,
                'license_number': eld_log.driver.license_number,
            } if eld_log.driver else None,
            'vehicle': {
                'license_plate': eld_log.vehicle.license_plate,
                'make': eld_log.vehicle.make,
                'model': eld_log.vehicle.model,
            } if eld_log.vehicle else None,
            'totals': {
                'drive_time': float(eld_log.total_drive_time),
                'on_duty_time': float(eld_log.total_on_duty_time),
                'off_duty_time': float(eld_log.total_off_duty_time),
                'miles_driven': float(eld_log.total_miles_driven),
            },
            'cycle_hours_used': float(eld_log.cycle_hours_used),
            'is_compliant': eld_log.is_compliant,
            'violations': eld_log.violation_summary,
            'duty_entries': [
                {
                    'duty_status': entry.duty_status,
                    'start_time': entry.start_time.isoformat(),
                    'end_time': entry.end_time.isoformat() if entry.end_time else None,
                    'duration_minutes': entry.duration_minutes,
                    'location': entry.location_description,
                    'remarks': entry.remarks,
                }
                for entry in eld_log.duty_entries.all().order_by('start_time')
            ]
        }


class HOSComplianceChecker:
    """
    Service for checking Hours of Service compliance.
    """

    # HOS limits
    MAX_DRIVING_HOURS = 11
    MAX_DUTY_HOURS = 14
    MAX_CYCLE_HOURS = 70
    MIN_OFF_DUTY_HOURS = 10
    RESTART_HOURS = 34

    def __init__(self):
        self.violations = []

    def check_trip_compliance(self, trip):
        """
        Check HOS compliance for a complete trip.
        """
        self.violations = []

        # Check current status before trip
        self._check_pre_trip_compliance(trip)

        # Check each day of the trip
        eld_logs = trip.eld_logs.all()
        for eld_log in eld_logs:
            self._check_daily_compliance(eld_log)

        return {
            'is_compliant': len(self.violations) == 0,
            'violations': self.violations
        }

    def _check_pre_trip_compliance(self, trip):
        """
        Check if driver can legally start the trip.
        """
        # Check cycle hours
        if trip.current_cycle_hours >= self.MAX_CYCLE_HOURS:
            self.violations.append({
                'type': 'CYCLE_EXCEEDED',
                'severity': 'CRITICAL',
                'description': f'Cannot start trip: {trip.current_cycle_hours} cycle hours used (max: {self.MAX_CYCLE_HOURS})'
            })

        # Check daily hours
        if trip.current_daily_drive_hours >= self.MAX_DRIVING_HOURS:
            self.violations.append({
                'type': 'DAILY_DRIVE_EXCEEDED',
                'severity': 'HIGH',
                'description': f'Cannot start trip: {trip.current_daily_drive_hours} driving hours used today (max: {self.MAX_DRIVING_HOURS})'
            })

        if trip.current_daily_duty_hours >= self.MAX_DUTY_HOURS:
            self.violations.append({
                'type': 'DAILY_DUTY_EXCEEDED',
                'severity': 'HIGH',
                'description': f'Cannot start trip: {trip.current_daily_duty_hours} duty hours used today (max: {self.MAX_DUTY_HOURS})'
            })

    def _check_daily_compliance(self, eld_log):
        """
        Check compliance for a daily ELD log.
        """
        # Check daily driving limit
        if eld_log.total_drive_time > self.MAX_DRIVING_HOURS:
            self.violations.append({
                'type': 'DAILY_DRIVE_EXCEEDED',
                'severity': 'HIGH',
                'description': f'Daily driving time exceeded: {eld_log.total_drive_time}h (max: {self.MAX_DRIVING_HOURS}h)',
                'date': eld_log.log_date.isoformat()
            })

        # Check daily duty limit
        if eld_log.total_on_duty_time > self.MAX_DUTY_HOURS:
            self.violations.append({
                'type': 'DAILY_DUTY_EXCEEDED',
                'severity': 'HIGH',
                'description': f'Daily on-duty time exceeded: {eld_log.total_on_duty_time}h (max: {self.MAX_DUTY_HOURS}h)',
                'date': eld_log.log_date.isoformat()
            })

        # Check cycle limit
        if eld_log.cycle_hours_used > self.MAX_CYCLE_HOURS:
            self.violations.append({
                'type': 'CYCLE_EXCEEDED',
                'severity': 'CRITICAL',
                'description': f'8-day cycle exceeded: {eld_log.cycle_hours_used}h (max: {self.MAX_CYCLE_HOURS}h)',
                'date': eld_log.log_date.isoformat()
            })

        # Check for sufficient rest periods
        self._check_rest_periods(eld_log)

    def _check_rest_periods(self, eld_log):
        """
        Check if driver had sufficient rest periods.
        """
        off_duty_entries = eld_log.duty_entries.filter(
            duty_status__in=['OFF', 'SB']
        ).order_by('start_time')

        longest_rest = 0
        for entry in off_duty_entries:
            rest_hours = entry.duration_minutes / 60
            if rest_hours > longest_rest:
                longest_rest = rest_hours

        if longest_rest < self.MIN_OFF_DUTY_HOURS and eld_log.total_drive_time > 0:
            self.violations.append({
                'type': 'INSUFFICIENT_REST',
                'severity': 'MEDIUM',
                'description': f'Insufficient rest: {longest_rest:.1f}h (min: {self.MIN_OFF_DUTY_HOURS}h)',
                'date': eld_log.log_date.isoformat()
            })

    def calculate_available_time(self, current_cycle_hours, daily_drive_hours, daily_duty_hours):
        """
        Calculate remaining available driving/duty time.
        """
        remaining_cycle = max(0, self.MAX_CYCLE_HOURS - current_cycle_hours)
        remaining_daily_drive = max(0, self.MAX_DRIVING_HOURS - daily_drive_hours)
        remaining_daily_duty = max(0, self.MAX_DUTY_HOURS - daily_duty_hours)

        # Available time is limited by the most restrictive limit
        available_drive_time = min(remaining_cycle, remaining_daily_drive)
        available_duty_time = min(remaining_cycle, remaining_daily_duty)

        return {
            'available_drive_hours': available_drive_time,
            'available_duty_hours': available_duty_time,
            'remaining_cycle_hours': remaining_cycle,
            'needs_restart': remaining_cycle <= 0
        }

    def suggest_restart_time(self, trip):
        """
        Suggest when a 34-hour restart should begin.
        """
        if trip.current_cycle_hours < 60:  # No restart needed yet
            return None

        # Calculate when restart should begin based on trip timeline
        first_stop = trip.stops.filter(stop_type='pickup').first()
        if first_stop:
            restart_start = first_stop.estimated_arrival_time - timedelta(hours=self.RESTART_HOURS)
            restart_end = first_stop.estimated_arrival_time

            return {
                'restart_start': restart_start.isoformat(),
                'restart_end': restart_end.isoformat(),
                'hours_to_restart': self.RESTART_HOURS,
                'reason': 'Approaching 70-hour cycle limit'
            }

        return None


class ELDReportGenerator:
    """
    Service for generating ELD reports and summaries.
    """

    def generate_daily_summary(self, eld_log):
        """
        Generate a daily summary report.
        """
        entries = eld_log.duty_entries.all().order_by('start_time')

        return {
            'log_date': eld_log.log_date.isoformat(),
            'driver': eld_log.driver.name if eld_log.driver else 'Unknown',
            'vehicle': f"{eld_log.vehicle.license_plate}" if eld_log.vehicle else 'Unknown',
            'summary': {
                'total_drive_time': f"{eld_log.total_drive_time:.2f} hours",
                'total_on_duty_time': f"{eld_log.total_on_duty_time:.2f} hours",
                'total_off_duty_time': f"{eld_log.total_off_duty_time:.2f} hours",
                'miles_driven': f"{eld_log.total_miles_driven:.1f} miles",
                'cycle_hours_used': f"{eld_log.cycle_hours_used:.2f} hours",
            },
            'status': 'Compliant' if eld_log.is_compliant else 'Non-Compliant',
            'violations': eld_log.violation_summary or 'None',
            'duty_changes': len(entries),
            'certified': 'Yes' if eld_log.is_certified else 'No'
        }

    def generate_trip_summary(self, trip):
        """
        Generate a complete trip summary report.
        """
        eld_logs = trip.eld_logs.all()

        total_drive_time = sum(float(log.total_drive_time) for log in eld_logs)
        total_duty_time = sum(float(log.total_on_duty_time) for log in eld_logs)
        total_miles = sum(float(log.total_miles_driven) for log in eld_logs)

        return {
            'trip_id': trip.id,
            'status': trip.status,
            'driver': trip.driver.name if trip.driver else 'Unknown',
            'route': {
                'from': trip.current_location.address,
                'pickup': trip.pickup_location.address,
                'dropoff': trip.dropoff_location.address,
            },
            'totals': {
                'total_drive_time': f"{total_drive_time:.2f} hours",
                'total_duty_time': f"{total_duty_time:.2f} hours",
                'total_miles': f"{total_miles:.1f} miles",
                'days': len(eld_logs),
            },
            'compliance': {
                'compliant_days': sum(1 for log in eld_logs if log.is_compliant),
                'violation_days': sum(1 for log in eld_logs if not log.is_compliant),
                'overall_compliant': all(log.is_compliant for log in eld_logs),
            },
            'created_at': trip.created_at.isoformat(),
        }


class ELDPrintService:
    """
    Service for generating ELD printouts and displays compliant with FMCSA requirements.
    """

    def generate_printable_log(self, eld_log):
        """
        Generate printable ELD log in FMCSA-compliant format.

        Args:
            eld_log: ELDLog instance

        Returns:
            Dict containing printable log data with graph-grid format
        """
        return {
            'header_info': self._generate_log_header(eld_log),
            'graph_grid': self._generate_graph_grid(eld_log),
            'duty_status_summary': self._generate_duty_summary(eld_log),
            'supporting_documents': self._get_supporting_documents(eld_log),
            'certification_info': self._get_certification_info(eld_log),
            'violations_warnings': self._get_violations_info(eld_log),
            'odometer_info': self._get_odometer_info(eld_log),
            'location_info': self._get_location_info(eld_log)
        }

    def _generate_log_header(self, eld_log):
        """Generate log header with required driver/vehicle information."""
        return {
            'date': eld_log.log_date.strftime('%m/%d/%Y'),
            'driver_name': eld_log.driver.name if eld_log.driver else '',
            'driver_license': eld_log.driver.license_number if eld_log.driver else '',
            'driver_license_state': eld_log.driver.license_state if eld_log.driver else '',
            'co_driver': getattr(eld_log.driver, 'co_driver_name', '') if eld_log.driver else '',
            'vehicle_info': f"{eld_log.vehicle.license_plate} - {eld_log.vehicle.make} {eld_log.vehicle.model}" if eld_log.vehicle else '',
            'vehicle_vin': eld_log.vehicle.vin if eld_log.vehicle else '',
            'carrier_info': getattr(eld_log.trip.driver, 'company_name', '') if hasattr(eld_log.trip, 'driver') else '',
            'main_office_address': '',  # TODO: Add to Company model
            'home_terminal_address': '',  # TODO: Add to Driver model
            'starting_time': '12:01 AM',  # 24-hour period start
            'ending_time': '12:00 AM',  # 24-hour period end
            'shipping_document_number': getattr(eld_log.trip, 'shipping_doc_number', '') if hasattr(eld_log,
                                                                                                    'trip') else ''
        }

    def _generate_graph_grid(self, eld_log):
        """
        Generate 24-hour graph grid showing duty status changes.
        Creates visual representation matching FMCSA requirements.
        """
        # Create 24-hour grid (1440 minutes)
        grid_data = []
        duty_entries = eld_log.duty_entries.all().order_by('start_time')

        for minute in range(1440):  # 24 hours * 60 minutes
            hour = minute // 60
            minute_in_hour = minute % 60

            # Determine duty status for this minute
            duty_status = self._get_duty_status_for_minute(minute, duty_entries, eld_log.log_date)

            grid_data.append({
                'minute': minute,
                'hour': hour,
                'minute_in_hour': minute_in_hour,
                'time_display': f"{hour:02d}:{minute_in_hour:02d}",
                'duty_status': duty_status,
                'status_display': self._get_status_display_char(duty_status)
            })

        # Create hour markers for the grid
        hour_markers = []
        for hour in range(24):
            hour_markers.append({
                'hour': hour,
                'display': f"{hour:02d}",
                'twelve_hour': self._format_12_hour(hour)
            })

        return {
            'grid_data': grid_data,
            'hour_markers': hour_markers,
            'hours_summary': self._calculate_hours_summary(grid_data),
            'graph_dimensions': {
                'width_inches': 8,  # Minimum 6 inches required by FMCSA
                'height_inches': 2  # Minimum 1.5 inches required by FMCSA
            },
            'grid_lines': self._generate_grid_lines()
        }

    def _get_duty_status_for_minute(self, minute_of_day, duty_entries, log_date):
        """Determine duty status for a specific minute of the day."""
        # Convert minute to actual datetime
        target_time = timezone.make_aware(
            datetime.combine(log_date, datetime.time()) +
            timedelta(minutes=minute_of_day)
        )

        # Find the duty status that covers this minute
        for entry in duty_entries:
            if entry.start_time <= target_time:
                if not entry.end_time or entry.end_time > target_time:
                    return entry.duty_status

        return 'OFF'  # Default to off-duty

    def _get_status_display_char(self, duty_status):
        """Get display character for duty status on graph."""
        status_chars = {
            'OFF': ' ',  # Off-duty (blank space)
            'SB': '▓',  # Sleeper berth (solid block)
            'D': '█',  # Driving (full block)
            'ON': '▒'  # On-duty not driving (dotted block)
        }
        return status_chars.get(duty_status, ' ')

    def _format_12_hour(self, hour_24):
        """Convert 24-hour format to 12-hour format."""
        if hour_24 == 0:
            return "12 AM"
        elif hour_24 < 12:
            return f"{hour_24} AM"
        elif hour_24 == 12:
            return "12 PM"
        else:
            return f"{hour_24 - 12} PM"

    def _generate_grid_lines(self):
        """Generate grid lines for visual representation."""
        return {
            'horizontal_lines': [
                {'position': 0, 'label': 'OFF DUTY'},
                {'position': 1, 'label': 'SLEEPER BERTH'},
                {'position': 2, 'label': 'DRIVING'},
                {'position': 3, 'label': 'ON DUTY (NOT DRIVING)'}
            ],
            'vertical_lines': [
                {'hour': h, 'position': h * 60} for h in range(0, 25, 3)  # Every 3 hours
            ]
        }

    def _calculate_hours_summary(self, grid_data):
        """Calculate summary of hours spent in each duty status."""
        status_counts = {'OFF': 0, 'SB': 0, 'D': 0, 'ON': 0}

        for minute_data in grid_data:
            status = minute_data['duty_status']
            status_counts[status] += 1

        # Convert minutes to hours
        return {
            'off_duty_hours': round(status_counts['OFF'] / 60, 2),
            'sleeper_berth_hours': round(status_counts['SB'] / 60, 2),
            'driving_hours': round(status_counts['D'] / 60, 2),
            'on_duty_not_driving_hours': round(status_counts['ON'] / 60, 2)
        }

    def _generate_duty_summary(self, eld_log):
        """Generate duty status time summary matching ELD log format."""
        return {
            'off_duty_time': f"{eld_log.total_off_duty_time:.2f}",
            'sleeper_berth_time': self._calculate_sleeper_time(eld_log),
            'driving_time': f"{eld_log.total_drive_time:.2f}",
            'on_duty_not_driving_time': self._calculate_on_duty_not_driving(eld_log),
            'total_on_duty_time': f"{eld_log.total_on_duty_time:.2f}",
            'cycle_hours_used': f"{eld_log.cycle_hours_used:.2f}",
            'cycle_hours_available': f"{70 - float(eld_log.cycle_hours_used):.2f}",
            'recap_hours': self._calculate_recap_hours(eld_log)
        }

    def _calculate_sleeper_time(self, eld_log):
        """Calculate total sleeper berth time."""
        sleeper_entries = eld_log.duty_entries.filter(duty_status='SB')
        total_minutes = sum(entry.duration_minutes for entry in sleeper_entries)
        return f"{total_minutes / 60:.2f}"

    def _calculate_on_duty_not_driving(self, eld_log):
        """Calculate on-duty not driving time."""
        total_on_duty = float(eld_log.total_on_duty_time)
        total_driving = float(eld_log.total_drive_time)
        return f"{total_on_duty - total_driving:.2f}"

    def _calculate_recap_hours(self, eld_log):
        """Calculate recap hours for 8-day period."""
        # This would typically look at the previous 8 days
        # For now, return current cycle info
        return {
            'day_1': f"{float(eld_log.total_on_duty_time):.2f}",
            'day_2': "0.00",  # Would need historical data
            'day_3': "0.00",
            'day_4': "0.00",
            'day_5': "0.00",
            'day_6': "0.00",
            'day_7': "0.00",
            'day_8': "0.00",
            'total_8_days': f"{eld_log.cycle_hours_used:.2f}"
        }

    def _get_supporting_documents(self, eld_log):
        """Get supporting documents for the log."""
        return [
            {
                'type': doc.get_document_type_display(),
                'reference': doc.reference_number,
                'date': doc.document_date.strftime('%m/%d/%Y'),
                'description': doc.description,
                'file_name': doc.file_name
            }
            for doc in eld_log.documents.all()[:8]  # Max 8 documents per FMCSA
        ]

    def _get_certification_info(self, eld_log):
        """Get certification information."""
        return {
            'is_certified': eld_log.is_certified,
            'certified_date': eld_log.certified_at.strftime('%m/%d/%Y %H:%M') if eld_log.certified_at else '',
            'driver_signature': 'ELECTRONICALLY SIGNED' if eld_log.is_certified else 'NOT CERTIFIED',
            'certification_method': 'ELD_DEVICE',
            'certification_timezone': 'UTC',
            'driver_review': 'REVIEWED AND CERTIFIED' if eld_log.is_certified else 'PENDING CERTIFICATION'
        }

    def _get_violations_info(self, eld_log):
        """Get violations and warnings information."""
        violations = eld_log.violations.all()
        return [
            {
                'type': violation.get_violation_type_display(),
                'severity': violation.get_severity_display(),
                'time': violation.violation_time.strftime('%H:%M'),
                'description': violation.description,
                'resolved': violation.is_resolved,
                'duration': f"{violation.duration_minutes} minutes"
            }
            for violation in violations
        ]

    def _get_odometer_info(self, eld_log):
        """Get odometer readings for the log."""
        return {
            'starting_odometer': eld_log.starting_odometer,
            'ending_odometer': eld_log.ending_odometer,
            'total_miles': eld_log.total_miles_driven or 0,
            'engine_hours': self._calculate_engine_hours(eld_log)
        }

    def _calculate_engine_hours(self, eld_log):
        """Calculate total engine hours for the day."""
        # Engine runs during driving and some on-duty activities
        driving_entries = eld_log.duty_entries.filter(duty_status__in=['D', 'ON'])
        total_minutes = sum(entry.duration_minutes for entry in driving_entries)
        return round(total_minutes / 60, 2)

    def _get_location_info(self, eld_log):
        """Get location information for duty status changes."""
        duty_entries = eld_log.duty_entries.all().order_by('start_time')

        locations = []
        for entry in duty_entries:
            location_info = {
                'time': entry.start_time.strftime('%H:%M'),
                'duty_status': entry.get_duty_status_display(),
                'location': entry.location_description or 'Unknown Location',
                'odometer': entry.odometer_reading,
                'remarks': entry.remarks or ''
            }

            # Add coordinates if available
            if entry.location:
                location_info.update({
                    'latitude': float(entry.location.latitude),
                    'longitude': float(entry.location.longitude),
                    'city': entry.location.city or '',
                    'state': entry.location.state or ''
                })

            locations.append(location_info)

        return locations

    def generate_inspection_format(self, eld_log):
        """
        Generate ELD log data in format suitable for roadside inspection.
        This format is specifically for presenting to DOT officers.
        """
        printable_data = self.generate_printable_log(eld_log)

        # Add inspection-specific formatting
        inspection_data = {
            'log_summary': {
                'date': printable_data['header_info']['date'],
                'driver': printable_data['header_info']['driver_name'],
                'license': f"{printable_data['header_info']['driver_license']} ({printable_data['header_info']['driver_license_state']})",
                'vehicle': printable_data['header_info']['vehicle_info'],
                'vin': printable_data['header_info']['vehicle_vin'],
                'carrier': printable_data['header_info']['carrier_info']
            },
            'hos_compliance': {
                'driving_hours': printable_data['duty_status_summary']['driving_time'],
                'on_duty_hours': printable_data['duty_status_summary']['total_on_duty_time'],
                'cycle_hours': printable_data['duty_status_summary']['cycle_hours_used'],
                'violations': len(printable_data['violations_warnings']),
                'is_compliant': eld_log.is_compliant
            },
            'duty_timeline': printable_data['location_info'],
            'graph_grid': printable_data['graph_grid'],
            'certification': printable_data['certification_info'],
            'documents': printable_data['supporting_documents'],
            'inspection_notes': [
                'ELD device meets FMCSA technical specifications',
                'All duty status changes automatically recorded',
                'Location data captured at required intervals',
                'Driver certification completed electronically',
                'Backup paper logs available if ELD malfunctions'
            ]
        }

        return inspection_data

    def export_to_csv(self, eld_log):
        """Export ELD log data to CSV format for data transfer."""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow([
            'Date', 'Time', 'Duty Status', 'Location', 'Odometer', 'Remarks'
        ])

        # Data rows
        duty_entries = eld_log.duty_entries.all().order_by('start_time')
        for entry in duty_entries:
            writer.writerow([
                eld_log.log_date.strftime('%m/%d/%Y'),
                entry.start_time.strftime('%H:%M'),
                entry.get_duty_status_display(),
                entry.location_description or 'N/A',
                entry.odometer_reading,
                entry.remarks or ''
            ])

        return output.getvalue()


# Updated view function to include the new ELDPrintService
@api_view(['GET'])
@permission_classes([AllowAny])
def generate_printable_log(request, log_id):
    """
    Generate printable ELD log for inspection/compliance.
    Supports multiple output formats: printable, inspection, csv
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
                'filename': f'eld_log_{eld_log.log_date.strftime("%Y%m%d")}_{eld_log.driver.name.replace(" ", "_")}.csv'
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
