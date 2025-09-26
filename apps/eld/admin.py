"""
Admin configuration for the ELD app.
"""
from django.contrib import admin
from .models import ELDLog, DutyStatusEntry, ELDViolation, ELDDocument, ELDAuditLog


class DutyStatusEntryInline(admin.TabularInline):
    model = DutyStatusEntry
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


class ELDViolationInline(admin.TabularInline):
    model = ELDViolation
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


class ELDDocumentInline(admin.TabularInline):
    model = ELDDocument
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ELDLog)
class ELDLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'log_date', 'driver', 'vehicle', 'total_drive_time',
        'total_on_duty_time', 'is_compliant', 'is_certified', 'created_at'
    ]
    list_filter = ['log_date', 'is_compliant', 'is_certified', 'created_at']
    search_fields = ['driver__name', 'vehicle__license_plate']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [DutyStatusEntryInline, ELDViolationInline, ELDDocumentInline]

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'trip', 'driver', 'vehicle', 'log_date'
            )
        }),
        ('Odometer Readings', {
            'fields': (
                'starting_odometer', 'ending_odometer', 'total_miles_driven'
            )
        }),
        ('Daily Totals', {
            'fields': (
                'total_drive_time', 'total_on_duty_time', 'total_off_duty_time',
                'cycle_hours_used'
            )
        }),
        ('Compliance', {
            'fields': (
                'is_compliant', 'violations'
            )
        }),
        ('Certification', {
            'fields': (
                'is_certified', 'certified_at'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DutyStatusEntry)
class DutyStatusEntryAdmin(admin.ModelAdmin):
    list_display = [
        'eld_log', 'duty_status', 'start_time', 'end_time',
        'duration_minutes', 'location_description', 'is_automatic'
    ]
    list_filter = ['duty_status', 'is_automatic', 'start_time']
    search_fields = ['eld_log__driver__name', 'location_description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ELDViolation)
class ELDViolationAdmin(admin.ModelAdmin):
    list_display = [
        'eld_log', 'violation_type', 'severity', 'violation_time',
        'duration_minutes', 'is_resolved'
    ]
    list_filter = ['violation_type', 'severity', 'is_resolved', 'violation_time']
    search_fields = ['eld_log__driver__name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ELDDocument)
class ELDDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'eld_log', 'document_type', 'title', 'document_date',
        'file_name', 'file_size'
    ]
    list_filter = ['document_type', 'document_date', 'created_at']
    search_fields = ['title', 'description', 'reference_number']
    readonly_fields = ['created_at', 'updated_at', 'file_size']


@admin.register(ELDAuditLog)
class ELDAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'eld_log', 'action', 'user_name', 'user_type', 'created_at'
    ]
    list_filter = ['action', 'user_type', 'created_at']
    search_fields = ['eld_log__driver__name', 'user_name', 'description']
    readonly_fields = ['created_at', 'updated_at']
