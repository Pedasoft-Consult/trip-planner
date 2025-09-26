"""
Business logic services for trip planning and management.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.core.models import Location, Driver, Vehicle
from .models import Trip, RouteSegment, Stop, FuelStop
from mapping.services import (
    geocode_address_service,
    calculate_route_service,
    find_fuel_stops_service
)
import logging

logger = logging.getLogger(__name__)


class TripPlanningService:
    """
    Service class for trip planning logic.
    """

    # Constants for HOS rules
    MAX_CYCLE_HOURS = 70
    MAX_DAILY_DRIVE_HOURS = 11
    MAX_DAILY_DUTY_HOURS = 14
    MIN_OFF_DUTY_HOURS = 10
    FUEL_INTERVAL_MILES = 1000
    AVERAGE_SPEED = 60  # mph for estimation

    def __init__(self):
        self.current_time = timezone.now()

    @transaction.atomic
    def create_trip(self, trip_data):
        """
        Create a complete trip with route planning and compliance checks.
        """
        try:
            # Step 1: Geocode all locations
            locations = self._geocode_locations(trip_data)

            # Step 2: Get driver and vehicle if provided
            driver = self._get_driver(trip_data.get('driver_id'))
            vehicle = self._get_vehicle(trip_data.get('vehicle_id'))

            # Step 3: Calculate route
            route_data = self._calculate_route(locations)

            # Step 4: Create trip object
            trip = self._create_trip_object(
                trip_data, locations, driver, vehicle, route_data
            )

            # Step 5: Plan stops (rest, fuel, etc.)
            stops = self._plan_stops(trip, route_data)

            # Step 6: Create route segments
            segments = self._create_route_segments(trip, route_data, stops)

            logger.info(f"Successfully created trip {trip.id}")
            return trip

        except Exception as e:
            logger.error(f"Error in create_trip: {str(e)}")
            raise

    def _geocode_locations(self, trip_data):
        """
        Geocode all trip locations and save to database.
        """
        locations = {}

        for location_type in ['current_location', 'pickup_location', 'dropoff_location']:
            address = trip_data[location_type]

            # Try to find existing location first
            try:
                location = Location.objects.filter(address__iexact=address).first()
                if not location:
                    # Geocode new address
                    location_data = geocode_address_service(address)
                    if location_data:
                        location = Location.objects.create(**location_data)
                    else:
                        raise ValueError(f"Could not geocode address: {address}")

                locations[location_type] = location

            except Exception as e:
                raise ValueError(f"Error geocoding {location_type}: {str(e)}")

        return locations

    def _get_driver(self, driver_id):
        """
        Get driver object if provided.
        """
        if driver_id:
            try:
                return Driver.objects.get(id=driver_id, is_active=True)
            except Driver.DoesNotExist:
                raise ValueError(f"Driver with id {driver_id} not found or inactive")
        return None

    def _get_vehicle(self, vehicle_id):
        """
        Get vehicle object if provided.
        """
        if vehicle_id:
            try:
                return Vehicle.objects.get(id=vehicle_id, is_active=True)
            except Vehicle.DoesNotExist:
                raise ValueError(f"Vehicle with id {vehicle_id} not found or inactive")
        return None

    def _calculate_route(self, locations):
        """
        Calculate route between all locations.
        """
        # Create waypoints for route calculation
        waypoints = [
            (float(locations['current_location'].latitude),
             float(locations['current_location'].longitude)),
            (float(locations['pickup_location'].latitude),
             float(locations['pickup_location'].longitude)),
            (float(locations['dropoff_location'].latitude),
             float(locations['dropoff_location'].longitude)),
        ]

        route_data = calculate_route_service(waypoints)
        if not route_data:
            raise ValueError("Could not calculate route")

        return route_data

    def _create_trip_object(self, trip_data, locations, driver, vehicle, route_data):
        """
        Create the main trip object.
        """
        trip = Trip.objects.create(
            driver=driver,
            vehicle=vehicle,
            current_location=locations['current_location'],
            pickup_location=locations['pickup_location'],
            dropoff_location=locations['dropoff_location'],
            current_cycle_hours=trip_data['current_cycle_hours'],
            current_daily_drive_hours=trip_data.get('current_daily_drive_hours', 0),
            current_daily_duty_hours=trip_data.get('current_daily_duty_hours', 0),
            total_distance_miles=Decimal(str(route_data.get('total_distance', 0))),
            estimated_duration_hours=Decimal(str(route_data.get('total_time', 0))),
            notes=trip_data.get('notes', ''),
            status='planning'
        )

        return trip

    def _plan_stops(self, trip, route_data):
        """
        Plan all stops including rest breaks, fuel stops, and mandatory breaks.
        """
        stops = []
        current_time = self.current_time

        # Add pickup stop
        pickup_stop = self._create_pickup_stop(trip, current_time)
        stops.append(pickup_stop)
        current_time += timedelta(hours=1)  # 1 hour for pickup

        # Calculate if mandatory breaks are needed
        total_distance = float(trip.total_distance_miles)
        estimated_driving_time = total_distance / self.AVERAGE_SPEED

        # Plan fuel stops
        fuel_stops = self._plan_fuel_stops(trip, route_data, current_time)
        stops.extend(fuel_stops)

        # Plan mandatory rest breaks based on HOS
        rest_stops = self._plan_rest_breaks(trip, estimated_driving_time, current_time)
        stops.extend(rest_stops)

        # Add dropoff stop
        final_time = current_time + timedelta(hours=estimated_driving_time)
        dropoff_stop = self._create_dropoff_stop(trip, final_time)
        stops.append(dropoff_stop)

        # Sort stops by sequence and save
        stops.sort(key=lambda x: x.sequence_order)
        Stop.objects.bulk_create(stops)

        return stops

    def _create_pickup_stop(self, trip, arrival_time):
        """
        Create pickup stop.
        """
        return Stop(
            trip=trip,
            location=trip.pickup_location,
            stop_type='pickup',
            sequence_order=1,
            estimated_arrival_time=arrival_time,
            estimated_departure_time=arrival_time + timedelta(hours=1),
            duration_minutes=60,
            is_mandatory=True,
            description='Pickup location'
        )

    def _create_dropoff_stop(self, trip, arrival_time):
        """
        Create dropoff stop.
        """
        return Stop(
            trip=trip,
            location=trip.dropoff_location,
            stop_type='dropoff',
            sequence_order=999,  # Will be reordered later
            estimated_arrival_time=arrival_time,
            estimated_departure_time=arrival_time + timedelta(hours=1),
            duration_minutes=60,
            is_mandatory=True,
            description='Dropoff location'
        )

    def _plan_fuel_stops(self, trip, route_data, start_time):
        """
        Plan fuel stops every 1000 miles.
        """
        stops = []
        total_distance = float(trip.total_distance_miles)

        if total_distance <= self.FUEL_INTERVAL_MILES:
            return stops  # No fuel stops needed

        # Calculate number of fuel stops needed
        num_fuel_stops = int(total_distance // self.FUEL_INTERVAL_MILES)

        for i in range(1, num_fuel_stops + 1):
            # Calculate approximate location for fuel stop
            distance_point = i * self.FUEL_INTERVAL_MILES
            time_offset = (distance_point / self.AVERAGE_SPEED)

            # Create a fuel stop location (simplified - would use real fuel stop finder)
            fuel_location = self._find_fuel_stop_location(trip, distance_point)

            stop = Stop(
                trip=trip,
                location=fuel_location,
                stop_type='fuel',
                sequence_order=i + 1,  # After pickup
                estimated_arrival_time=start_time + timedelta(hours=time_offset),
                estimated_departure_time=start_time + timedelta(hours=time_offset + 0.5),
                duration_minutes=30,
                is_mandatory=False,
                description=f'Fuel stop #{i}'
            )
            stops.append(stop)

        return stops

    def _find_fuel_stop_location(self, trip, distance_point):
        """
        Find a suitable fuel stop location at the given distance point.
        This is simplified - in production, would use real truck stop APIs.
        """
        # For now, create a generic fuel stop location
        # In production, this would call find_fuel_stops_service()
        fuel_location = Location.objects.create(
            address=f"Fuel Stop at mile {distance_point}",
            latitude=trip.pickup_location.latitude,  # Simplified
            longitude=trip.pickup_location.longitude,
            city="Fuel City",
            state="FS"
        )
        return fuel_location

    def _plan_rest_breaks(self, trip, driving_time, start_time):
        """
        Plan mandatory rest breaks based on Hours of Service rules.
        """
        stops = []
        current_cycle = float(trip.current_cycle_hours)
        current_daily_drive = float(trip.current_daily_drive_hours)
        current_daily_duty = float(trip.current_daily_duty_hours)

        # Check if 34-hour restart is needed
        if current_cycle + driving_time > self.MAX_CYCLE_HOURS:
            restart_stop = self._create_restart_break(trip, start_time)
            stops.append(restart_stop)

        # Check if daily limits require breaks
        remaining_drive_time = self.MAX_DAILY_DRIVE_HOURS - current_daily_drive
        remaining_duty_time = self.MAX_DAILY_DUTY_HOURS - current_daily_duty

        if driving_time > remaining_drive_time or driving_time > remaining_duty_time:
            # Need mandatory 10-hour break
            break_time = start_time + timedelta(hours=min(remaining_drive_time, remaining_duty_time))
            mandatory_break = Stop(
                trip=trip,
                location=trip.pickup_location,  # Simplified location
                stop_type='mandatory_break',
                sequence_order=50,  # Will be reordered
                estimated_arrival_time=break_time,
                estimated_departure_time=break_time + timedelta(hours=10),
                duration_minutes=600,  # 10 hours
                is_mandatory=True,
                description='Mandatory 10-hour rest break'
            )
            stops.append(mandatory_break)

        return stops

    def _create_restart_break(self, trip, start_time):
        """
        Create a 34-hour restart break.
        """
        return Stop(
            trip=trip,
            location=trip.pickup_location,  # Simplified location
            stop_type='mandatory_break',
            sequence_order=10,  # Early in sequence
            estimated_arrival_time=start_time,
            estimated_departure_time=start_time + timedelta(hours=34),
            duration_minutes=2040,  # 34 hours
            is_mandatory=True,
            description='34-hour restart break'
        )

    def _create_route_segments(self, trip, route_data, stops):
        """
        Create route segments between stops.
        """
        segments = []
        segments_data = route_data.get('segments', [])

        for i, segment_data in enumerate(segments_data):
            segment = RouteSegment(
                trip=trip,
                start_location=trip.pickup_location if i == 0 else trip.pickup_location,  # Simplified
                end_location=trip.dropoff_location if i == len(segments_data) - 1 else trip.dropoff_location,
                sequence_order=i + 1,
                distance_miles=Decimal(str(segment_data.get('distance', 0))),
                estimated_time_hours=Decimal(str(segment_data.get('time', 0))),
                geometry=segment_data.get('geometry')
            )
            segments.append(segment)

        RouteSegment.objects.bulk_create(segments)
        return segments


class HOSComplianceService:
    """
    Service for Hours of Service compliance calculations.
    """

    @staticmethod
    def can_drive(current_cycle_hours, daily_drive_hours, daily_duty_hours):
        """
        Check if driver can legally drive.
        """
        if current_cycle_hours >= 70:
            return False, "70-hour cycle limit reached"

        if daily_drive_hours >= 11:
            return False, "11-hour daily drive limit reached"

        if daily_duty_hours >= 14:
            return False, "14-hour daily duty limit reached"

        return True, "Can drive"

    @staticmethod
    def calculate_available_hours(current_cycle_hours, daily_drive_hours, daily_duty_hours):
        """
        Calculate remaining available hours.
        """
        remaining_cycle = max(0, 70 - current_cycle_hours)
        remaining_daily_drive = max(0, 11 - daily_drive_hours)
        remaining_daily_duty = max(0, 14 - daily_duty_hours)

        return {
            'cycle_hours': remaining_cycle,
            'daily_drive_hours': remaining_daily_drive,
            'daily_duty_hours': remaining_daily_duty
        }
