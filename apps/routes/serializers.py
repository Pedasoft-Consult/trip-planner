"""
Serializers for the routes app.
"""
from rest_framework import serializers
from apps.core.serializers import LocationSerializer
from .models import RouteTemplate, RouteWaypoint, RestArea, RouteAlert


class RouteWaypointSerializer(serializers.ModelSerializer):
    """
    Serializer for RouteWaypoint model.
    """
    location = LocationSerializer(read_only=True)

    class Meta:
        model = RouteWaypoint
        fields = [
            'id', 'location', 'sequence_order', 'waypoint_type',
            'stop_duration_minutes', 'is_mandatory', 'created_at'
        ]


class RouteTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for RouteTemplate model.
    """
    start_location = LocationSerializer(read_only=True)
    end_location = LocationSerializer(read_only=True)
    waypoints = RouteWaypointSerializer(many=True, read_only=True)

    class Meta:
        model = RouteTemplate
        fields = [
            'id', 'name', 'description', 'start_location', 'end_location',
            'total_distance_miles', 'estimated_time_hours', 'average_speed',
            'avoid_tolls', 'truck_route', 'times_used', 'last_used',
            'geometry', 'is_active', 'waypoints', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'times_used', 'last_used', 'created_at', 'updated_at']


class RestAreaSerializer(serializers.ModelSerializer):
    """
    Serializer for RestArea model.
    """
    location = LocationSerializer(read_only=True)

    class Meta:
        model = RestArea
        fields = [
            'id', 'location', 'name', 'brand', 'phone',
            'truck_parking_spaces', 'car_parking_spaces',
            'is_24_hours', 'opening_time', 'closing_time',
            'amenities', 'rating', 'review_count',
            'diesel_price', 'price_updated', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RouteAlertSerializer(serializers.ModelSerializer):
    """
    Serializer for RouteAlert model.
    """
    location = LocationSerializer(read_only=True)
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)

    class Meta:
        model = RouteAlert
        fields = [
            'id', 'location', 'alert_type', 'alert_type_display',
            'severity', 'severity_display', 'title', 'description',
            'start_time', 'end_time', 'expected_duration_hours',
            'estimated_delay_minutes', 'affects_trucks',
            'source', 'external_id', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RouteCalculationSerializer(serializers.Serializer):
    """
    Serializer for route calculation requests.
    """
    waypoints = serializers.ListField(
        child=serializers.DictField(),
        min_length=2,
        help_text="List of waypoint objects with lat/lng coordinates"
    )
    avoid_tolls = serializers.BooleanField(default=False)
    truck_route = serializers.BooleanField(default=True)

    def validate_waypoints(self, value):
        """
        Validate waypoint format.
        """
        for waypoint in value:
            if not isinstance(waypoint, dict):
                raise serializers.ValidationError("Each waypoint must be a dictionary")

            # Check for required coordinate fields
            lat_keys = ['latitude', 'lat']
            lng_keys = ['longitude', 'lng', 'lon']

            has_lat = any(key in waypoint for key in lat_keys)
            has_lng = any(key in waypoint for key in lng_keys)

            if not has_lat or not has_lng:
                raise serializers.ValidationError(
                    "Each waypoint must have latitude and longitude coordinates"
                )

        return value


class RouteOptimizationSerializer(serializers.Serializer):
    """
    Serializer for route optimization requests.
    """
    stops = serializers.ListField(
        child=serializers.DictField(),
        min_length=3,
        help_text="List of stops to optimize"
    )
    start_location = serializers.DictField(required=False)
    end_location = serializers.DictField(required=False)
    optimization_type = serializers.ChoiceField(
        choices=[
            ('distance', 'Minimize Distance'),
            ('time', 'Minimize Time'),
            ('fuel', 'Minimize Fuel Cost'),
        ],
        default='time'
    )


class TrafficDataSerializer(serializers.Serializer):
    """
    Serializer for traffic data responses.
    """
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    traffic_status = serializers.ChoiceField(
        choices=[
            ('light', 'Light Traffic'),
            ('moderate', 'Moderate Traffic'),
            ('heavy', 'Heavy Traffic'),
            ('severe', 'Severe Congestion'),
        ]
    )
    average_speed = serializers.FloatField()
    congestion_level = serializers.ChoiceField(
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('extreme', 'Extreme'),
        ]
    )
    estimated_delay_minutes = serializers.IntegerField(default=0)


class TruckRestrictionSerializer(serializers.Serializer):
    """
    Serializer for truck restriction responses.
    """
    height_restrictions = serializers.ListField(
        child=serializers.DictField(),
        default=list
    )
    weight_restrictions = serializers.ListField(
        child=serializers.DictField(),
        default=list
    )
    hazmat_restrictions = serializers.ListField(
        child=serializers.DictField(),
        default=list
    )
    bridge_restrictions = serializers.ListField(
        child=serializers.DictField(),
        default=list
    )
    tunnel_restrictions = serializers.ListField(
        child=serializers.DictField(),
        default=list
    )
    warnings = serializers.ListField(
        child=serializers.CharField(),
        default=list
    )
