"""
Serializers for the ELD app.
"""
from rest_framework import serializers
from apps.core.serializers import DriverSerializer, VehicleSerializer, LocationSerializer
from .models import ELDLog, DutyStatusEntry, ELDViolation, ELDDocument, ELDAuditLog


class DutyStatusEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for DutyStatusEntry model.
    """
    location = LocationSerializer(read_only=True)
    duty_status_display = serializers.CharField(source='get_duty_status_display', read_only=True)

    class Meta:
        model = DutyStatusEntry
        fields = [
            'id', 'duty_status', 'duty_status_display', 'start_time',
            'end_time', 'duration_minutes', 'location', 'location_description',
            'odometer_reading', 'remarks', 'is_automatic', 'created_at'
        ]


class ELDViolationSerializer(serializers.ModelSerializer):
    """
    Serializer for ELDViolation model.
    """
    violation_type_display = serializers.CharField(source='get_violation_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)

    class Meta:
        model = ELDViolation
        fields = [
            'id', 'violation_type', 'violation_type_display', 'severity',
            'severity_display', 'description', 'violation_time',
            'duration_minutes', 'is_resolved', 'resolution_notes',
            'resolved_at', 'created_at'
        ]


class ELDDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for ELDDocument model.
    """
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)

    class Meta:
        model = ELDDocument
        fields = [
            'id', 'document_type', 'document_type_display', 'title',
            'description', 'file', 'file_name', 'file_size',
            'document_date', 'reference_number', 'created_at'
        ]


class ELDAuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for ELDAuditLog model.
    """
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = ELDAuditLog
        fields = [
            'id', 'action', 'action_display', 'description', 'user_name',
            'user_type', 'ip_address', 'created_at'
        ]


class ELDLogSerializer(serializers.ModelSerializer):
    """
    Serializer for ELDLog model with related data.
    """
    driver = DriverSerializer(read_only=True)
    vehicle = VehicleSerializer(read_only=True)
    duty_entries = DutyStatusEntrySerializer(many=True, read_only=True)
    violations = ELDViolationSerializer(many=True, read_only=True)
    documents = ELDDocumentSerializer(many=True, read_only=True)

    # Calculated fields
    total_miles_driven = serializers.DecimalField(max_digits=6, decimal_places=1, read_only=True)
    compliance_status = serializers.SerializerMethodField()
    violation_count = serializers.SerializerMethodField()

    class Meta:
        model = ELDLog
        fields = [
            'id', 'trip', 'driver', 'vehicle', 'log_date',
            'starting_odometer', 'ending_odometer', 'total_miles_driven',
            'total_drive_time', 'total_on_duty_time', 'total_off_duty_time',
            'cycle_hours_used', 'is_compliant', 'compliance_status',
            'violations', 'violation_count', 'is_certified', 'certified_at',
            'duty_entries', 'documents', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_compliance_status(self, obj):
        """Get human-readable compliance status."""
        if obj.is_compliant:
            return 'Compliant'
        elif obj.violations:
            return 'Has Violations'
        else:
            return 'Under Review'

    def get_violation_count(self, obj):
        """Get count of violations."""
        return obj.violations.count()


class ELDLogSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for ELD log lists.
    """
    driver_name = serializers.CharField(source='driver.name', read_only=True)
    vehicle_info = serializers.SerializerMethodField()
    compliance_status = serializers.SerializerMethodField()

    class Meta:
        model = ELDLog
        fields = [
            'id', 'log_date', 'driver_name', 'vehicle_info',
            'total_drive_time', 'total_on_duty_time', 'cycle_hours_used',
            'is_compliant', 'compliance_status', 'is_certified'
        ]

    def get_vehicle_info(self, obj):
        """Get vehicle display info."""
        if obj.vehicle:
            return f"{obj.vehicle.license_plate} ({obj.vehicle.make} {obj.vehicle.model})"
        return "Unknown Vehicle"

    def get_compliance_status(self, obj):
        """Get human-readable compliance status."""
        return 'Compliant' if obj.is_compliant else 'Non-Compliant'


class ELDComplianceCheckSerializer(serializers.Serializer):
    """
    Serializer for compliance check requests.
    """
    current_cycle_hours = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=70
    )
    daily_drive_hours = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=0,
        max_value=11,
        default=0
    )
    daily_duty_hours = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=0,
        max_value=14,
        default=0
    )

    def validate(self, data):
        """Validate HOS data."""
        if data['daily_drive_hours'] > data['daily_duty_hours']:
            raise serializers.ValidationError(
                "Daily driving hours cannot exceed daily on-duty hours"
            )
        return data
