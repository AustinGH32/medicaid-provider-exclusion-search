import pdfplumber
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from exclusions.models import StagingNewJersey


def parse_date(value):
    # NJ uses MM/DD/YYYY format
    if not value:
        return None
    s = str(value).strip()
    if not s or s.lower() in ('nan', 'none', 'permanent', ''):
        return None
    for fmt in ('%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def clean_str(value):
    # converts None to empty string and strips whitespace
    if value is None:
        return ''
    # replace newlines within cells with a space
    s = str(value).strip().replace('\n', ' ')
    return '' if s.lower() in ('nan', 'none', '') else s


def extract_npi(value):
    # NPI is always exactly 10 digits
    import re
    if not value:
        return ''
    s = clean_str(value)
    matches = re.findall(r'\b\d{10}\b', s)
    return matches[0] if matches else ''


class Command(BaseCommand):
    help = 'Import New Jersey Medicaid exclusions from PDF into staging_new_jersey table.'

    def add_arguments(self, parser):
        parser.add_argument('pdf_file', type=str, help='Path to the New Jersey PDF file')
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete all existing New Jersey records before importing'
        )

    def handle(self, *args, **options):
        pdf_path = Path(options['pdf_file'])
        if not pdf_path.exists():
            raise CommandError(f'File not found: {pdf_path}')

        if options['clear']:
            count, _ = StagingNewJersey.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing New Jersey records.'))

        self.stdout.write(f'Reading {pdf_path} ...')

        created = 0
        skipped = 0
        batch   = []

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()

                for table in tables:
                    # skip header rows — they contain column names not data
                    for row in table:
                        # skip empty rows
                        if not any(row):
                            continue
                        # skip header rows by checking if first cell is a known header
                        if row[0] and row[0].strip().upper() in (
                            'PROVIDER NAME', 'PROVIDERNAME', 'NAME'
                        ):
                            continue

                        try:
                            obj = StagingNewJersey(
                                # NJ combines all names into provider name column
                                business_name   = clean_str(row[0]),
                                title           = clean_str(row[1]) if len(row) > 1 else '',
                                npi             = extract_npi(row[2]) if len(row) > 2 else '',
                                address         = clean_str(row[3]) if len(row) > 3 else '',
                                city            = clean_str(row[4]) if len(row) > 4 else '',
                                state           = clean_str(row[5]) if len(row) > 5 else 'NJ',
                                zip_code        = clean_str(row[6])[:10] if len(row) > 6 else '',
                                action          = clean_str(row[7]) if len(row) > 7 else '',
                                exclusion_date  = parse_date(row[8]) if len(row) > 8 else None,
                                expiration_date = parse_date(row[9]) if len(row) > 9 else None,
                            )
                            batch.append(obj)

                        except Exception as e:
                            skipped += 1
                            self.stderr.write(f'  Page {page_num}: skipped — {e}')
                            continue

                if len(batch) >= 500:
                    StagingNewJersey.objects.bulk_create(batch)
                    created += len(batch)
                    batch = []
                    self.stdout.write(f'  Inserted {created} rows...', ending='\r')
                    self.stdout.flush()

        if batch:
            StagingNewJersey.objects.bulk_create(batch)
            created += len(batch)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Imported {created} New Jersey records. Skipped {skipped}.'
        ))