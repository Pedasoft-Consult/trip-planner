"""
Trip models for the ELD Trip Planner application.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import BaseModel, Location, Driver, Vehicle


class Trip(BaseModel):
    """
    Main trip model that stores trip planning information.
    """
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='trips'
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='trips'
    )

    current_location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='trips_as_current'
    )
    pickup_location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='trips_as_pickup'
    )
    dropoff_location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='trips_as_dropoff'
    )

    # Hours of Service tracking
    current_cycle_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(70)],
        help_text="Current hours used in 8-day cycle (0-70)"
    )
    current_daily_drive_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(11)],
        help_text="Daily driving hours used (0-11)"
    )
    current_daily_duty_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(14)],
        help_text="Daily on-duty hours used (0-14)"
    )

    # Trip details
    total_distance_miles = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    estimated_duration_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    estimated_fuel_cost = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planning'
    )

    # Metadata
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'trips_trip'
        ordering = ['-created_at']

    def __str__(self):
        return f"Trip {self.id} - {self.status}"


class RouteSegment(BaseModel):
    """
    Individual segments of a route between two points.
    """
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='route_segments'
    )

    start_location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='segments_as_start'
    )
    end_location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='segments_as_end'
    )

    sequence_order = models.PositiveIntegerField()
    distance_miles = models.DecimalField(max_digits=8, decimal_places=2)
    estimated_time_hours = models.DecimalField(max_digits=5, decimal_places=2)

    # Route geometry (optional, for map display)
    geometry = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'trips_route_segment'
        ordering = ['trip', 'sequence_order']
        unique_together = ['trip', 'sequence_order']

    def __str__(self):
        return f"Segment {self.sequence_order} for Trip {self.trip.id}"


class Stop(BaseModel):
    """
    Planned stops along the route (rest, fuel, etc.).
    """
    STOP_TYPES = [
        ('rest', 'Rest Break'),
        ('fuel', 'Fuel Stop'),
        ('pickup', 'Pickup'),
        ('dropoff', 'Dropoff'),
        ('mandatory_break', 'Mandatory Break'),
        ('meal', 'Meal Break'),
    ]

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='stops'
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='stops'
    )

    stop_type = models.CharField(max_length=20, choices=STOP_TYPES)
    sequence_order = models.PositiveIntegerField()

    # Timing
    estimated_arrival_time = models.DateTimeField()
    estimated_departure_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()

    # Stop details
    is_mandatory = models.BooleanField(default=False)
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'trips_stop'
        ordering = ['trip', 'sequence_order']
        unique_together = ['trip', 'sequence_order']

    def __str__(self):
        return f"{self.get_stop_type_display()} - {self.location}"


class FuelStop(BaseModel):
    """
    Specific fuel stop information with pricing and amenities.
    """
    stop = models.OneToOneField(
        Stop,
        on_delete=models.CASCADE,
        related_name='fuel_details'
    )

    # Fuel information
    diesel_price_per_gallon = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        null=True,
        blank=True
    )
    estimated_fuel_gallons = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    estimated_fuel_cost = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Amenities
    has_parking = models.BooleanField(default=True)
    has_restrooms = models.BooleanField(default=True)
    has_food = models.BooleanField(default=False)
    has_showers = models.BooleanField(default=False)
    has_truck_wash = models.BooleanField(default=False)

    # Station details
    station_name = models.CharField(max_length=100, blank=True)
    station_brand = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'trips_fuel_stop'

    def __str__(self):
        return f"Fuel Stop - {self.station_name or self.stop.location}"
