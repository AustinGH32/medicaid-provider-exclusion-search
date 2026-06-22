import pandas as pd
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from exclusions.models import StagingNorthCarolina


def parse_date(value):
    # NC stores dates as datetime objects from Excel
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
    # NC NPI field can contain multiple NPIs separated by commas
    # NPIs are always exactly 10 digits
    import re
    if not value:
        return ''
    s = str(value).strip()
    if s.lower() in ('nan', 'none', ''):
        return ''
    matches = re.findall(r'\b\d{10}\b', s)
    return matches[0] if matches else ''


class Command(BaseCommand):
    help = 'Import North Carolina Medicaid exclusions into the staging_north_carolina table.'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to the North Carolina Excel file')
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete all existing North Carolina records before importing'
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
            count, _ = StagingNorthCarolina.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing North Carolina records.'))

        self.stdout.write(f'Reading {excel_path} ...')

        # NC file has 6 header rows before real data starts at row 7
        # header=6 tells pandas to use row 7 (index 6) as the column names
        df = pd.read_excel(excel_path, header=6)

        # rename columns to cleaner names we control
        df.columns = [
            'excluded_entity', 'npi', 'exclusion_date',
            'reason', 'city', 'state', 'zip_code', 'ownership'
        ]

        created = 0
        skipped = 0
        batch   = []

        for row_num, row in df.iterrows():
            try:
                # skip empty rows
                if not clean_str(row.get('excluded_entity')):
                    continue

                obj = StagingNorthCarolina(
                    excluded_entity = clean_str(row.get('excluded_entity')),
                    npi             = extract_npi(row.get('npi')),
                    exclusion_date  = parse_date(row.get('exclusion_date')),
                    reason          = clean_str(row.get('reason')),
                    city            = clean_str(row.get('city')),
                    state           = 'NC',
                    zip_code        = clean_str(str(row.get('zip_code')))[:10],
                    ownership       = clean_str(row.get('ownership')),
                )
                batch.append(obj)

            except Exception as e:
                skipped += 1
                self.stderr.write(f'  Row {row_num}: skipped — {e}')
                continue

            if len(batch) >= batch_size:
                StagingNorthCarolina.objects.bulk_create(batch)
                created += len(batch)
                batch = []
                self.stdout.write(f'  Inserted {created} rows...', ending='\r')
                self.stdout.flush()

        if batch:
            StagingNorthCarolina.objects.bulk_create(batch)
            created += len(batch)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Imported {created} North Carolina records. Skipped {skipped}.'
        ))