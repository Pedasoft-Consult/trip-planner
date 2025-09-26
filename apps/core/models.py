"""
Enhanced ELD models with location recording compliance for FMCSA requirements.
Addresses 60-minute interval tracking and duty status change location recording.
Now includes comprehensive supporting documents integration.
"""
from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class BaseModel(models.Model):
    """
    Abstract base model that provides common fields for all models.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Location(BaseModel):
    """
    Model to store location information with coordinates.
    """
    address = models.CharField(max_length=500)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50, default='USA')
    postal_code = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'core_location'
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
        ]

    def __str__(self):
        return f"{self.city}, {self.state}" if self.city and self.state else self.address


class Driver(BaseModel):
    """
    Enhanced Driver model with ELD compliance fields.
    """
    # Basic driver information
    name = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True)
    license_state = models.CharField(max_length=2)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    # ELD REQUIRED FIELDS
    # Digital signature capability for ELD certification
    driver_signature = models.TextField(
        blank=True,
        help_text="Digital signature data for ELD log certification"
    )

    # Co-driver information for team driving
    co_driver_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Name of co-driver for team driving operations"
    )

    # Shipping document tracking
    shipping_document_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Current shipping document/load number"
    )

    # Additional ELD compliance fields
    employee_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="Driver employee ID for company tracking"
    )

    # Home terminal information (required for ELD)
    home_terminal_address = models.TextField(
        blank=True,
        help_text="Driver's home terminal address"
    )
    home_terminal_timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text="Home terminal timezone for ELD compliance"
    )

    # Carrier information
    carrier_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Motor carrier company name"
    )
    carrier_usdot_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="USDOT number of motor carrier"
    )

    # ELD device information
    eld_device_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="ELD device identifier"
    )
    eld_device_model = models.CharField(
        max_length=100,
        blank=True,
        help_text="ELD device model/manufacturer"
    )

    # Certification and compliance tracking
    last_certification_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last date driver certified their logs"
    )
    certification_method = models.CharField(
        max_length=20,
        choices=[
            ('ELECTRONIC', 'Electronic Signature'),
            ('PIN', 'PIN Entry'),
            ('BIOMETRIC', 'Biometric'),
        ],
        default='ELECTRONIC',
        help_text="Method used for log certification"
    )

    # Status and activity tracking
    is_active = models.BooleanField(default=True)
    current_duty_status = models.CharField(
        max_length=3,
        choices=[
            ('OFF', 'Off Duty'),
            ('SB', 'Sleeper Berth'),
            ('D', 'Driving'),
            ('ON', 'On Duty (Not Driving)'),
        ],
        default='OFF',
        help_text="Current duty status"
    )

    # HOS tracking
    current_cycle_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Current 8-day cycle hours used"
    )
    current_daily_drive_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        help_text="Today's driving hours"
    )
    current_daily_duty_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        help_text="Today's on-duty hours"
    )

    # Last duty status change tracking
    last_duty_change_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Time of last duty status change"
    )
    last_duty_change_location = models.TextField(
        blank=True,
        help_text="Location of last duty status change"
    )

    class Meta:
        db_table = 'core_driver'
        ordering = ['name']
        indexes = [
            models.Index(fields=['license_number']),
            models.Index(fields=['is_active']),
            models.Index(fields=['current_duty_status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.license_number})"

    def get_full_display_name(self):
        """Get driver display name with co-driver if applicable."""
        if self.co_driver_name:
            return f"{self.name} / {self.co_driver_name} (Team)"
        return self.name

    def can_drive(self):
        """Check if driver can legally drive based on HOS rules."""
        if not self.is_active:
            return False, "Driver is inactive"

        if self.current_cycle_hours >= 70:
            return False, "70-hour cycle limit reached"

        if self.current_daily_drive_hours >= 11:
            return False, "11-hour daily drive limit reached"

        if self.current_daily_duty_hours >= 14:
            return False, "14-hour daily duty limit reached"

        return True, "Can drive"

    def certify_logs(self, signature_data=None, method='ELECTRONIC'):
        """Certify driver's ELD logs."""
        self.last_certification_date = timezone.now()
        self.certification_method = method

        if signature_data:
            self.driver_signature = signature_data

        self.save(update_fields=[
            'last_certification_date',
            'certification_method',
            'driver_signature'
        ])

    def update_duty_status(self, new_status, location=None):
        """Update driver's duty status."""
        old_status = self.current_duty_status
        self.current_duty_status = new_status
        self.last_duty_change_time = timezone.now()

        if location:
            self.last_duty_change_location = location

        self.save(update_fields=[
            'current_duty_status',
            'last_duty_change_time',
            'last_duty_change_location'
        ])

        return {
            'old_status': old_status,
            'new_status': new_status,
            'change_time': self.last_duty_change_time,
            'location': location
        }


class Company(BaseModel):
    """
    Enhanced Company model with ELD compliance fields.
    """
    name = models.CharField(max_length=200)
    dot_number = models.CharField(max_length=20, unique=True)
    mc_number = models.CharField(max_length=20, blank=True)

    # Enhanced address information
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)

    phone = models.CharField(max_length=20)
    email = models.EmailField()

    # ELD REQUIRED FIELDS
    # Main office address (separate from mailing)
    main_office_address = models.TextField(
        blank=True,
        help_text="Main office address for ELD compliance"
    )

    # Terminal information
    home_terminal_address = models.TextField(
        blank=True,
        help_text="Home terminal address"
    )
    home_terminal_timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text="Home terminal timezone"
    )

    # Carrier identification
    carrier_name = models.CharField(
        max_length=200,
        help_text="Official carrier name as registered with FMCSA"
    )

    # ELD provider information
    eld_provider = models.CharField(
        max_length=100,
        blank=True,
        help_text="ELD system provider/vendor"
    )
    eld_registration_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="ELD system registration ID"
    )

    # Compliance and certifications
    fmcsa_registration_date = models.DateField(
        null=True,
        blank=True,
        help_text="FMCSA registration date"
    )

    # Contact information for inspections
    inspection_contact_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Primary contact for DOT inspections"
    )
    inspection_contact_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Phone number for inspection contact"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'core_company'
        verbose_name_plural = 'companies'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (DOT: {self.dot_number})"

    def get_full_carrier_info(self):
        """Get complete carrier identification string."""
        info = f"{self.carrier_name or self.name}"
        if self.dot_number:
            info += f" (DOT: {self.dot_number})"
        if self.mc_number:
            info += f" (MC: {self.mc_number})"
        return info


class Vehicle(BaseModel):
    """
    Enhanced Vehicle model with ELD compliance fields.
    """
    vin = models.CharField(max_length=17, unique=True)
    license_plate = models.CharField(max_length=20)
    license_state = models.CharField(max_length=2)
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.IntegerField()

    # Enhanced fuel and performance data
    fuel_capacity = models.DecimalField(max_digits=6, decimal_places=2)
    mpg = models.DecimalField(max_digits=4, decimal_places=1, default=6.5)

    # ELD REQUIRED FIELDS
    # Vehicle identification for ELD
    vehicle_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Fleet vehicle number or identifier"
    )

    # Engine specifications
    engine_serial_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Engine serial number"
    )
    engine_model = models.CharField(
        max_length=100,
        blank=True,
        help_text="Engine model/manufacturer"
    )

    # ELD device connection
    eld_device_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Connected ELD device identifier"
    )
    eld_connection_type = models.CharField(
        max_length=20,
        choices=[
            ('OBDII', 'OBD-II Port'),
            ('J1939', 'J1939 Data Bus'),
            ('J1708', 'J1708 Data Bus'),
            ('WIRELESS', 'Wireless Connection'),
        ],
        blank=True,
        help_text="How ELD connects to vehicle"
    )

    # Current odometer and engine hours
    current_odometer = models.PositiveIntegerField(
        default=0,
        help_text="Current odometer reading in miles"
    )
    current_engine_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Current engine hours"
    )

    # Vehicle specifications for compliance
    gvwr = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Gross Vehicle Weight Rating (GVWR) in pounds"
    )
    vehicle_type = models.CharField(
        max_length=20,
        choices=[
            ('TRUCK', 'Truck'),
            ('TRACTOR', 'Truck Tractor'),
            ('BUS', 'Bus'),
            ('OTHER', 'Other'),
        ],
        default='TRUCK',
        help_text="Vehicle type classification"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'core_vehicle'
        ordering = ['license_plate']
        indexes = [
            models.Index(fields=['vin']),
            models.Index(fields=['license_plate']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        display = f"{self.year} {self.make} {self.model} ({self.license_plate})"
        if self.vehicle_number:
            display = f"#{self.vehicle_number} - {display}"
        return display

    def get_vehicle_identification(self):
        """Get complete vehicle identification for ELD logs."""
        return {
            'vehicle_number': self.vehicle_number or '',
            'license_plate': self.license_plate,
            'license_state': self.license_state,
            'vin': self.vin,
            'make_model_year': f"{self.year} {self.make} {self.model}",
            'current_odometer': self.current_odometer,
            'engine_hours': float(self.current_engine_hours)
        }

    def update_odometer(self, new_reading):
        """Update odometer reading with validation."""
        if new_reading < self.current_odometer:
            raise ValueError("Odometer reading cannot decrease")

        miles_driven = new_reading - self.current_odometer
        self.current_odometer = new_reading

        # Estimate engine hours (rough calculation)
        if miles_driven > 0:
            estimated_hours = miles_driven / 45  # Assume 45 mph average
            self.current_engine_hours += estimated_hours

        self.save(update_fields=['current_odometer', 'current_engine_hours'])
        return miles_driven


class DutyStatusEntry(BaseModel):
    """
    Enhanced duty status entry model with comprehensive location tracking
    for ELD compliance per FMCSA regulations.
    """
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='duty_status_entries'
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='duty_status_entries'
    )

    # Core duty status information
    duty_status = models.CharField(
        max_length=3,
        choices=[
            ('OFF', 'Off Duty'),
            ('SB', 'Sleeper Berth'),
            ('D', 'Driving'),
            ('ON', 'On Duty (Not Driving)'),
        ],
        help_text="Driver duty status"
    )

    previous_duty_status = models.CharField(
        max_length=3,
        choices=[
            ('OFF', 'Off Duty'),
            ('SB', 'Sleeper Berth'),
            ('D', 'Driving'),
            ('ON', 'On Duty (Not Driving)'),
        ],
        blank=True,
        help_text="Previous duty status for change tracking"
    )

    # ENHANCED LOCATION TRACKING FOR ELD COMPLIANCE
    # Primary location data (required for all duty status changes)
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text="GPS latitude coordinate"
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text="GPS longitude coordinate"
    )

    # Location precision and method tracking
    location_method = models.CharField(
        max_length=20,
        choices=[
            ('GPS', 'GPS/GNSS'),
            ('CELLULAR', 'Cellular Tower'),
            ('WIFI', 'WiFi Location'),
            ('MANUAL', 'Manual Entry'),
            ('UNKNOWN', 'Unknown Method'),
        ],
        default='GPS',
        help_text="Method used to determine location"
    )

    location_precision = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Location precision in meters"
    )

    # Human-readable location information
    location_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Human-readable location description"
    )

    # Address components for location context
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    # Mileage tracking (required for ELD compliance)
    odometer_reading = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Vehicle odometer reading at time of entry"
    )
    miles_driven_since_last = models.DecimalField(
        max_digits=8,
        decimal_places=1,
        default=0,
        help_text="Miles driven since last duty status change"
    )

    # Engine hours tracking
    engine_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Engine hours at time of entry"
    )

    # Time tracking
    start_time = models.DateTimeField(
        help_text="Start time of this duty status"
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="End time of this duty status (when changed)"
    )

    # ELD compliance flags
    is_automatic = models.BooleanField(
        default=True,
        help_text="Whether this entry was automatically generated by ELD"
    )
    is_edited = models.BooleanField(
        default=False,
        help_text="Whether this entry has been edited by driver"
    )

    # Location recording trigger
    location_trigger = models.CharField(
        max_length=20,
        choices=[
            ('DUTY_CHANGE', 'Duty Status Change'),
            ('INTERVAL', '60-Minute Interval'),
            ('POWER_ON', 'Vehicle Power On'),
            ('POWER_OFF', 'Vehicle Power Off'),
            ('MANUAL', 'Manual Request'),
        ],
        default='DUTY_CHANGE',
        help_text="What triggered this location recording"
    )

    # Shipping document reference
    shipping_document_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Associated shipping document number"
    )

    # Driver remarks/annotations
    driver_remarks = models.TextField(
        blank=True,
        help_text="Driver comments or remarks for this entry"
    )

    # ELD certification tracking
    is_certified = models.BooleanField(
        default=False,
        help_text="Whether this entry has been certified by driver"
    )
    certification_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this entry was certified"
    )

    class Meta:
        db_table = 'core_duty_status_entry'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['driver', '-start_time']),
            models.Index(fields=['vehicle', '-start_time']),
            models.Index(fields=['duty_status']),
            models.Index(fields=['is_automatic']),
            models.Index(fields=['location_trigger']),
            models.Index(fields=['latitude', 'longitude']),
        ]

    def __str__(self):
        return f"{self.driver.name} - {self.get_duty_status_display()} at {self.start_time}"

    def save(self, *args, **kwargs):
        """Enhanced save method with location validation."""
        # Validate location data if provided
        if self.latitude is not None and self.longitude is not None:
            if not (-90 <= float(self.latitude) <= 90):
                raise ValueError("Latitude must be between -90 and 90 degrees")
            if not (-180 <= float(self.longitude) <= 180):
                raise ValueError("Longitude must be between -180 and 180 degrees")

        # Auto-populate location description if coordinates provided
        if self.latitude and self.longitude and not self.location_description:
            self.location_description = f"{self.latitude:.4f}, {self.longitude:.4f}"

        super().save(*args, **kwargs)

    def get_location_display(self):
        """Get human-readable location string."""
        if self.location_description:
            return self.location_description
        elif self.city and self.state:
            return f"{self.city}, {self.state}"
        elif self.latitude and self.longitude:
            return f"{self.latitude:.4f}, {self.longitude:.4f}"
        else:
            return "Location not recorded"

    def calculate_duration(self):
        """Calculate duration of this duty status period."""
        if self.end_time:
            return self.end_time - self.start_time
        else:
            return timezone.now() - self.start_time

    def is_location_required(self):
        """Determine if location recording is required for this entry."""
        # Location required for all duty status changes
        if self.location_trigger == 'DUTY_CHANGE':
            return True
        # Location required for 60-minute intervals during driving
        if self.location_trigger == 'INTERVAL' and self.duty_status == 'D':
            return True
        # Location required for power events
        if self.location_trigger in ['POWER_ON', 'POWER_OFF']:
            return True
        return False

    def validate_location_compliance(self):
        """Validate ELD location recording compliance."""
        errors = []

        if self.is_location_required():
            if self.latitude is None or self.longitude is None:
                errors.append("Location coordinates required for this entry type")

            if not self.location_method:
                errors.append("Location method must be specified")

        return errors

    def get_day_key(self):
        """Get the day key for this entry (used for supporting documents)."""
        return self.start_time.date()


class LocationTrackingEntry(BaseModel):
    """
    Dedicated model for 60-minute interval location tracking during driving.
    Separate from duty status changes to maintain clear audit trail.
    """
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='location_tracking_entries'
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='location_tracking_entries'
    )

    # Location data
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    location_method = models.CharField(max_length=20, default='GPS')
    location_precision = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Time and tracking info
    recorded_at = models.DateTimeField()
    odometer_reading = models.PositiveIntegerField()
    engine_hours = models.DecimalField(max_digits=8, decimal_places=2)

    # Distance since last location record
    miles_since_last_location = models.DecimalField(
        max_digits=8,
        decimal_places=1,
        default=0
    )

    # Current driving session reference
    duty_status_entry = models.ForeignKey(
        DutyStatusEntry,
        on_delete=models.CASCADE,
        related_name='location_intervals',
        help_text="Associated driving duty status entry"
    )

    # Automatic tracking metadata
    is_automatic = models.BooleanField(default=True)
    interval_sequence = models.PositiveIntegerField(
        help_text="Sequence number within driving session"
    )

    class Meta:
        db_table = 'core_location_tracking_entry'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['driver', '-recorded_at']),
            models.Index(fields=['vehicle', '-recorded_at']),
            models.Index(fields=['duty_status_entry', 'interval_sequence']),
            models.Index(fields=['latitude', 'longitude']),
        ]
        unique_together = ['duty_status_entry', 'interval_sequence']

    def __str__(self):
        return f"{self.driver.name} - Interval #{self.interval_sequence} at {self.recorded_at}"


class ELDDocument(BaseModel):
    """
    Enhanced ELD supporting documents model for FMCSA compliance.
    Motor carriers must retain up to 8 supporting documents per 24-hour period.
    """

    DOCUMENT_TYPES = [
        ('BILL_OF_LADING', 'Bill of Lading'),
        ('DISPATCH_RECORD', 'Dispatch Record'),
        ('FUEL_RECEIPT', 'Fuel Receipt'),
        ('LOADING_DOCUMENTS', 'Loading Documents'),
        ('WEIGHT_STATION_BYPASS', 'Weight Station Bypass'),
        ('BORDER_CROSSING', 'Border Crossing Documents'),
        ('INSPECTION_REPORTS', 'Inspection Reports'),
        ('DELIVERY_RECEIPT', 'Delivery Receipt'),
        ('EXPENSE_RECEIPT', 'Expense Receipt'),
        ('LOGBOOK_PAGE', 'Paper Logbook Page'),
        ('PERMIT', 'Special Permit'),
        ('MANIFEST', 'Cargo Manifest'),
        ('OTHER', 'Other Supporting Document'),
    ]

    # Core document information
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='eld_documents'
    )

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='eld_documents',
        null=True,
        blank=True
    )

    document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPES,
        help_text="Type of supporting document"
    )

    document_date = models.DateField(
        help_text="Date this document applies to (24-hour period)"
    )

    document_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Specific time if applicable"
    )

    # Document content
    title = models.CharField(
        max_length=200,
        help_text="Document title or description"
    )

    description = models.TextField(
        blank=True,
        help_text="Additional document description"
    )

    # File attachments
    document_file = models.FileField(
        upload_to='eld_documents/%Y/%m/%d/',
        blank=True,
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'tiff', 'doc', 'docx']
        )],
        help_text="Scanned or digital copy of document"
    )

    # Document reference information
    document_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Document reference number (BOL#, invoice#, etc.)"
    )

    issuing_authority = models.CharField(
        max_length=200,
        blank=True,
        help_text="Authority or organization that issued document"
    )

    # Geographic information
    location_city = models.CharField(max_length=100, blank=True)
    location_state = models.CharField(max_length=2, blank=True)
    location_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Location where document was obtained/applies"
    )

    # Compliance tracking
    is_required = models.BooleanField(
        default=False,
        help_text="Whether this document is required for compliance"
    )

    upload_method = models.CharField(
        max_length=20,
        choices=[
            ('DRIVER_MOBILE', 'Driver Mobile App'),
            ('DRIVER_TABLET', 'Driver ELD Tablet'),
            ('OFFICE_SCAN', 'Office Scan'),
            ('EMAIL', 'Email Upload'),
            ('API', 'API Integration'),
            ('MANUAL', 'Manual Entry'),
        ],
        default='DRIVER_MOBILE',
        help_text="How document was uploaded to system"
    )

    # Verification and approval
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether document has been verified by office staff"
    )

    verified_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_eld_documents'
    )

    verified_at = models.DateTimeField(null=True, blank=True)

    # Associated duty periods or trips
    associated_duty_entries = models.ManyToManyField(
        DutyStatusEntry,
        blank=True,
        related_name='supporting_documents',
        help_text="Duty status entries this document supports"
    )

    # Driver notes
    driver_notes = models.TextField(
        blank=True,
        help_text="Driver notes about this document"
    )

    # Office notes
    office_notes = models.TextField(
        blank=True,
        help_text="Office staff notes about this document"
    )

    class Meta:
        db_table = 'core_eld_document'
        ordering = ['-document_date', '-created_at']
        indexes = [
            models.Index(fields=['driver', '-document_date']),
            models.Index(fields=['vehicle', '-document_date']),
            models.Index(fields=['document_type']),
            models.Index(fields=['document_date']),
            models.Index(fields=['is_required']),
            models.Index(fields=['is_verified']),
        ]

    def __str__(self):
        return f"{self.driver.name} - {self.get_document_type_display()} ({self.document_date})"

    def save(self, *args, **kwargs):
        """Enhanced save with document validation."""
        # Set title from document type if not provided
        if not self.title:
            self.title = self.get_document_type_display()

        super().save(*args, **kwargs)

    def get_file_size_mb(self):
        """Get file size in MB."""
        if self.document_file:
            return round(self.document_file.size / (1024 * 1024), 2)
        return 0

    def is_image(self):
        """Check if document is an image file."""
        if self.document_file:
            return self.document_file.name.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff'))
        return False

    def is_pdf(self):
        """Check if document is a PDF file."""
        if self.document_file:
            return self.document_file.name.lower().endswith('.pdf')
        return False


class DailyDocumentSummary(BaseModel):
    """
    Summary model to track supporting documents for each 24-hour period.
    Helps ensure compliance with the 8-document retention requirement.
    """
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='daily_document_summaries'
    )

    date = models.DateField(
        help_text="24-hour period date"
    )

    # Document counts by type
    document_count = models.PositiveIntegerField(
        default=0,
        help_text="Total documents for this day"
    )

    required_documents_count = models.PositiveIntegerField(
        default=0,
        help_text="Count of required documents"
    )

    # Compliance flags
    has_minimum_documents = models.BooleanField(
        default=False,
        help_text="Whether minimum required documents are present"
    )

    exceeds_limit = models.BooleanField(
        default=False,
        help_text="Whether document count exceeds 8-document limit"
    )

    # Key document presence flags
    has_bill_of_lading = models.BooleanField(default=False)
    has_dispatch_record = models.BooleanField(default=False)
    has_fuel_receipts = models.BooleanField(default=False)

    # Verification status
    all_documents_verified = models.BooleanField(
        default=False,
        help_text="Whether all documents for this day are verified"
    )

    # Duty time summary for context
    total_duty_time = models.DurationField(
        null=True,
        blank=True,
        help_text="Total duty time for this day"
    )

    driving_time = models.DurationField(
        null=True,
        blank=True,
        help_text="Total driving time for this day"
    )

    class Meta:
        db_table = 'core_daily_document_summary'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['driver', '-date']),
            models.Index(fields=['date']),
            models.Index(fields=['has_minimum_documents']),
            models.Index(fields=['exceeds_limit']),
        ]
        unique_together = ['driver', 'date']

    def __str__(self):
        return f"{self.driver.name} - {self.date} ({self.document_count} docs)"

    def update_summary(self):
        """Update the summary based on current documents."""
        documents = ELDDocument.objects.filter(
            driver=self.driver,
            document_date=self.date
        )

        self.document_count = documents.count()
        self.required_documents_count = documents.filter(is_required=True).count()
        self.exceeds_limit = self.document_count > 8

        # Check for key document types
        doc_types = documents.values_list('document_type', flat=True)
        self.has_bill_of_lading = 'BILL_OF_LADING' in doc_types
        self.has_dispatch_record = 'DISPATCH_RECORD' in doc_types
        self.has_fuel_receipts = 'FUEL_RECEIPT' in doc_types

        # Check verification status
        self.all_documents_verified = not documents.filter(is_verified=False).exists()

        # Set minimum requirements (customize based on your needs)
        self.has_minimum_documents = (
                self.has_dispatch_record and  # At minimum need dispatch
                self.document_count >= 1
        )

        self.save()


class ELDComplianceAlert(BaseModel):
    """
    Model for tracking ELD compliance alerts and notifications.
    """
    ALERT_TYPES = [
        ('MISSING_LOCATION', 'Missing Location Data'),
        ('MISSING_INTERVAL', 'Missing 60-Minute Interval'),
        ('EXCESSIVE_DOCUMENTS', 'Excessive Supporting Documents'),
        ('MISSING_DOCUMENTS', 'Missing Required Documents'),
        ('UNVERIFIED_DOCUMENTS', 'Unverified Documents'),
        ('HOS_VIOLATION', 'Hours of Service Violation'),
        ('DEVICE_MALFUNCTION', 'ELD Device Malfunction'),
        ('DATA_TRANSFER_FAILURE', 'Data Transfer Failure'),
    ]

    SEVERITY_LEVELS = [
        ('LOW', 'Low Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('HIGH', 'High Priority'),
        ('CRITICAL', 'Critical - Immediate Action Required'),
    ]

    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('DISMISSED', 'Dismissed'),
    ]

    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='compliance_alerts'
    )

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='compliance_alerts',
        null=True,
        blank=True
    )

    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='OPEN')

    title = models.CharField(max_length=200)
    description = models.TextField()

    # Alert timing
    alert_date = models.DateField()
    alert_time = models.TimeField(null=True, blank=True)

    # Related objects
    related_duty_entry = models.ForeignKey(
        DutyStatusEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compliance_alerts'
    )

    related_document = models.ForeignKey(
        ELDDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compliance_alerts'
    )

    # Resolution tracking
    resolved_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_compliance_alerts'
    )

    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    # Notification tracking
    driver_notified = models.BooleanField(default=False)
    office_notified = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'core_eld_compliance_alert'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['driver', '-alert_date']),
            models.Index(fields=['status']),
            models.Index(fields=['severity']),
            models.Index(fields=['alert_type']),
        ]

    def __str__(self):
        return f"{self.driver.name} - {self.title} ({self.get_severity_display()})"

    def mark_resolved(self, user, resolution_notes=""):
        """Mark alert as resolved."""
        self.status = 'RESOLVED'
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.resolution_notes = resolution_notes
        self.save()


class ELDDataTransferLog(BaseModel):
    """
    Log for tracking ELD data transfers to authorities (roadside inspections, etc.)
    Required for FMCSA compliance.
    """
    TRANSFER_TYPES = [
        ('ROADSIDE', 'Roadside Inspection'),
        ('AUDIT', 'Compliance Audit'),
        ('ELECTRONIC', 'Electronic Transfer'),
        ('WEB_PORTAL', 'Web Portal Download'),
        ('EMAIL', 'Email Transfer'),
        ('USB', 'USB Transfer'),
        ('PRINT', 'Printed Records'),
    ]

    TRANSFER_STATUS = [
        ('INITIATED', 'Transfer Initiated'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed Successfully'),
        ('FAILED', 'Transfer Failed'),
        ('PARTIAL', 'Partially Completed'),
    ]

    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='data_transfers'
    )

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='data_transfers'
    )

    transfer_type = models.CharField(max_length=20, choices=TRANSFER_TYPES)
    status = models.CharField(max_length=15, choices=TRANSFER_STATUS, default='INITIATED')

    # Transfer details
    requested_by = models.CharField(
        max_length=200,
        help_text="Authority or person requesting the data"
    )

    requesting_authority = models.CharField(
        max_length=200,
        blank=True,
        help_text="Official authority (DOT, State Police, etc.)"
    )

    badge_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Officer badge or ID number"
    )

    # Date range of requested data
    data_start_date = models.DateField()
    data_end_date = models.DateField()

    # Transfer execution
    transfer_initiated_at = models.DateTimeField(auto_now_add=True)
    transfer_completed_at = models.DateTimeField(null=True, blank=True)

    # Location of transfer
    transfer_location = models.CharField(
        max_length=200,
        blank=True,
        help_text="Location where transfer occurred"
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )

    # Technical details
    records_transferred = models.PositiveIntegerField(
        default=0,
        help_text="Number of records transferred"
    )

    file_format = models.CharField(
        max_length=20,
        choices=[
            ('CSV', 'CSV Format'),
            ('JSON', 'JSON Format'),
            ('XML', 'XML Format'),
            ('PDF', 'PDF Report'),
            ('PRINT', 'Printed Copy'),
        ],
        default='CSV'
    )

    file_size_mb = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Size of transferred data in MB"
    )

    # Compliance notes
    transfer_notes = models.TextField(
        blank=True,
        help_text="Notes about the transfer process"
    )

    driver_signature_required = models.BooleanField(
        default=True,
        help_text="Whether driver signature was required"
    )

    driver_signature_obtained = models.BooleanField(
        default=False,
        help_text="Whether driver signature was obtained"
    )

    # Error tracking
    error_message = models.TextField(
        blank=True,
        help_text="Error details if transfer failed"
    )

    retry_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of retry attempts"
    )

    class Meta:
        db_table = 'core_eld_data_transfer_log'
        ordering = ['-transfer_initiated_at']
        indexes = [
            models.Index(fields=['driver', '-transfer_initiated_at']),
            models.Index(fields=['vehicle', '-transfer_initiated_at']),
            models.Index(fields=['status']),
            models.Index(fields=['transfer_type']),
            models.Index(fields=['data_start_date', 'data_end_date']),
        ]

    def __str__(self):
        return f"{self.driver.name} - {self.get_transfer_type_display()} ({self.transfer_initiated_at})"

    def mark_completed(self, records_count=0, file_size_mb=0):
        """Mark transfer as completed."""
        self.status = 'COMPLETED'
        self.transfer_completed_at = timezone.now()
        self.records_transferred = records_count
        self.file_size_mb = file_size_mb
        self.save()

    def mark_failed(self, error_message=""):
        """Mark transfer as failed."""
        self.status = 'FAILED'
        self.error_message = error_message
        self.retry_count += 1
        self.save()

    def get_transfer_duration(self):
        """Get duration of transfer process."""
        if self.transfer_completed_at:
            return self.transfer_completed_at - self.transfer_initiated_at
        else:
            return timezone.now() - self.transfer_initiated_at


# Manager Classes for ELD Operations
class ELDLocationManager:
    """
    Manager class for handling ELD location recording compliance.
    Handles automatic 60-minute interval tracking and duty status locations.
    """

    @staticmethod
    def record_duty_status_change(driver, vehicle, new_status,
                                  latitude=None, longitude=None,
                                  location_method='GPS', **kwargs):
        """
        Record a duty status change with required location data.
        """
        # Get current duty status entry to end it
        current_entry = DutyStatusEntry.objects.filter(
            driver=driver,
            end_time__isnull=True
        ).first()

        # End current duty status
        if current_entry:
            current_entry.end_time = timezone.now()
            current_entry.save()

        # Create new duty status entry
        new_entry = DutyStatusEntry.objects.create(
            driver=driver,
            vehicle=vehicle,
            duty_status=new_status,
            previous_duty_status=current_entry.duty_status if current_entry else '',
            latitude=latitude,
            longitude=longitude,
            location_method=location_method,
            start_time=timezone.now(),
            location_trigger='DUTY_CHANGE',
            odometer_reading=vehicle.current_odometer,
            engine_hours=vehicle.current_engine_hours,
            **kwargs
        )

        # Update driver's current duty status
        driver.update_duty_status(
            new_status,
            location=new_entry.get_location_display()
        )

        # Update daily document summary for this date
        summary, created = DailyDocumentSummary.objects.get_or_create(
            driver=driver,
            date=new_entry.get_day_key()
        )
        summary.update_summary()

        logger.info(
            f"Duty status changed: {driver.name} to {new_status} "
            f"at {latitude}, {longitude}"
        )

        return new_entry

    @staticmethod
    def record_location_interval(driver, vehicle, latitude, longitude,
                                 location_method='GPS'):
        """
        Record a 60-minute interval location during driving.
        """
        # Get current driving duty status entry
        driving_entry = DutyStatusEntry.objects.filter(
            driver=driver,
            duty_status='D',
            end_time__isnull=True
        ).first()

        if not driving_entry:
            logger.warning(
                f"No active driving session for interval recording: {driver.name}"
            )
            return None

        # Get sequence number for this interval
        last_interval = LocationTrackingEntry.objects.filter(
            duty_status_entry=driving_entry
        ).order_by('-interval_sequence').first()

        sequence = 1
        if last_interval:
            sequence = last_interval.interval_sequence + 1

        # Calculate miles since last location
        miles_since_last = 0
        if last_interval:
            miles_since_last = vehicle.current_odometer - last_interval.odometer_reading
        elif driving_entry.odometer_reading:
            miles_since_last = vehicle.current_odometer - driving_entry.odometer_reading

        # Create location tracking entry
        location_entry = LocationTrackingEntry.objects.create(
            driver=driver,
            vehicle=vehicle,
            latitude=latitude,
            longitude=longitude,
            location_method=location_method,
            recorded_at=timezone.now(),
            odometer_reading=vehicle.current_odometer,
            engine_hours=vehicle.current_engine_hours,
            miles_since_last_location=miles_since_last,
            duty_status_entry=driving_entry,
            interval_sequence=sequence
        )

        logger.info(
            f"Location interval recorded: {driver.name} interval #{sequence} "
            f"at {latitude}, {longitude}"
        )

        return location_entry

    @staticmethod
    def get_compliance_report(driver, start_date, end_date):
        """
        Generate location recording compliance report for a driver.
        """
        # Get all duty status entries in date range
        duty_entries = DutyStatusEntry.objects.filter(
            driver=driver,
            start_time__range=[start_date, end_date]
        ).order_by('start_time')

        # Get all location intervals in date range
        location_intervals = LocationTrackingEntry.objects.filter(
            driver=driver,
            recorded_at__range=[start_date, end_date]
        ).order_by('recorded_at')

        # Get supporting documents summary
        document_summaries = DailyDocumentSummary.objects.filter(
            driver=driver,
            date__range=[start_date.date() if hasattr(start_date, 'date') else start_date,
                         end_date.date() if hasattr(end_date, 'date') else end_date]
        )

        compliance_issues = []

        # Check duty status changes have locations
        for entry in duty_entries:
            if entry.is_location_required():
                if not entry.latitude or not entry.longitude:
                    compliance_issues.append({
                        'type': 'missing_duty_location',
                        'entry': entry,
                        'message': f'Missing location for {entry.duty_status} at {entry.start_time}'
                    })

        # Check 60-minute intervals during driving
        driving_entries = duty_entries.filter(duty_status='D')
        for driving_entry in driving_entries:
            duration = driving_entry.calculate_duration()
            if duration.total_seconds() > 3600:  # More than 1 hour
                intervals_count = location_intervals.filter(
                    duty_status_entry=driving_entry
                ).count()

                expected_intervals = int(duration.total_seconds() // 3600)
                if intervals_count < expected_intervals:
                    compliance_issues.append({
                        'type': 'missing_intervals',
                        'entry': driving_entry,
                        'expected': expected_intervals,
                        'actual': intervals_count,
                        'message': f'Missing location intervals for driving session'
                    })

        # Check supporting documents compliance
        for summary in document_summaries:
            if not summary.has_minimum_documents:
                compliance_issues.append({
                    'type': 'insufficient_documents',
                    'date': summary.date,
                    'count': summary.document_count,
                    'message': f'Insufficient supporting documents for {summary.date}'
                })

            if summary.exceeds_limit:
                compliance_issues.append({
                    'type': 'excessive_documents',
                    'date': summary.date,
                    'count': summary.document_count,
                    'message': f'Exceeds 8-document limit for {summary.date} ({summary.document_count} documents)'
                })

        return {
            'duty_entries_count': duty_entries.count(),
            'location_intervals_count': location_intervals.count(),
            'document_summaries_count': document_summaries.count(),
            'compliance_issues': compliance_issues,
            'is_compliant': len(compliance_issues) == 0,
            'document_compliance': {
                'days_with_sufficient_docs': document_summaries.filter(has_minimum_documents=True).count(),
                'days_exceeding_limit': document_summaries.filter(exceeds_limit=True).count(),
                'total_documents': sum(s.document_count for s in document_summaries),
                'verified_documents': sum(1 for s in document_summaries if s.all_documents_verified),
            }
        }


class ELDDocumentManager:
    """
    Manager for handling ELD supporting documents compliance.
    """

    @staticmethod
    def upload_document(driver, document_type, document_date, title,
                        document_file=None, **kwargs):
        """
        Upload a supporting document for a driver.
        """
        # Create the document
        document = ELDDocument.objects.create(
            driver=driver,
            document_type=document_type,
            document_date=document_date,
            title=title,
            document_file=document_file,
            **kwargs
        )

        # Update daily summary
        summary, created = DailyDocumentSummary.objects.get_or_create(
            driver=driver,
            date=document_date
        )
        summary.update_summary()

        logger.info(f"Document uploaded: {driver.name} - {document_type} for {document_date}")

        return document

    @staticmethod
    def get_documents_for_date(driver, date):
        """
        Get all supporting documents for a specific date.
        """
        return ELDDocument.objects.filter(
            driver=driver,
            document_date=date
        ).order_by('document_type', 'created_at')

    @staticmethod
    def check_daily_compliance(driver, date):
        """
        Check if a specific day meets supporting document requirements.
        """
        documents = ELDDocumentManager.get_documents_for_date(driver, date)

        issues = []

        # Check document count (max 8)
        if documents.count() > 8:
            issues.append(f"Exceeds 8-document limit ({documents.count()} documents)")

        # Check for required document types (customize based on your requirements)
        doc_types = set(documents.values_list('document_type', flat=True))

        # Example requirements - adjust as needed
        if 'DISPATCH_RECORD' not in doc_types:
            issues.append("Missing dispatch record")

        # Check if all documents are verified
        unverified = documents.filter(is_verified=False).count()
        if unverified > 0:
            issues.append(f"{unverified} unverified documents")

        return {
            'is_compliant': len(issues) == 0,
            'document_count': documents.count(),
            'issues': issues,
            'documents': documents
        }

    @staticmethod
    def auto_associate_documents_with_duty(driver, date):
        """
        Automatically associate supporting documents with duty status entries
        for the same date.
        """
        documents = ELDDocumentManager.get_documents_for_date(driver, date)
        duty_entries = DutyStatusEntry.objects.filter(
            driver=driver,
            start_time__date=date
        )

        associations_made = 0

        for document in documents:
            # Logic to determine which duty entries this document should be associated with
            relevant_entries = []

            if document.document_type == 'FUEL_RECEIPT':
                # Associate fuel receipts with driving periods
                relevant_entries = duty_entries.filter(duty_status='D')
            elif document.document_type == 'LOADING_DOCUMENTS':
                # Associate loading docs with on-duty periods
                relevant_entries = duty_entries.filter(duty_status='ON')
            elif document.document_type in ['BILL_OF_LADING', 'DISPATCH_RECORD']:
                # Associate these with all duty entries for the day
                relevant_entries = duty_entries

            if relevant_entries.exists():
                document.associated_duty_entries.set(relevant_entries)
                associations_made += 1

        return associations_made

    @staticmethod
    def generate_document_retention_report(driver, start_date, end_date):
        """
        Generate a report showing document retention compliance over a date range.
        """
        summaries = DailyDocumentSummary.objects.filter(
            driver=driver,
            date__range=[start_date, end_date]
        ).order_by('date')

        report_data = {
            'driver': driver,
            'start_date': start_date,
            'end_date': end_date,
            'total_days': (end_date - start_date).days + 1,
            'days_with_documents': summaries.count(),
            'compliant_days': summaries.filter(has_minimum_documents=True, exceeds_limit=False).count(),
            'days_exceeding_limit': summaries.filter(exceeds_limit=True).count(),
            'total_documents': sum(s.document_count for s in summaries),
            'average_docs_per_day': 0,
            'document_type_breakdown': {},
            'daily_details': []
        }

        if summaries.count() > 0:
            report_data['average_docs_per_day'] = report_data['total_documents'] / summaries.count()

        # Get document type breakdown
        all_documents = ELDDocument.objects.filter(
            driver=driver,
            document_date__range=[start_date, end_date]
        )

        type_counts = {}
        for doc in all_documents:
            doc_type = doc.get_document_type_display()
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1

        report_data['document_type_breakdown'] = type_counts

        # Daily details
        for summary in summaries:
            daily_docs = ELDDocument.objects.filter(
                driver=driver,
                document_date=summary.date
            )

            report_data['daily_details'].append({
                'date': summary.date,
                'document_count': summary.document_count,
                'is_compliant': summary.has_minimum_documents and not summary.exceeds_limit,
                'exceeds_limit': summary.exceeds_limit,
                'all_verified': summary.all_documents_verified,
                'document_types': list(daily_docs.values_list('document_type', flat=True)),
                'total_duty_time': summary.total_duty_time,
                'driving_time': summary.driving_time
            })

        return report_data
