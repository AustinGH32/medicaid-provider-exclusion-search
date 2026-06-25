import pandas as pd
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from exclusions.models import StagingOregon


def parse_date(value):
    # Oregon stores dates as datetime objects from Excel
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        if hasattr(value, 'date'):
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
    if value is None:
        return ''
    s = str(value).strip()
    return '' if s.lower() in ('nan', 'none', '') else s


class Command(BaseCommand):
    help = 'Import Oregon Medicaid exclusions into the staging_oregon table.'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to the Oregon Excel file')
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete all existing Oregon records before importing'
        )

    def handle(self, *args, **options):
        excel_path = Path(options['excel_file'])
        if not excel_path.exists():
            raise CommandError(f'File not found: {excel_path}')

        if options['clear']:
            count, _ = StagingOregon.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing Oregon records.'))

        self.stdout.write(f'Reading {excel_path} ...')

        # Oregon file is clean with proper column headers
        df = pd.read_excel(excel_path)

        created = 0
        skipped = 0
        batch   = []

        for row_num, row in df.iterrows():
            try:
                # skip empty rows
                if not clean_str(row.get('First Name')) and not clean_str(row.get('Last Name')) and not clean_str(row.get('Business Name')):
                    continue

                obj = StagingOregon(
                    first_name    = clean_str(row.get('First Name')),
                    last_name     = clean_str(row.get('Last Name')),
                    business_name = clean_str(row.get('Business Name')),
                    npi           = clean_str(str(row.get('NPI', ''))).split('.')[0],
                    provider_type = clean_str(row.get('Provider Type')),
                    duration      = clean_str(row.get('Duration')),
                    state         = 'OR',
                    exclusion_date = parse_date(row.get('Effective date')),
                )
                batch.append(obj)

            except Exception as e:
                skipped += 1
                self.stderr.write(f'  Row {row_num}: skipped — {e}')
                continue

        if batch:
            StagingOregon.objects.bulk_create(batch)
            created += len(batch)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Imported {created} Oregon records. Skipped {skipped}.'
        ))