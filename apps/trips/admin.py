"""
Admin configuration for the trips app.
"""
from django.contrib import admin
from .models import Trip, RouteSegment, Stop, FuelStop


class RouteSegmentInline(admin.TabularInline):
    model = RouteSegment
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


class StopInline(admin.TabularInline):
    model = Stop
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


class FuelStopInline(admin.StackedInline):
    model = FuelStop
    extra = 0


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'status', 'driver', 'total_distance_miles',
        'estimated_duration_hours', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'updated_at']
    search_fields = ['driver__name', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [RouteSegmentInline, StopInline]

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'driver', 'vehicle', 'status', 'notes'
            )
        }),
        ('Locations', {
            'fields': (
                'current_location', 'pickup_location', 'dropoff_location'
            )
        }),
        ('Hours of Service', {
            'fields': (
                'current_cycle_hours', 'current_daily_drive_hours',
                'current_daily_duty_hours'
            )
        }),
        ('Trip Details', {
            'fields': (
                'total_distance_miles', 'estimated_duration_hours',
                'estimated_fuel_cost'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RouteSegment)
class RouteSegmentAdmin(admin.ModelAdmin):
    list_display = [
        'trip', 'sequence_order', 'distance_miles',
        'estimated_time_hours', 'created_at'
    ]
    list_filter = ['created_at', 'trip__status']
    search_fields = ['trip__id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = [
        'trip', 'stop_type', 'sequence_order',
        'estimated_arrival_time', 'is_mandatory'
    ]
    list_filter = ['stop_type', 'is_mandatory', 'created_at']
    search_fields = ['trip__id', 'description', 'location__address']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [FuelStopInline]


@admin.register(FuelStop)
class FuelStopAdmin(admin.ModelAdmin):
    list_display = [
        'stop', 'station_name', 'diesel_price_per_gallon',
        'estimated_fuel_cost', 'has_parking'
    ]
    list_filter = ['has_parking', 'has_restrooms', 'has_food']
    search_fields = ['station_name', 'station_brand', 'stop__trip__id']
