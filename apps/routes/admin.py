"""
Admin configuration for the routes app.
"""
from django.contrib import admin
from .models import RouteTemplate, RouteWaypoint, RestArea, RouteAlert


class RouteWaypointInline(admin.TabularInline):
    model = RouteWaypoint
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


@admin.register(RouteTemplate)
class RouteTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'start_location', 'end_location',
        'total_distance_miles', 'estimated_time_hours',
        'times_used', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'truck_route', 'avoid_tolls', 'created_at']
    search_fields = ['name', 'description', 'start_location__address', 'end_location__address']
    readonly_fields = ['times_used', 'last_used', 'created_at', 'updated_at']
    inlines = [RouteWaypointInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Route Details', {
            'fields': (
                'start_location', 'end_location', 'total_distance_miles',
                'estimated_time_hours', 'average_speed'
            )
        }),
        ('Preferences', {
            'fields': ('avoid_tolls', 'truck_route')
        }),
        ('Usage Statistics', {
            'fields': ('times_used', 'last_used'),
            'classes': ('collapse',)
        }),
        ('Advanced', {
            'fields': ('geometry', 'is_active'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RouteWaypoint)
class RouteWaypointAdmin(admin.ModelAdmin):
    list_display = [
        'route_template', 'sequence_order', 'waypoint_type',
        'location', 'stop_duration_minutes', 'is_mandatory'
    ]
    list_filter = ['waypoint_type', 'is_mandatory', 'created_at']
    search_fields = ['route_template__name', 'location__address']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(RestArea)
class RestAreaAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'location', 'brand', 'truck_parking_spaces',
        'is_24_hours', 'rating', 'is_active'
    ]
    list_filter = [
        'is_24_hours', 'is_active', 'brand', 'rating',
        'location__state', 'created_at'
    ]
    search_fields = ['name', 'brand', 'location__address', 'location__city']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'brand', 'location', 'phone')
        }),
        ('Capacity', {
            'fields': ('truck_parking_spaces', 'car_parking_spaces')
        }),
        ('Operating Hours', {
            'fields': ('is_24_hours', 'opening_time', 'closing_time')
        }),
        ('Amenities & Services', {
            'fields': ('amenities',)
        }),
        ('Reviews & Ratings', {
            'fields': ('rating', 'review_count'),
            'classes': ('collapse',)
        }),
        ('Fuel Pricing', {
            'fields': ('diesel_price', 'price_updated'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RouteAlert)
class RouteAlertAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'alert_type', 'severity', 'location',
        'start_time', 'end_time', 'affects_trucks', 'is_active'
    ]
    list_filter = [
        'alert_type', 'severity', 'affects_trucks', 'is_active',
        'start_time', 'source'
    ]
    search_fields = ['title', 'description', 'location__address', 'source']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Alert Information', {
            'fields': ('title', 'alert_type', 'severity', 'description')
        }),
        ('Location & Impact', {
            'fields': (
                'location', 'affects_trucks', 'estimated_delay_minutes'
            )
        }),
        ('Timing', {
            'fields': (
                'start_time', 'end_time', 'expected_duration_hours'
            )
        }),
        ('Source Information', {
            'fields': ('source', 'external_id'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('location')
