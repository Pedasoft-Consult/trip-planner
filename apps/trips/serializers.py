"""
Serializers for the trips app.
"""
from rest_framework import serializers
from apps.core.serializers import LocationSerializer, DriverSerializer, VehicleSerializer
from .models import Trip, RouteSegment, Stop, FuelStop


class FuelStopSerializer(serializers.ModelSerializer):
    """
    Serializer for FuelStop model.
    """

    class Meta:
        model = FuelStop
        fields = [
            'id', 'diesel_price_per_gallon', 'estimated_fuel_gallons',
            'estimated_fuel_cost', 'has_parking', 'has_restrooms',
            'has_food', 'has_showers', 'has_truck_wash',
            'station_name', 'station_brand'
        ]


class StopSerializer(serializers.ModelSerializer):
    """
    Serializer for Stop model.
    """
    location = LocationSerializer(read_only=True)
    fuel_details = FuelStopSerializer(read_only=True)

    class Meta:
        model = Stop
        fields = [
            'id', 'stop_type', 'sequence_order', 'location',
            'estimated_arrival_time', 'estimated_departure_time',
            'duration_minutes', 'is_mandatory', 'description',
            'fuel_details', 'created_at'
        ]


class RouteSegmentSerializer(serializers.ModelSerializer):
    """
    Serializer for RouteSegment model.
    """
    start_location = LocationSerializer(read_only=True)
    end_location = LocationSerializer(read_only=True)

    class Meta:
        model = RouteSegment
        fields = [
            'id', 'sequence_order', 'start_location', 'end_location',
            'distance_miles', 'estimated_time_hours', 'geometry'
        ]


class TripSerializer(serializers.ModelSerializer):
    """
    Serializer for Trip model with all related data.
    """
    driver = DriverSerializer(read_only=True)
    vehicle = VehicleSerializer(read_only=True)
    current_location = LocationSerializer(read_only=True)
    pickup_location = LocationSerializer(read_only=True)
    dropoff_location = LocationSerializer(read_only=True)
    route_segments = RouteSegmentSerializer(many=True, read_only=True)
    stops = StopSerializer(many=True, read_only=True)

    class Meta:
        model = Trip
        fields = [
            'id', 'driver', 'vehicle', 'current_location',
            'pickup_location', 'dropoff_location',
            'current_cycle_hours', 'current_daily_drive_hours',
            'current_daily_duty_hours', 'total_distance_miles',
            'estimated_duration_hours', 'estimated_fuel_cost',
            'status', 'notes', 'route_segments', 'stops',
            'created_at', 'updated_at'
        ]


class TripCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new trip with address inputs.
    """
    current_location = serializers.CharField(max_length=500)
    pickup_location = serializers.CharField(max_length=500)
    dropoff_location = serializers.CharField(max_length=500)
    current_cycle_hours = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=70
    )
    current_daily_drive_hours = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=0,
        max_value=11,
        default=0
    )
    current_daily_duty_hours = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=0,
        max_value=14,
        default=0
    )
    driver_id = serializers.IntegerField(required=False)
    vehicle_id = serializers.IntegerField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """
        Validate trip data for HOS compliance.
        """
        cycle_hours = data.get('current_cycle_hours', 0)
        daily_drive = data.get('current_daily_drive_hours', 0)
        daily_duty = data.get('current_daily_duty_hours', 0)

        if cycle_hours >= 70:
            raise serializers.ValidationError(
                "Cannot start trip with 70 or more cycle hours. 34-hour restart required."
            )

        if daily_drive >= 11:
            raise serializers.ValidationError(
                "Cannot start trip with 11 or more daily driving hours."
            )

        if daily_duty >= 14:
            raise serializers.ValidationError(
                "Cannot start trip with 14 or more daily on-duty hours."
            )

        if daily_drive > daily_duty:
            raise serializers.ValidationError(
                "Daily driving hours cannot exceed daily on-duty hours."
            )

        return data


class TripSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for trip lists.
    """
    current_location_address = serializers.CharField(
        source='current_location.address', read_only=True
    )
    pickup_location_address = serializers.CharField(
        source='pickup_location.address', read_only=True
    )
    dropoff_location_address = serializers.CharField(
        source='dropoff_location.address', read_only=True
    )
    driver_name = serializers.CharField(
        source='driver.name', read_only=True
    )

    class Meta:
        model = Trip
        fields = [
            'id', 'status', 'current_location_address',
            'pickup_location_address', 'dropoff_location_address',
            'driver_name', 'total_distance_miles', 'estimated_duration_hours',
            'created_at'
        ]
