import csv
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from exclusions.models import StagingNewYork


def parse_date(value):
    # New York uses MM/DD/YYYY format
    # example: "07/26/2016" -> date(2016, 7, 26)
    if not value:
        return None
    s = str(value).strip()
    if not s or s.lower() == 'nan':
        return None
    try:
        return datetime.strptime(s, '%m/%d/%Y').date()
    except ValueError:
        return None


def clean_str(value):
    # converts None, 'nan', 'none' to empty string
    # strips extra whitespace from real values
    if value is None:
        return ''
    s = str(value).strip()
    return '' if s.lower() in ('nan', 'none', '') else s


class Command(BaseCommand):
    help = 'Import New York OIG exclusions into the staging_new_york table.'

    def add_arguments(self, parser):
        # path to the Excel file, required
        parser.add_argument('excel_file', type=str, help='Path to the New York Excel file')
        # optional flag to wipe existing records before importing
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete all existing New York records before importing'
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

        # if --clear flag passed, wipe all existing New York records first
        if options['clear']:
            count, _ = StagingNewYork.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing New York records.'))

        self.stdout.write(f'Reading {excel_path} ...')

        # read the Excel file into a pandas dataframe
        import pandas as pd
        df = pd.read_excel(excel_path)

        created = 0
        skipped = 0
        batch   = []

        for row_num, row in df.iterrows():
            try:
                # New York stores the full name in provider_name
                # no separate first/last name fields so we store in business_name
                obj = StagingNewYork(
                    business_name  = clean_str(row.get('provider_name')),
                    npi            = clean_str(row.get('npi_num')),
                    license_number = clean_str(row.get('license_num')),
                    provider_type  = clean_str(row.get('provider_type')),
                    state          = 'NY',
                    exclusion_date = parse_date(row.get('exclusion_effective_date')),
                )
                batch.append(obj)

            except Exception as e:
                skipped += 1
                self.stderr.write(f'  Row {row_num}: skipped — {e}')
                continue

            # insert in batches instead of one record at a time
            if len(batch) >= batch_size:
                StagingNewYork.objects.bulk_create(batch)
                created += len(batch)
                batch = []
                self.stdout.write(f'  Inserted {created} rows...', ending='\r')
                self.stdout.flush()

        # insert the final batch of remaining records
        if batch:
            StagingNewYork.objects.bulk_create(batch)
            created += len(batch)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Imported {created} New York records. Skipped {skipped}.'
        ))