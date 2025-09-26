"""
Enhanced admin configuration for the core app models with ELD compliance.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from .models import (
    Location, Driver, Vehicle, Company,
    DutyStatusEntry, LocationTrackingEntry, ELDDocument,
    DailyDocumentSummary, ELDComplianceAlert, ELDDataTransferLog
)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['address', 'city', 'state', 'country', 'created_at']
    list_filter = ['state', 'country', 'created_at']
    search_fields = ['address', 'city', 'state', 'postal_code']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Address Information', {
            'fields': ('address', 'city', 'state', 'country', 'postal_code')
        }),
        ('Coordinates', {
            'fields': ('latitude', 'longitude')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'license_number', 'license_state', 'current_duty_status',
        'can_drive_indicator', 'current_cycle_hours', 'is_active', 'last_certification'
    ]
    list_filter = [
        'license_state', 'is_active', 'current_duty_status',
        'certification_method', 'carrier_name', 'created_at'
    ]
    search_fields = [
        'name', 'license_number', 'email', 'employee_id',
        'carrier_name', 'co_driver_name', 'carrier_usdot_number'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'last_certification_date',
        'last_duty_change_time', 'available_hours_display'
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': (
                ('name', 'co_driver_name'),
                ('license_number', 'license_state'),
                ('phone', 'email'),
                ('employee_id', 'is_active')
            )
        }),
        ('Carrier Information', {
            'fields': (
                ('carrier_name', 'carrier_usdot_number'),
                'shipping_document_number'
            )
        }),
        ('Terminal Information', {
            'fields': (
                'home_terminal_address',
                'home_terminal_timezone'
            ),
            'classes': ('collapse',)
        }),
        ('ELD Device', {
            'fields': (
                ('eld_device_id', 'eld_device_model')
            )
        }),
        ('Current Status', {
            'fields': (
                ('current_duty_status', 'last_duty_change_time'),
                'last_duty_change_location'
            )
        }),
        ('Hours of Service', {
            'fields': (
                ('current_cycle_hours', 'current_daily_drive_hours', 'current_daily_duty_hours'),
                'available_hours_display'
            )
        }),
        ('Certification', {
            'fields': (
                ('certification_method', 'last_certification_date'),
                'driver_signature'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['certify_logs', 'reset_daily_hours', 'activate_drivers', 'deactivate_drivers']

    def can_drive_indicator(self, obj):
        """Display can drive status with color indicator."""
        can_drive, reason = obj.can_drive()
        if can_drive:
            return format_html(
                '<span style="color: green; font-weight: bold;">Can Drive</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">{}</span>',
                reason
            )

    can_drive_indicator.short_description = 'Drive Status'

    def last_certification(self, obj):
        """Display last certification date."""
        if obj.last_certification_date:
            return obj.last_certification_date.strftime('%m/%d/%Y %H:%M')
        return 'Never'

    last_certification.short_description = 'Last Certified'

    def available_hours_display(self, obj):
        """Display available hours calculation."""
        cycle_remaining = max(0, 70 - float(obj.current_cycle_hours))
        drive_remaining = max(0, 11 - float(obj.current_daily_drive_hours))
        duty_remaining = max(0, 14 - float(obj.current_daily_duty_hours))

        return format_html(
            '<strong>Cycle:</strong> {:.1f}h | <strong>Drive:</strong> {:.1f}h | <strong>Duty:</strong> {:.1f}h',
            cycle_remaining, drive_remaining, duty_remaining
        )

    available_hours_display.short_description = 'Available Hours'

    def certify_logs(self, request, queryset):
        """Action to certify logs for selected drivers."""
        count = 0
        for driver in queryset:
            driver.certify_logs()
            count += 1
        self.message_user(request, f'Certified logs for {count} drivers.')

    certify_logs.short_description = 'Certify ELD logs for selected drivers'

    def reset_daily_hours(self, request, queryset):
        """Action to reset daily hours (use carefully)."""
        queryset.update(
            current_daily_drive_hours=0,
            current_daily_duty_hours=0
        )
        self.message_user(request, f'Reset daily hours for {queryset.count()} drivers.')

    reset_daily_hours.short_description = 'Reset daily hours (CAUTION)'

    def activate_drivers(self, request, queryset):
        """Activate selected drivers."""
        queryset.update(is_active=True)
        self.message_user(request, f'Activated {queryset.count()} drivers.')

    activate_drivers.short_description = 'Activate selected drivers'

    def deactivate_drivers(self, request, queryset):
        """Deactivate selected drivers."""
        queryset.update(is_active=False)
        self.message_user(request, f'Deactivated {queryset.count()} drivers.')

    deactivate_drivers.short_description = 'Deactivate selected drivers'


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = [
        'license_plate', 'make', 'model', 'year', 'vehicle_number',
        'current_odometer', 'eld_connection_status', 'is_active', 'created_at'
    ]
    list_filter = [
        'make', 'year', 'is_active', 'vehicle_type',
        'eld_connection_type', 'license_state', 'created_at'
    ]
    search_fields = [
        'vin', 'license_plate', 'make', 'model', 'vehicle_number',
        'engine_serial_number', 'eld_device_id'
    ]
    readonly_fields = ['created_at', 'updated_at', 'vehicle_info_display']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                ('license_plate', 'license_state'),
                ('make', 'model', 'year'),
                ('vehicle_number', 'is_active')
            )
        }),
        ('Vehicle Identification', {
            'fields': (
                'vin',
                ('gvwr', 'vehicle_type')
            )
        }),
        ('Engine Information', {
            'fields': (
                ('engine_serial_number', 'engine_model')
            ),
            'classes': ('collapse',)
        }),
        ('Performance Data', {
            'fields': (
                ('fuel_capacity', 'mpg'),
                ('current_odometer', 'current_engine_hours')
            )
        }),
        ('ELD Connection', {
            'fields': (
                ('eld_device_id', 'eld_connection_type')
            )
        }),
        ('Vehicle Info', {
            'fields': ('vehicle_info_display',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['activate_vehicles', 'deactivate_vehicles']

    def eld_connection_status(self, obj):
        """Display ELD connection status."""
        if obj.eld_device_id:
            return format_html(
                '<span style="color: green;">Connected</span><br>'
                '<small>{}</small>',
                obj.eld_device_id
            )
        else:
            return format_html('<span style="color: red;">Not Connected</span>')

    eld_connection_status.short_description = 'ELD Status'

    def vehicle_info_display(self, obj):
        """Display formatted vehicle information."""
        info = obj.get_vehicle_identification()
        return format_html(
            '<strong>VIN:</strong> {}<br>'
            '<strong>Odometer:</strong> {:,} miles<br>'
            '<strong>Engine Hours:</strong> {:.1f}h',
            info['vin'],
            info['current_odometer'],
            info['engine_hours']
        )

    vehicle_info_display.short_description = 'Vehicle Information'

    def activate_vehicles(self, request, queryset):
        """Activate selected vehicles."""
        queryset.update(is_active=True)
        self.message_user(request, f'Activated {queryset.count()} vehicles.')

    activate_vehicles.short_description = 'Activate selected vehicles'

    def deactivate_vehicles(self, request, queryset):
        """Deactivate selected vehicles."""
        queryset.update(is_active=False)
        self.message_user(request, f'Deactivated {queryset.count()} vehicles.')

    deactivate_vehicles.short_description = 'Deactivate selected vehicles'


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'dot_number', 'mc_number', 'carrier_name',
        'eld_provider', 'fmcsa_status', 'is_active', 'created_at'
    ]
    list_filter = [
        'is_active', 'created_at', 'eld_provider',
        'state', 'fmcsa_registration_date'
    ]
    search_fields = [
        'name', 'dot_number', 'mc_number', 'carrier_name',
        'eld_registration_id', 'inspection_contact_name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'carrier_info_display']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                ('name', 'carrier_name'),
                ('dot_number', 'mc_number'),
                'is_active'
            )
        }),
        ('Address Information', {
            'fields': (
                'address',
                ('city', 'state', 'zip_code'),
                ('phone', 'email')
            )
        }),
        ('Terminal Information', {
            'fields': (
                'main_office_address',
                'home_terminal_address',
                'home_terminal_timezone'
            ),
            'classes': ('collapse',)
        }),
        ('ELD System', {
            'fields': (
                ('eld_provider', 'eld_registration_id')
            )
        }),
        ('FMCSA Compliance', {
            'fields': (
                'fmcsa_registration_date',
            )
        }),
        ('Inspection Contact', {
            'fields': (
                ('inspection_contact_name', 'inspection_contact_phone')
            ),
            'classes': ('collapse',)
        }),
        ('Carrier Information', {
            'fields': ('carrier_info_display',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def fmcsa_status(self, obj):
        """Display FMCSA registration status."""
        if obj.fmcsa_registration_date:
            return format_html(
                '<span style="color: green;">Registered</span><br>'
                '<small>{}</small>',
                obj.fmcsa_registration_date.strftime('%m/%d/%Y')
            )
        else:
            return format_html('<span style="color: orange;">Not Registered</span>')

    fmcsa_status.short_description = 'FMCSA Status'

    def carrier_info_display(self, obj):
        """Display formatted carrier information."""
        return format_html(
            '<strong>Full Name:</strong> {}<br>'
            '<strong>DOT:</strong> {}<br>'
            '<strong>MC:</strong> {}',
            obj.get_full_carrier_info(),
            obj.dot_number,
            obj.mc_number or 'N/A'
        )

    carrier_info_display.short_description = 'Carrier Information'


@admin.register(DutyStatusEntry)
class DutyStatusEntryAdmin(admin.ModelAdmin):
    list_display = [
        'driver', 'duty_status', 'start_time', 'end_time',
        'location_display_short', 'is_automatic', 'is_certified'
    ]
    list_filter = [
        'duty_status', 'is_automatic', 'is_certified',
        'location_trigger', 'location_method'
    ]
    search_fields = [
        'driver__name', 'location_description',
        'shipping_document_number'
    ]
    readonly_fields = [
        'previous_duty_status', 'miles_driven_since_last',
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'start_time'

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'driver', 'vehicle', 'duty_status', 'previous_duty_status',
                'start_time', 'end_time'
            )
        }),
        ('Location Data', {
            'fields': (
                'latitude', 'longitude', 'location_method',
                'location_precision', 'location_description',
                'city', 'state', 'postal_code'
            )
        }),
        ('Vehicle Data', {
            'fields': (
                'odometer_reading', 'miles_driven_since_last',
                'engine_hours'
            )
        }),
        ('ELD Compliance', {
            'fields': (
                'location_trigger', 'is_automatic', 'is_edited',
                'is_certified', 'certification_date'
            )
        }),
        ('Additional Information', {
            'fields': (
                'shipping_document_number', 'driver_remarks'
            )
        })
    )

    def location_display_short(self, obj):
        location = obj.get_location_display()
        return location[:50] + '...' if len(location) > 50 else location
    location_display_short.short_description = 'Location'


@admin.register(LocationTrackingEntry)
class LocationTrackingEntryAdmin(admin.ModelAdmin):
    list_display = [
        'driver', 'interval_sequence', 'recorded_at',
        'location_coords', 'miles_since_last_location'
    ]
    list_filter = ['location_method', 'is_automatic']
    search_fields = ['driver__name']
    readonly_fields = ['miles_since_last_location', 'created_at']
    date_hierarchy = 'recorded_at'

    def location_coords(self, obj):
        return f"{obj.latitude:.4f}, {obj.longitude:.4f}"
    location_coords.short_description = 'Coordinates'


@admin.register(ELDDocument)
class ELDDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'driver', 'document_type', 'document_date',
        'title', 'file_info', 'is_verified', 'is_required'
    ]
    list_filter = [
        'document_type', 'is_verified', 'is_required',
        'upload_method', 'document_date'
    ]
    search_fields = [
        'driver__name', 'title', 'document_number',
        'issuing_authority'
    ]
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'document_date'

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'driver', 'vehicle', 'document_type', 'document_date',
                'document_time', 'title', 'description'
            )
        }),
        ('Document Details', {
            'fields': (
                'document_file', 'document_number', 'issuing_authority'
            )
        }),
        ('Location', {
            'fields': (
                'location_city', 'location_state', 'location_description'
            )
        }),
        ('Compliance', {
            'fields': (
                'is_required', 'upload_method', 'is_verified',
                'verified_by', 'verified_at'
            )
        }),
        ('Notes', {
            'fields': ('driver_notes', 'office_notes')
        })
    )

    def file_info(self, obj):
        if obj.document_file:
            size = obj.get_file_size_mb()
            file_type = "PDF" if obj.is_pdf() else "Image" if obj.is_image() else "File"
            return f"{file_type} ({size} MB)"
        return "No file"
    file_info.short_description = 'File'


@admin.register(DailyDocumentSummary)
class DailyDocumentSummaryAdmin(admin.ModelAdmin):
    list_display = [
        'driver', 'date', 'document_count',
        'compliance_status', 'verification_status'
    ]
    list_filter = [
        'has_minimum_documents', 'exceeds_limit',
        'all_documents_verified', 'date'
    ]
    search_fields = ['driver__name']
    readonly_fields = [
        'document_count', 'required_documents_count',
        'has_minimum_documents', 'exceeds_limit',
        'all_documents_verified'
    ]
    date_hierarchy = 'date'

    def compliance_status(self, obj):
        if obj.exceeds_limit:
            return format_html('<span style="color: orange;">Too Many Docs</span>')
        elif obj.has_minimum_documents:
            return format_html('<span style="color: green;">Compliant</span>')
        else:
            return format_html('<span style="color: red;">Insufficient</span>')
    compliance_status.short_description = 'Compliance'

    def verification_status(self, obj):
        if obj.all_documents_verified:
            return format_html('<span style="color: green;">All Verified</span>')
        else:
            return format_html('<span style="color: orange;">Pending</span>')
    verification_status.short_description = 'Verification'


@admin.register(ELDComplianceAlert)
class ELDComplianceAlertAdmin(admin.ModelAdmin):
    list_display = [
        'driver', 'alert_type', 'severity', 'status',
        'alert_date', 'title'
    ]
    list_filter = [
        'alert_type', 'severity', 'status',
        'driver_notified', 'office_notified'
    ]
    search_fields = ['driver__name', 'title', 'description']
    readonly_fields = ['created_at', 'resolved_at']
    date_hierarchy = 'alert_date'

    fieldsets = (
        ('Alert Information', {
            'fields': (
                'driver', 'vehicle', 'alert_type', 'severity',
                'status', 'title', 'description'
            )
        }),
        ('Timing', {
            'fields': ('alert_date', 'alert_time')
        }),
        ('Related Objects', {
            'fields': ('related_duty_entry', 'related_document')
        }),
        ('Resolution', {
            'fields': (
                'resolved_by', 'resolved_at', 'resolution_notes'
            )
        }),
        ('Notifications', {
            'fields': (
                'driver_notified', 'office_notified', 'notification_sent_at'
            )
        })
    )


@admin.register(ELDDataTransferLog)
class ELDDataTransferLogAdmin(admin.ModelAdmin):
    list_display = [
        'driver', 'transfer_type', 'status', 'requested_by',
        'transfer_initiated_at', 'records_transferred'
    ]
    list_filter = [
        'transfer_type', 'status', 'file_format',
        'driver_signature_required', 'driver_signature_obtained'
    ]
    search_fields = [
        'driver__name', 'requested_by', 'requesting_authority',
        'badge_number'
    ]
    readonly_fields = [
        'transfer_initiated_at', 'transfer_completed_at',
        'records_transferred', 'file_size_mb', 'retry_count'
    ]
    date_hierarchy = 'transfer_initiated_at'

    fieldsets = (
        ('Transfer Information', {
            'fields': (
                'driver', 'vehicle', 'transfer_type', 'status',
                'data_start_date', 'data_end_date'
            )
        }),
        ('Authority Information', {
            'fields': (
                'requested_by', 'requesting_authority', 'badge_number'
            )
        }),
        ('Location', {
            'fields': (
                'transfer_location', 'latitude', 'longitude'
            )
        }),
        ('Technical Details', {
            'fields': (
                'file_format', 'records_transferred', 'file_size_mb'
            )
        }),
        ('Compliance', {
            'fields': (
                'driver_signature_required', 'driver_signature_obtained',
                'transfer_notes'
            )
        }),
        ('Error Handling', {
            'fields': ('error_message', 'retry_count')
        })
    )


# Custom admin site configuration
admin.site.site_header = 'ELD Trip Planner Administration'
admin.site.site_title = 'ELD Admin'
admin.site.index_title = 'ELD Trip Planner Management'


# Custom CSS and JS for better admin experience
class ELDAdminMixin:
    """Mixin to add custom styling and optimize queries for ELD admin pages."""

    class Media:
        css = {
            'all': ('admin/css/eld_admin.css',)
        }
        js = ('admin/js/eld_admin.js',)

    def get_queryset(self, request):
        """Optimize querysets with select_related for better performance."""
        qs = super().get_queryset(request)

        # Add select_related for commonly accessed foreign keys
        if hasattr(self.model, '_meta'):
            foreign_keys = [
                field.name for field in self.model._meta.fields
                if field.many_to_one
            ]
            if foreign_keys:
                qs = qs.select_related(*foreign_keys[:3])  # Limit to avoid over-optimization

        return qs


# Apply performance optimizations to key admin classes
for model_admin in [DriverAdmin, VehicleAdmin, CompanyAdmin,
                   DutyStatusEntryAdmin, ELDDocumentAdmin]:
    # Add the mixin to existing classes
    model_admin.__bases__ = (ELDAdminMixin,) + model_admin.__bases__
