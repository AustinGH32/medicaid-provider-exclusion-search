import pandas as pd
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from exclusions.models import StagingOhio


def parse_date(value):
    # Ohio stores dates as datetime objects from Excel
    # NaT is pandas' null value for dates - we need to handle it explicitly
    if value is None:
        return None
    # check for pandas NaT (Not a Time) which is their null date value
    try:
        import pandas as pd
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        if hasattr(value, 'date'):
            # already a datetime object from pandas - just extract date part
            return value.date()
        s = str(value).strip()
        if not s or s.lower() in ('nan', 'none', 'nat'):
            return None
        return datetime.strptime(s[:10], '%Y-%m-%d').date()
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
    # Ohio NPI field can contain multiple NPIs separated by commas
    # example: "1447317433, 1598934424" -> "1447317433" (take first one)
    # NPIs are always exactly 10 digits
    import re
    if not value:
        return ''
    matches = re.findall(r'\b\d{10}\b', str(value))
    return matches[0] if matches else ''


class Command(BaseCommand):
    help = 'Import Ohio Medicaid exclusions into the staging_ohio table.'

    def add_arguments(self, parser):
        # path to the Excel file, required
        parser.add_argument('excel_file', type=str, help='Path to the Ohio Excel file')
        # optional flag to wipe existing records before importing
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete all existing Ohio records before importing'
        )
        # optional batch size for bulk_create
        parser.add_argument(
            '--batch-size', type=int, default=500,
            help='Number of rows per bulk_create batch (default: 500)'
        )

    def handle(self, *args, **options):
        excel_path = Path(options['excel_file'])
        if not excel_path.exists():
            raise CommandError(f'File not found: {excel_path}')

        batch_size = options['batch_size']

        # if --clear flag passed, wipe all existing Ohio records first
        if options['clear']:
            count, _ = StagingOhio.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing Ohio records.'))

        self.stdout.write(f'Reading {excel_path} ...')

        created = 0
        skipped = 0
        batch   = []

        
        # SHEET 1: Individuals
        # Has separate first/last/middle name fields and DOB
        self.stdout.write('Processing Individuals sheet...')
        df_individuals = pd.read_excel(excel_path, sheet_name='Individuals')

        for row_num, row in df_individuals.iterrows():
            try:
                obj = StagingOhio(
                    last_name      = clean_str(row.get('Last Name')),
                    first_name     = clean_str(row.get('First Name')),
                    middle_name    = clean_str(row.get('Middle Name')),
                    dob            = parse_date(row.get('DOB')),
                    npi            = extract_npi(row.get('NPI')),
                    provider_type  = clean_str(row.get('Provider Type')),
                    status         = clean_str(row.get('Status')),
                    state          = 'OH',
                    exclusion_date = parse_date(row.get('Action Date')),
                )
                batch.append(obj)

            except Exception as e:
                skipped += 1
                self.stderr.write(f'  Individuals row {row_num}: skipped — {e}')
                continue

            if len(batch) >= batch_size:
                StagingOhio.objects.bulk_create(batch)
                created += len(batch)
                batch = []
                self.stdout.write(f'  Inserted {created} rows...', ending='\r')
                self.stdout.flush()

       
        # SHEET 2: Organizations
        # Has a single organization name field and address details
        self.stdout.write('Processing Organizations sheet...')
        df_organizations = pd.read_excel(excel_path, sheet_name='Organizations')

        for row_num, row in df_organizations.iterrows():
            try:
                obj = StagingOhio(
                    business_name  = clean_str(row.get('Organization Name')),
                    npi            = extract_npi(row.get('NPI')),
                    address        = clean_str(row.get('Address 1')),
                    city           = clean_str(row.get('City')),
                    state          = clean_str(row.get('State')) or 'OH',
                    zip_code = str(int(float(row.get('Zip Code')))) if row.get('Zip Code') and str(row.get('Zip Code')).lower() not in ('nan', 'none') else '',
                    provider_type  = clean_str(row.get('Provider Type')),
                    status         = clean_str(row.get('Status')),
                    exclusion_date = parse_date(row.get('Action Date')),
                )
                batch.append(obj)

            except Exception as e:
                skipped += 1
                self.stderr.write(f'  Organizations row {row_num}: skipped — {e}')
                continue

            if len(batch) >= batch_size:
                StagingOhio.objects.bulk_create(batch)
                created += len(batch)
                batch = []
                self.stdout.write(f'  Inserted {created} rows...', ending='\r')
                self.stdout.flush()

        # insert the final batch of remaining records
        if batch:
            StagingOhio.objects.bulk_create(batch)
            created += len(batch)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Imported {created} Ohio records. Skipped {skipped}.'
        ))