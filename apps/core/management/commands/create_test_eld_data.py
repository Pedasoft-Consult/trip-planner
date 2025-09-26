# apps/core/management/commands/create_test_eld_data.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from apps.core.models import (  # Changed from 'core.models' to 'apps.core.models'
    Driver, Vehicle, Company,ELDLocationManager, ELDDocumentManager
)


class Command(BaseCommand):
    help = 'Create test data for ELD system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing test data first',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing test data...')
            Driver.objects.filter(name__startswith='Test').delete()
            Vehicle.objects.filter(license_plate__startswith='TEST').delete()
            Company.objects.filter(name__startswith='Test').delete()

        self.stdout.write('Creating test data...')

        # Create test company
        company = Company.objects.create(
            name="Test Trucking Company",
            carrier_name="Test Trucking LLC",
            dot_number="123456",
            mc_number="MC123456",
            address="123 Main St",
            city="Los Angeles",
            state="CA",
            zip_code="90210",
            phone="555-0123",
            email="contact@testtruck.com",
            eld_provider="TestELD Solutions",
            home_terminal_timezone="America/Los_Angeles"
        )

        # Create test vehicles
        vehicles = []
        for i in range(1, 4):
            vehicle = Vehicle.objects.create(
                vin=f"1HGCM82633A00000{i}",
                license_plate=f"TEST{i:03d}",
                license_state="CA",
                make="Freightliner",
                model="Cascadia",
                year=2022 + i,
                fuel_capacity=Decimal('200.0'),
                mpg=Decimal('7.5'),
                vehicle_number=f"TRUCK{i:03d}",
                eld_device_id=f"ELD{i:05d}",
                current_odometer=50000 + (i * 10000),
                current_engine_hours=Decimal(str(2000 + (i * 500))),
                vehicle_type='TRACTOR'
            )
            vehicles.append(vehicle)

        # Create test drivers
        drivers = []
        driver_names = [
            ("John Smith", "CA12345678"),
            ("Maria Rodriguez", "TX87654321"),
            ("David Johnson", "FL11223344")
        ]

        for name, license_num in driver_names:
            driver = Driver.objects.create(
                name=f"Test {name}",
                license_number=license_num,
                license_state="CA",
                phone="555-0100",
                email=f"{name.lower().replace(' ', '.')}@testtruck.com",
                carrier_name=company.carrier_name,
                carrier_usdot_number=company.dot_number,
                home_terminal_address=company.address,
                home_terminal_timezone=company.home_terminal_timezone,
                eld_device_id=f"ELD{len(drivers) + 1:05d}",
                employee_id=f"EMP{len(drivers) + 1:03d}"
            )
            drivers.append(driver)

        # Create sample duty status entries
        self.stdout.write('Creating duty status entries...')
        base_date = timezone.now().date() - timedelta(days=7)

        for day in range(7):
            current_date = base_date + timedelta(days=day)

            for i, driver in enumerate(drivers):
                vehicle = vehicles[i % len(vehicles)]

                # Start of day - Off Duty
                start_time = timezone.make_aware(
                    datetime.combine(current_date, datetime.min.time().replace(hour=6))
                )

                ELDLocationManager.record_duty_status_change(
                    driver=driver,
                    vehicle=vehicle,
                    new_status='OFF',
                    latitude=Decimal('34.0522'),
                    longitude=Decimal('-118.2437'),
                    location_method='GPS'
                )

                # On Duty (Not Driving) - Pre-trip inspection
                on_duty_time = start_time + timedelta(hours=1)
                ELDLocationManager.record_duty_status_change(
                    driver=driver,
                    vehicle=vehicle,
                    new_status='ON',
                    latitude=Decimal('34.0525'),
                    longitude=Decimal('-118.2440'),
                    location_method='GPS'
                )

                # Driving
                driving_time = on_duty_time + timedelta(minutes=30)
                ELDLocationManager.record_duty_status_change(
                    driver=driver,
                    vehicle=vehicle,
                    new_status='D',
                    latitude=Decimal('34.0530'),
                    longitude=Decimal('-118.2445'),
                    location_method='GPS'
                )

                # Back to On Duty - Loading/Unloading
                loading_time = driving_time + timedelta(hours=5)
                ELDLocationManager.record_duty_status_change(
                    driver=driver,
                    vehicle=vehicle,
                    new_status='ON',
                    latitude=Decimal('36.1627'),
                    longitude=Decimal('-115.1370'),  # Las Vegas area
                    location_method='GPS'
                )

                # Off Duty - Rest
                off_duty_time = loading_time + timedelta(hours=2)
                ELDLocationManager.record_duty_status_change(
                    driver=driver,
                    vehicle=vehicle,
                    new_status='OFF',
                    latitude=Decimal('36.1630'),
                    longitude=Decimal('-115.1375'),
                    location_method='GPS'
                )

        # Create sample documents
        self.stdout.write('Creating sample documents...')
        document_types = [
            'BILL_OF_LADING',
            'DISPATCH_RECORD',
            'FUEL_RECEIPT',
            'LOADING_DOCUMENTS'
        ]

        for day in range(3):  # Last 3 days
            doc_date = timezone.now().date() - timedelta(days=day)

            for driver in drivers[:2]:  # Just first 2 drivers
                for doc_type in document_types[:2]:  # 2 docs per day
                    ELDDocumentManager.upload_document(
                        driver=driver,
                        document_type=doc_type,
                        document_date=doc_date,
                        title=f"Test {doc_type.replace('_', ' ').title()}",
                        description=f"Sample {doc_type} document for testing",
                        location_city="Los Angeles",
                        location_state="CA",
                        is_required=True
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created test data:\n'
                f'- 1 Company\n'
                f'- {len(vehicles)} Vehicles\n'
                f'- {len(drivers)} Drivers\n'
                f'- Duty status entries for the last 7 days\n'
                f'- Sample documents for the last 3 days'
            )
        )

        self.stdout.write('\nYou can now:')
        self.stdout.write('1. Visit /admin to view the data')
        self.stdout.write('2. Test the ELD functionality')
        self.stdout.write('3. Generate compliance reports')
