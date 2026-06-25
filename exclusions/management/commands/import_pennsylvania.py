import csv
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from exclusions.models import StagingPennsylvania


def parse_date(value):
    # Pennsylvania uses MM/DD/YYYY format
    if not value:
        return None
    s = str(value).strip()
    if not s or s.lower() in ('nan', 'none', ''):
        return None
    for fmt in ('%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def clean_str(value):
    # converts None, 'nan', 'none' to empty string
    if value is None:
        return ''
    s = str(value).strip()
    return '' if s.lower() in ('nan', 'none', '') else s


class Command(BaseCommand):
    help = 'Import Pennsylvania Medicaid exclusions into the staging_pennsylvania table.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the Pennsylvania CSV file')
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete all existing Pennsylvania records before importing'
        )
        parser.add_argument(
            '--batch-size', type=int, default=500,
            help='Number of rows per bulk_create batch (default: 500)'
        )

    def handle(self, *args, **options):
        csv_path = Path(options['csv_file'])
        if not csv_path.exists():
            raise CommandError(f'File not found: {csv_path}')

        batch_size = options['batch_size']

        if options['clear']:
            count, _ = StagingPennsylvania.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing Pennsylvania records.'))

        self.stdout.write(f'Importing from {csv_path} ...')

        created = 0
        skipped = 0
        batch   = []

        with open(csv_path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=1):
                try:
                    # Pennsylvania has separate first/last name fields
                    # NAM_BUSNS_MP is the business name field
                    # IDN_NPI is the NPI field
                    last_name     = clean_str(row.get('NAM_LAST_PROVR'))
                    first_name    = clean_str(row.get('NAM_FIRST_PROVR'))
                    business_name = clean_str(row.get('NAM_BUSNS_MP'))

                    # if no individual name use the combined ProviderName as business name
                    if not last_name and not first_name and not business_name:
                        business_name = clean_str(row.get('ProviderName'))

                    obj = StagingPennsylvania(
                        last_name      = last_name,
                        first_name     = first_name,
                        middle_name    = clean_str(row.get('NAM_MIDDLE_PROVR')),
                        business_name  = business_name,
                        npi            = clean_str(row.get('IDN_NPI')),
                        license_number = clean_str(row.get('LicenseNumber')),
                        status         = clean_str(row.get('Status')),
                        state          = 'PA',
                        exclusion_date = parse_date(row.get('BeginDate')),
                        end_date       = parse_date(row.get('EndDate')),
                    )
                    batch.append(obj)

                except Exception as e:
                    skipped += 1
                    self.stderr.write(f'  Row {row_num}: skipped — {e}')
                    continue

                if len(batch) >= batch_size:
                    StagingPennsylvania.objects.bulk_create(batch)
                    created += len(batch)
                    batch = []
                    self.stdout.write(f'  Inserted {created} rows...', ending='\r')
                    self.stdout.flush()

            if batch:
                StagingPennsylvania.objects.bulk_create(batch)
                created += len(batch)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Imported {created} Pennsylvania records. Skipped {skipped}.'
        ))