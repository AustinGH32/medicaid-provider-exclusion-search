import pandas as pd
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from exclusions.models import StagingNorthDakota


def parse_date(value):
    # ND stores dates as datetime objects from Excel
    # some are strings like "9/18/2014", others are datetime objects
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        if hasattr(value, 'date'):
            # already a datetime object from pandas
            return value.date()
        s = str(value).strip()
        if not s or s.lower() in ('nan', 'none', 'nat'):
            return None
        # try common date formats
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y'):
            try:
                return datetime.strptime(s[:10], fmt).date()
            except ValueError:
                continue
        return None
    except (ValueError, TypeError):
        return None


def clean_str(value):
    # converts None, 'nan', 'none' to empty string
    # strips extra whitespace from real values
    if value is None:
        return ''
    s = str(value).strip()
    return '' if s.lower() in ('nan', 'none', '') else s


def extract_npi(value):
    # ND NPI field - extract 10 digit number
    import re
    if not value:
        return ''
    s = str(value).strip()
    if s.lower() in ('nan', 'none', ''):
        return ''
    matches = re.findall(r'\b\d{10}\b', s)
    return matches[0] if matches else ''


class Command(BaseCommand):
    help = 'Import North Dakota Medicaid exclusions into the staging_north_dakota table.'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to the North Dakota Excel file')
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete all existing North Dakota records before importing'
        )
        parser.add_argument(
            '--batch-size', type=int, default=500,
            help='Number of rows per bulk_create batch (default: 500)'
        )

    def handle(self, *args, **options):
        excel_path = Path(options['excel_file'])
        if not excel_path.exists():
            raise CommandError(f'File not found: {excel_path}')

        batch_size = options['batch_size']

        if options['clear']:
            count, _ = StagingNorthDakota.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing North Dakota records.'))

        self.stdout.write(f'Reading {excel_path} ...')

        # ND file has 4 header rows before the actual data starts at row 5
        # header=4 tells pandas to use row 5 (index 4) as the column names
        df = pd.read_excel(excel_path, header=4)

        # rename columns to cleaner names we control
        # ND columns: Provider Name, Business Name, Street Address, City, State,
        # Zip, Medicaid Provider Number, Medicare Provider Number, NPI,
        # License Number, Provider Type, Practice State, Sanction Type,
        # Exclusion Date, Reason for Exclusion, Verification Contact
        df.columns = [
            'provider_name', 'business_name', 'address', 'city', 'state',
            'zip_code', 'medicaid_provider_num', 'medicare_provider_num', 'npi',
            'license_number', 'provider_type', 'practice_state', 'sanction_type',
            'exclusion_date', 'reason', 'verification_contact'
        ]

        created = 0
        skipped = 0
        batch   = []

        for row_num, row in df.iterrows():
            try:
                # skip empty rows
                if not clean_str(row.get('provider_name')) and not clean_str(row.get('business_name')):
                    continue

                obj = StagingNorthDakota(
                    provider_name  = clean_str(row.get('provider_name')),
                    business_name  = clean_str(row.get('business_name')),
                    npi            = extract_npi(row.get('npi')),
                    license_number = clean_str(row.get('license_number')),
                    provider_type  = clean_str(row.get('provider_type')),
                    sanction_type  = clean_str(row.get('sanction_type')),
                    address        = clean_str(row.get('address')),
                    city           = clean_str(row.get('city')),
                    state          = 'ND',
                    zip_code       = clean_str(row.get('zip_code'))[:10],
                    exclusion_date = parse_date(row.get('exclusion_date')),
                )
                batch.append(obj)

            except Exception as e:
                skipped += 1
                self.stderr.write(f'  Row {row_num}: skipped — {e}')
                continue

            if len(batch) >= batch_size:
                StagingNorthDakota.objects.bulk_create(batch)
                created += len(batch)
                batch = []
                self.stdout.write(f'  Inserted {created} rows...', ending='\r')
                self.stdout.flush()

        if batch:
            StagingNorthDakota.objects.bulk_create(batch)
            created += len(batch)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Imported {created} North Dakota records. Skipped {skipped}.'
        ))