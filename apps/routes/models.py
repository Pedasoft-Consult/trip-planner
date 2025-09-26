"""
Route-specific models for advanced routing features.
"""
from django.db import models
from apps.core.models import BaseModel, Location


class RouteTemplate(BaseModel):
    """
    Saved route templates for commonly used routes.
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Route points
    start_location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='route_templates_as_start'
    )
    end_location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='route_templates_as_end'
    )

    # Route characteristics
    total_distance_miles = models.DecimalField(max_digits=8, decimal_places=2)
    estimated_time_hours = models.DecimalField(max_digits=6, decimal_places=2)
    average_speed = models.DecimalField(max_digits=4, decimal_places=1, default=60)

    # Route preferences
    avoid_tolls = models.BooleanField(default=False)
    truck_route = models.BooleanField(default=True)

    # Usage tracking
    times_used = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)

    # Route geometry (stored as GeoJSON)
    geometry = models.JSONField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'routes_template'
        ordering = ['-times_used', 'name']

    def __str__(self):
        return self.name


class RouteWaypoint(BaseModel):
    """
    Waypoints along a route template.
    """
    route_template = models.ForeignKey(
        RouteTemplate,
        on_delete=models.CASCADE,
        related_name='waypoints'
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='route_waypoints'
    )

    sequence_order = models.PositiveIntegerField()
    waypoint_type = models.CharField(
        max_length=20,
        choices=[
            ('start', 'Start Point'),
            ('waypoint', 'Waypoint'),
            ('fuel', 'Fuel Stop'),
            ('rest', 'Rest Area'),
            ('end', 'End Point'),
        ],
        default='waypoint'
    )

    # Stop duration if applicable
    stop_duration_minutes = models.PositiveIntegerField(default=0)
    is_mandatory = models.BooleanField(default=False)

    class Meta:
        db_table = 'routes_waypoint'
        ordering = ['route_template', 'sequence_order']
        unique_together = ['route_template', 'sequence_order']

    def __str__(self):
        return f"{self.route_template.name} - {self.get_waypoint_type_display()}"


class RestArea(BaseModel):
    """
    Information about truck rest areas and stops.
    """
    AMENITY_CHOICES = [
        ('PARKING', 'Truck Parking'),
        ('FUEL', 'Fuel Station'),
        ('RESTROOMS', 'Restrooms'),
        ('FOOD', 'Food Service'),
        ('SHOWERS', 'Shower Facilities'),
        ('LAUNDRY', 'Laundry'),
        ('WIFI', 'WiFi'),
        ('ATM', 'ATM'),
        ('TRUCK_WASH', 'Truck Wash'),
        ('SCALES', 'Truck Scales'),
        ('MAINTENANCE', 'Maintenance'),
    ]

    location = models.OneToOneField(
        Location,
        on_delete=models.CASCADE,
        related_name='rest_area'
    )

    # Basic information
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    # Capacity
    truck_parking_spaces = models.PositiveIntegerField(default=0)
    car_parking_spaces = models.PositiveIntegerField(default=0)

    # Operating hours
    is_24_hours = models.BooleanField(default=True)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)

    # Amenities (stored as JSON array)
    amenities = models.JSONField(default=list)

    # Ratings and reviews
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    review_count = models.PositiveIntegerField(default=0)

    # Fuel pricing (if applicable)
    diesel_price = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    price_updated = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'routes_rest_area'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.location.city}, {self.location.state}"


class RouteAlert(BaseModel):
    """
    Real-time alerts and notifications for routes.
    """
    ALERT_TYPES = [
        ('CONSTRUCTION', 'Construction'),
        ('ACCIDENT', 'Accident'),
        ('WEATHER', 'Weather Alert'),
        ('ROAD_CLOSURE', 'Road Closure'),
        ('TRAFFIC_JAM', 'Traffic Jam'),
        ('FUEL_SHORTAGE', 'Fuel Shortage'),
        ('INSPECTION', 'DOT Inspection'),
        ('OTHER', 'Other'),
    ]

    SEVERITY_LEVELS = [
        ('LOW', 'Low'),
        ('MODERATE', 'Moderate'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='route_alerts'
    )

    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)

    title = models.CharField(max_length=200)
    description = models.TextField()

    # Time information
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    expected_duration_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True)

    # Impact
    estimated_delay_minutes = models.PositiveIntegerField(default=0)
    affects_trucks = models.BooleanField(default=True)

    # Source information
    source = models.CharField(max_length=100, blank=True)  # DOT, 511, etc.
    external_id = models.CharField(max_length=100, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'routes_alert'
        ordering = ['-start_time', '-severity']
        indexes = [
            models.Index(fields=['location', 'is_active']),
            models.Index(fields=['start_time', 'end_time']),
        ]

    def __str__(self):
        return f"{self.get_alert_type_display()}: {self.title}"
