"""
Enhanced serializers with ELD compliance fields.
Update apps/core/serializers.py with these changes.
"""
from rest_framework import serializers
from .models import Location, Driver, Vehicle, Company


class LocationSerializer(serializers.ModelSerializer):
    """
    Serializer for Location model.
    """
    display_address = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = [
            'id', 'address', 'latitude', 'longitude',
            'city', 'state', 'country', 'postal_code',
            'display_address', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_display_address(self, obj):
        """Get formatted display address."""
        return str(obj)


class EnhancedDriverSerializer(serializers.ModelSerializer):
    """
    Enhanced Driver serializer with ELD compliance fields.
    """
    # Computed fields for display
    full_display_name = serializers.CharField(source='get_full_display_name', read_only=True)
    can_drive_status = serializers.SerializerMethodField()
    carrier_info = serializers.SerializerMethodField()

    # HOS status fields
    available_drive_hours = serializers.SerializerMethodField()
    available_duty_hours = serializers.SerializerMethodField()
    remaining_cycle_hours = serializers.SerializerMethodField()

    class Meta:
        model = Driver
        fields = [
            # Basic information
            'id', 'name', 'license_number', 'license_state',
            'phone', 'email', 'full_display_name',

            # ELD compliance fields
            'driver_signature', 'co_driver_name', 'shipping_document_number',
            'employee_id', 'home_terminal_address', 'home_terminal_timezone',
            'carrier_name', 'carrier_usdot_number',

            # ELD device information
            'eld_device_id', 'eld_device_model',

            # Certification tracking
            'last_certification_date', 'certification_method',

            # Status tracking
            'is_active', 'current_duty_status',

            # HOS tracking
            'current_cycle_hours', 'current_daily_drive_hours',
            'current_daily_duty_hours',

            # Last activity
            'last_duty_change_time', 'last_duty_change_location',

            # Computed fields
            'can_drive_status', 'carrier_info',
            'available_drive_hours', 'available_duty_hours',
            'remaining_cycle_hours',

            # Timestamps
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_certification_date']

    def get_can_drive_status(self, obj):
        """Get driver's legal driving status."""
        can_drive, reason = obj.can_drive()
        return {
            'can_drive': can_drive,
            'reason': reason
        }

    def get_carrier_info(self, obj):
        """Get carrier information string."""
        if obj.carrier_name and obj.carrier_usdot_number:
            return f"{obj.carrier_name} (USDOT: {obj.carrier_usdot_number})"
        return obj.carrier_name or ''

    def get_available_drive_hours(self, obj):
        """Calculate available driving hours."""
        cycle_remaining = max(0, 70 - float(obj.current_cycle_hours))
        daily_remaining = max(0, 11 - float(obj.current_daily_drive_hours))
        return min(cycle_remaining, daily_remaining)

    def get_available_duty_hours(self, obj):
        """Calculate available duty hours."""
        cycle_remaining = max(0, 70 - float(obj.current_cycle_hours))
        daily_remaining = max(0, 14 - float(obj.current_daily_duty_hours))
        return min(cycle_remaining, daily_remaining)

    def get_remaining_cycle_hours(self, obj):
        """Calculate remaining cycle hours."""
        return max(0, 70 - float(obj.current_cycle_hours))


class EnhancedVehicleSerializer(serializers.ModelSerializer):
    """
    Enhanced Vehicle serializer with ELD compliance fields.
    """
    # Computed fields
    vehicle_identification = serializers.SerializerMethodField()
    display_name = serializers.CharField(source='__str__', read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            # Basic information
            'id', 'vin', 'license_plate', 'license_state',
            'make', 'model', 'year', 'display_name',

            # Performance data
            'fuel_capacity', 'mpg',

            # ELD compliance fields
            'vehicle_number', 'engine_serial_number', 'engine_model',
            'eld_device_id', 'eld_connection_type',

            # Current readings
            'current_odometer', 'current_engine_hours',

            # Specifications
            'gvwr', 'vehicle_type',

            # Status
            'is_active',

            # Computed fields
            'vehicle_identification',

            # Timestamps
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_vehicle_identification(self, obj):
        """Get complete vehicle identification."""
        return obj.get_vehicle_identification()


class EnhancedCompanySerializer(serializers.ModelSerializer):
    """
    Enhanced Company serializer with ELD compliance fields.
    """
    # Computed fields
    full_carrier_info = serializers.CharField(source='get_full_carrier_info', read_only=True)

    class Meta:
        model = Company
        fields = [
            # Basic information
            'id', 'name', 'dot_number', 'mc_number',

            # Address information
            'address', 'city', 'state', 'zip_code',
            'phone', 'email',

            # ELD compliance fields
            'main_office_address', 'home_terminal_address',
            'home_terminal_timezone', 'carrier_name',

            # ELD system information
            'eld_provider', 'eld_registration_id',

            # Compliance tracking
            'fmcsa_registration_date',

            # Inspection contact
            'inspection_contact_name', 'inspection_contact_phone',

            # Status
            'is_active',

            # Computed fields
            'full_carrier_info',

            # Timestamps
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DriverCertificationSerializer(serializers.Serializer):
    """
    Serializer for driver log certification requests.
    """
    signature_data = serializers.CharField(
        required=False,
        help_text="Digital signature data (base64 encoded)"
    )
    certification_method = serializers.ChoiceField(
        choices=[
            ('ELECTRONIC', 'Electronic Signature'),
            ('PIN', 'PIN Entry'),
            ('BIOMETRIC', 'Biometric'),
        ],
        default='ELECTRONIC'
    )
    pin_code = serializers.CharField(
        required=False,
        max_length=10,
        help_text="PIN code for PIN-based certification"
    )

    def validate(self, data):
        """Validate certification data based on method."""
        method = data.get('certification_method', 'ELECTRONIC')

        if method == 'PIN' and not data.get('pin_code'):
            raise serializers.ValidationError(
                "PIN code is required for PIN-based certification"
            )

        if method == 'ELECTRONIC' and not data.get('signature_data'):
            raise serializers.ValidationError(
                "Signature data is required for electronic certification"
            )

        return data


class DutyStatusChangeSerializer(serializers.Serializer):
    """
    Serializer for duty status change requests.
    """
    new_status = serializers.ChoiceField(
        choices=[
            ('OFF', 'Off Duty'),
            ('SB', 'Sleeper Berth'),
            ('D', 'Driving'),
            ('ON', 'On Duty (Not Driving)'),
        ]
    )
    location = serializers.CharField(
        required=False,
        help_text="Location description for status change"
    )
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)
    odometer_reading = serializers.IntegerField(required=False)
    remarks = serializers.CharField(
        required=False,
        max_length=200,
        help_text="Additional remarks or notes"
    )

    def validate(self, data):
        """Validate duty status change data."""
        # Ensure location is provided for driving status
        if data.get('new_status') == 'D' and not data.get('location'):
            raise serializers.ValidationError(
                "Location is required when changing to driving status"
            )

        # Validate coordinates if provided
        lat = data.get('latitude')
        lng = data.get('longitude')

        if lat is not None:
            if not (-90 <= lat <= 90):
                raise serializers.ValidationError(
                    "Latitude must be between -90 and 90"
                )

        if lng is not None:
            if not (-180 <= lng <= 180):
                raise serializers.ValidationError(
                    "Longitude must be between -180 and 180"
                )

        return data


class VehicleOdometerUpdateSerializer(serializers.Serializer):
    """
    Serializer for vehicle odometer updates.
    """
    new_reading = serializers.IntegerField(
        min_value=0,
        help_text="New odometer reading in miles"
    )
    location = serializers.CharField(
        required=False,
        help_text="Location where reading was taken"
    )

    def validate_new_reading(self, value):
        """Validate that new reading is not less than current."""
        if hasattr(self, 'instance') and self.instance:
            if value < self.instance.current_odometer:
                raise serializers.ValidationError(
                    f"New reading ({value}) cannot be less than current reading "
                    f"({self.instance.current_odometer})"
                )
        return value


# Main serializers that use enhanced versions
class DriverSerializer(EnhancedDriverSerializer):
    """Main driver serializer (uses enhanced version)."""
    pass


class VehicleSerializer(EnhancedVehicleSerializer):
    """Main vehicle serializer (uses enhanced version)."""
    pass


class CompanySerializer(EnhancedCompanySerializer):
    """Main company serializer (uses enhanced version)."""
    pass


# Simplified serializers for lists and references
class DriverSummarySerializer(serializers.ModelSerializer):
    """Lightweight driver serializer for lists and references."""
    full_display_name = serializers.CharField(source='get_full_display_name', read_only=True)
    can_drive = serializers.SerializerMethodField()

    class Meta:
        model = Driver
        fields = [
            'id', 'name', 'full_display_name', 'license_number',
            'license_state', 'current_duty_status', 'can_drive',
            'current_cycle_hours', 'is_active'
        ]

    def get_can_drive(self, obj):
        """Get simple can drive status."""
        can_drive, _ = obj.can_drive()
        return can_drive


class VehicleSummarySerializer(serializers.ModelSerializer):
    """Lightweight vehicle serializer for lists and references."""
    display_name = serializers.CharField(source='__str__', read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            'id', 'display_name', 'license_plate', 'vin',
            'make', 'model', 'year', 'vehicle_number',
            'current_odometer', 'is_active'
        ]


class CompanySummarySerializer(serializers.ModelSerializer):
    """Lightweight company serializer for lists and references."""

    class Meta:
        model = Company
        fields = [
            'id', 'name', 'dot_number', 'mc_number',
            'carrier_name', 'is_active'
        ]
