import csv
import re
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from exclusions.models import StagingCalifornia


def extract_npi(provider_number):
    # Provider Number field contains a mix of license numbers and NPIs
    # NPIs are always exactly 10 digits
    # example: "PHA410230, PHA393440, 1821137118" -> "1821137118"
    if not provider_number:
        return ''
    # find all 10 digit numbers in the field
    matches = re.findall(r'\b\d{10}\b', str(provider_number))
    # return the first 10 digit number found, or empty string if none
    return matches[0] if matches else ''


def parse_date(value):
    # California uses MM/DD/YYYY format unlike federal (YYYYMMDD)
    # example: "07/08/2016" -> date(2016, 7, 8)
    if not value:
        return None
    s = str(value).strip()
    if not s or s.lower() == 'nan':
        return None
    try:
        return datetime.strptime(s, '%m/%d/%Y').date()
    except ValueError:
        try:
            return datetime.strptime(s, '%m/%d/%y').date()
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
    help = 'Import California suspended/ineligible providers into the california_exclusion table.'

    def add_arguments(self, parser):
        # path to the CSV file, required
        parser.add_argument('csv_file', type=str, help='Path to the California CSV file')
        # optional flag to wipe existing records before importing
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete all existing California records before importing'
        )
        # optional batch size for bulk_create
        parser.add_argument(
            '--batch-size', type=int, default=500,
            help='Number of rows per bulk_create batch (default: 500)'
        )

    def handle(self, *args, **options):
        csv_path = Path(options['csv_file'])
        if not csv_path.exists():
            raise CommandError(f'File not found: {csv_path}')

        batch_size = options['batch_size']

        # if --clear flag passed, wipe all existing California records first
        if options['clear']:
            count, _ = StagingCalifornia.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing California records.'))

        self.stdout.write(f'Importing from {csv_path} ...')

        created = 0
        skipped = 0
        batch   = []

        with open(csv_path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=1):
                try:
                    # extract NPI from the Provider Number field
                    # which may contain multiple IDs separated by commas
                    npi = extract_npi(row.get('Provider Number', ''))

                    raw_last     = clean_str(row.get('Last Name'))
                    raw_first    = clean_str(row.get('First Name'))
                    raw_business = clean_str(row.get('A/K/A-Also Known As\nD/B/A-Doing Business as'))

                    # California puts business names in the Last Name column
                    # when First Name is N/A it's a business not an individual
                    if raw_first.upper() == 'N/A' or raw_first == '':
                        last_name     = ''
                        first_name    = ''
                        business_name = raw_last
                    else:
                        last_name     = raw_last
                        first_name    = raw_first
                        business_name = raw_business if raw_business.upper() != 'N/A' else ''

                    obj = StagingCalifornia(
                        last_name      = last_name,
                        first_name     = first_name,
                        middle_name    = clean_str(row.get('Middle Name')),
                        business_name  = business_name,
                        npi            = npi,
                        provider_type  = clean_str(row.get('Provider Type')),
                        license_number = clean_str(row.get('License Number')),
                        address        = clean_str(row.get('Address(es)')),
                        state          = 'CA',
                        exclusion_date = parse_date(row.get('Date of Suspension')),
                        active_period  = clean_str(row.get('Active Period')),
                    )
                    batch.append(obj)

                except Exception as e:
                    skipped += 1
                    self.stderr.write(f'  Row {row_num}: skipped — {e}')
                    continue

                # insert in batches instead of one record at a time
                if len(batch) >= batch_size:
                    StagingCalifornia.objects.bulk_create(batch)
                    created += len(batch)
                    batch = []
                    self.stdout.write(f'  Inserted {created} rows...', ending='\r')
                    self.stdout.flush()

            # insert the final batch of remaining records
            if batch:
                StagingCalifornia.objects.bulk_create(batch)
                created += len(batch)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Imported {created} California records. Skipped {skipped}.'
        ))