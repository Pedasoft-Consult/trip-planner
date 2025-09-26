"""
ELD (Electronic Logging Device) models for FMCSA compliance.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import BaseModel, Driver, Vehicle, Location
from apps.trips.models import Trip


class ELDLog(BaseModel):
    """
    Daily ELD log sheet for a driver.
    """
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='eld_logs'
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='eld_logs'
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='eld_logs'
    )

    # Log date
    log_date = models.DateField()

    # Odometer readings
    starting_odometer = models.PositiveIntegerField(default=0)
    ending_odometer = models.PositiveIntegerField(default=0)

    # Daily totals
    total_miles_driven = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        default=0
    )
    total_drive_time = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        help_text="Total driving time in hours"
    )
    total_on_duty_time = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        help_text="Total on-duty time in hours"
    )
    total_off_duty_time = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        help_text="Total off-duty time in hours"
    )

    # Cycle information
    cycle_hours_used = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(70)]
    )

    # Compliance flags
    is_compliant = models.BooleanField(default=True)
    violation_summary = models.TextField(blank=True)  # Renamed from 'violations'

    # Certification
    is_certified = models.BooleanField(default=False)
    certified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'eld_log'
        unique_together = ['driver', 'log_date']
        ordering = ['-log_date']

    def __str__(self):
        return f"ELD Log - {self.driver.name} - {self.log_date}"


class DutyStatusEntry(BaseModel):
    """
    Individual duty status change entries within an ELD log.
    """
    DUTY_STATUS_CHOICES = [
        ('OFF', 'Off Duty'),
        ('SB', 'Sleeper Berth'),
        ('D', 'Driving'),
        ('ON', 'On Duty (Not Driving)'),
    ]

    eld_log = models.ForeignKey(
        ELDLog,
        on_delete=models.CASCADE,
        related_name='duty_entries'
    )

    # Duty status information
    duty_status = models.CharField(max_length=3, choices=DUTY_STATUS_CHOICES)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=0)

    # Location information
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='duty_entries'
    )
    location_description = models.CharField(max_length=200, blank=True)

    # Odometer reading at time of status change
    odometer_reading = models.PositiveIntegerField(default=0)

    # Additional information
    remarks = models.CharField(max_length=200, blank=True)
    is_automatic = models.BooleanField(default=True)

    class Meta:
        db_table = 'eld_duty_status_entry'
        ordering = ['eld_log', 'start_time']

    def __str__(self):
        return f"{self.get_duty_status_display()} - {self.start_time}"


class ELDViolation(BaseModel):
    """
    HOS violations detected during trip planning or log generation.
    """
    VIOLATION_TYPES = [
        ('CYCLE_EXCEEDED', '70-hour cycle exceeded'),
        ('DAILY_DRIVE_EXCEEDED', '11-hour daily drive limit exceeded'),
        ('DAILY_DUTY_EXCEEDED', '14-hour daily duty limit exceeded'),
        ('INSUFFICIENT_REST', 'Insufficient off-duty time'),
        ('MISSING_LOG', 'Missing or incomplete log'),
        ('FORM_MANNER', 'Form and manner violation'),
    ]

    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    eld_log = models.ForeignKey(
        ELDLog,
        on_delete=models.CASCADE,
        related_name='violations'  # This is fine now since we renamed the field above
    )

    violation_type = models.CharField(max_length=50, choices=VIOLATION_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    description = models.TextField()

    # Time information
    violation_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=0)

    # Resolution
    is_resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'eld_violation'
        ordering = ['-violation_time']

    def __str__(self):
        return f"{self.get_violation_type_display()} - {self.violation_time.date()}"


class ELDDocument(BaseModel):
    """
    Supporting documents for ELD logs (bills of lading, receipts, etc.).
    """
    DOCUMENT_TYPES = [
        ('BILL_OF_LADING', 'Bill of Lading'),
        ('DISPATCH_RECORD', 'Dispatch Record'),
        ('FUEL_RECEIPT', 'Fuel Receipt'),
        ('TOLL_RECEIPT', 'Toll Receipt'),
        ('REPAIR_ORDER', 'Repair Order'),
        ('OTHER', 'Other'),
    ]

    eld_log = models.ForeignKey(
        ELDLog,
        on_delete=models.CASCADE,
        related_name='documents'
    )

    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # File information
    file = models.FileField(upload_to='eld_documents/', null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(default=0)

    # Document metadata
    document_date = models.DateField()
    reference_number = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'eld_document'
        ordering = ['-document_date']

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.title}"


class ELDAuditLog(BaseModel):
    """
    Audit trail for ELD log modifications and certifications.
    """
    ACTION_CHOICES = [
        ('CREATED', 'Log Created'),
        ('MODIFIED', 'Log Modified'),
        ('CERTIFIED', 'Log Certified'),
        ('UNCERTIFIED', 'Log Uncertified'),
        ('VIOLATION_ADDED', 'Violation Added'),
        ('VIOLATION_RESOLVED', 'Violation Resolved'),
    ]

    eld_log = models.ForeignKey(
        ELDLog,
        on_delete=models.CASCADE,
        related_name='audit_entries'
    )

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField()

    # User information (if applicable)
    user_name = models.CharField(max_length=100, blank=True)
    user_type = models.CharField(max_length=50, blank=True)  # driver, fleet_manager, etc.

    # Technical details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = 'eld_audit_log'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_display()} - {self.created_at}"
