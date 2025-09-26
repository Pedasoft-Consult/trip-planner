# Generated Django migration file
# Save as: apps/core/migrations/0002_add_eld_compliance_fields.py

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        # Enhance Driver model
        migrations.AddField(
            model_name='driver',
            name='driver_signature',
            field=models.TextField(blank=True, help_text='Digital signature data for ELD log certification'),
        ),
        migrations.AddField(
            model_name='driver',
            name='co_driver_name',
            field=models.CharField(blank=True, help_text='Name of co-driver for team driving operations', max_length=100),
        ),
        migrations.AddField(
            model_name='driver',
            name='shipping_document_number',
            field=models.CharField(blank=True, help_text='Current shipping document/load number', max_length=100),
        ),
        migrations.AddField(
            model_name='driver',
            name='employee_id',
            field=models.CharField(blank=True, help_text='Driver employee ID for company tracking', max_length=50),
        ),
        migrations.AddField(
            model_name='driver',
            name='home_terminal_address',
            field=models.TextField(blank=True, help_text="Driver's home terminal address"),
        ),
        migrations.AddField(
            model_name='driver',
            name='home_terminal_timezone',
            field=models.CharField(default='UTC', help_text='Home terminal timezone for ELD compliance', max_length=50),
        ),
        migrations.AddField(
            model_name='driver',
            name='carrier_name',
            field=models.CharField(blank=True, help_text='Motor carrier company name', max_length=200),
        ),
        migrations.AddField(
            model_name='driver',
            name='carrier_usdot_number',
            field=models.CharField(blank=True, help_text='USDOT number of motor carrier', max_length=20),
        ),
        migrations.AddField(
            model_name='driver',
            name='eld_device_id',
            field=models.CharField(blank=True, help_text='ELD device identifier', max_length=100),
        ),
        migrations.AddField(
            model_name='driver',
            name='eld_device_model',
            field=models.CharField(blank=True, help_text='ELD device model/manufacturer', max_length=100),
        ),
        migrations.AddField(
            model_name='driver',
            name='last_certification_date',
            field=models.DateTimeField(blank=True, help_text='Last date driver certified their logs', null=True),
        ),
        migrations.AddField(
            model_name='driver',
            name='certification_method',
            field=models.CharField(choices=[('ELECTRONIC', 'Electronic Signature'), ('PIN', 'PIN Entry'), ('BIOMETRIC', 'Biometric')], default='ELECTRONIC', help_text='Method used for log certification', max_length=20),
        ),
        migrations.AddField(
            model_name='driver',
            name='current_duty_status',
            field=models.CharField(choices=[('OFF', 'Off Duty'), ('SB', 'Sleeper Berth'), ('D', 'Driving'), ('ON', 'On Duty (Not Driving)')], default='OFF', help_text='Current duty status', max_length=3),
        ),
        migrations.AddField(
            model_name='driver',
            name='current_cycle_hours',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Current 8-day cycle hours used', max_digits=5),
        ),
        migrations.AddField(
            model_name='driver',
            name='current_daily_drive_hours',
            field=models.DecimalField(decimal_places=2, default=0, help_text="Today's driving hours", max_digits=4),
        ),
        migrations.AddField(
            model_name='driver',
            name='current_daily_duty_hours',
            field=models.DecimalField(decimal_places=2, default=0, help_text="Today's on-duty hours", max_digits=4),
        ),
        migrations.AddField(
            model_name='driver',
            name='last_duty_change_time',
            field=models.DateTimeField(blank=True, help_text='Time of last duty status change', null=True),
        ),
        migrations.AddField(
            model_name='driver',
            name='last_duty_change_location',
            field=models.TextField(blank=True, help_text='Location of last duty status change'),
        ),

        # Enhance Vehicle model
        migrations.AddField(
            model_name='vehicle',
            name='vehicle_number',
            field=models.CharField(blank=True, help_text='Fleet vehicle number or identifier', max_length=50),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='engine_serial_number',
            field=models.CharField(blank=True, help_text='Engine serial number', max_length=100),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='engine_model',
            field=models.CharField(blank=True, help_text='Engine model/manufacturer', max_length=100),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='eld_device_id',
            field=models.CharField(blank=True, help_text='Connected ELD device identifier', max_length=100),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='eld_connection_type',
            field=models.CharField(blank=True, choices=[('OBDII', 'OBD-II Port'), ('J1939', 'J1939 Data Bus'), ('J1708', 'J1708 Data Bus'), ('WIRELESS', 'Wireless Connection')], help_text='How ELD connects to vehicle', max_length=20),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='current_odometer',
            field=models.PositiveIntegerField(default=0, help_text='Current odometer reading in miles'),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='current_engine_hours',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Current engine hours', max_digits=8),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='gvwr',
            field=models.PositiveIntegerField(blank=True, help_text='Gross Vehicle Weight Rating (GVWR) in pounds', null=True),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='vehicle_type',
            field=models.CharField(choices=[('TRUCK', 'Truck'), ('TRACTOR', 'Truck Tractor'), ('BUS', 'Bus'), ('OTHER', 'Other')], default='TRUCK', help_text='Vehicle type classification', max_length=20),
        ),

        # Enhance Company model
        migrations.AddField(
            model_name='company',
            name='city',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='company',
            name='state',
            field=models.CharField(blank=True, max_length=2),
        ),
        migrations.AddField(
            model_name='company',
            name='zip_code',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name='company',
            name='main_office_address',
            field=models.TextField(blank=True, help_text='Main office address for ELD compliance'),
        ),
        migrations.AddField(
            model_name='company',
            name='home_terminal_address',
            field=models.TextField(blank=True, help_text='Home terminal address'),
        ),
        migrations.AddField(
            model_name='company',
            name='home_terminal_timezone',
            field=models.CharField(default='UTC', help_text='Home terminal timezone', max_length=50),
        ),
        migrations.AddField(
            model_name='company',
            name='carrier_name',
            field=models.CharField(help_text='Official carrier name as registered with FMCSA', max_length=200, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='company',
            name='eld_provider',
            field=models.CharField(blank=True, help_text='ELD system provider/vendor', max_length=100),
        ),
        migrations.AddField(
            model_name='company',
            name='eld_registration_id',
            field=models.CharField(blank=True, help_text='ELD system registration ID', max_length=100),
        ),
        migrations.AddField(
            model_name='company',
            name='fmcsa_registration_date',
            field=models.DateField(blank=True, help_text='FMCSA registration date', null=True),
        ),
        migrations.AddField(
            model_name='company',
            name='inspection_contact_name',
            field=models.CharField(blank=True, help_text='Primary contact for DOT inspections', max_length=100),
        ),
        migrations.AddField(
            model_name='company',
            name='inspection_contact_phone',
            field=models.CharField(blank=True, help_text='Phone number for inspection contact', max_length=20),
        ),

        # Add indexes for performance
        migrations.AddIndex(
            model_name='driver',
            index=models.Index(fields=['license_number'], name='core_driver_license_idx'),
        ),
        migrations.AddIndex(
            model_name='driver',
            index=models.Index(fields=['is_active'], name='core_driver_active_idx'),
        ),
        migrations.AddIndex(
            model_name='driver',
            index=models.Index(fields=['current_duty_status'], name='core_driver_duty_status_idx'),
        ),
        migrations.AddIndex(
            model_name='vehicle',
            index=models.Index(fields=['vin'], name='core_vehicle_vin_idx'),
        ),
        migrations.AddIndex(
            model_name='vehicle',
            index=models.Index(fields=['license_plate'], name='core_vehicle_plate_idx'),
        ),
        migrations.AddIndex(
            model_name='vehicle',
            index=models.Index(fields=['is_active'], name='core_vehicle_active_idx'),
        ),

        # Update Meta options for ordering
        migrations.AlterModelOptions(
            name='driver',
            options={'ordering': ['name']},
        ),
        migrations.AlterModelOptions(
            name='vehicle',
            options={'ordering': ['license_plate']},
        ),
        migrations.AlterModelOptions(
            name='company',
            options={'ordering': ['name'], 'verbose_name_plural': 'companies'},
        ),
    ]
