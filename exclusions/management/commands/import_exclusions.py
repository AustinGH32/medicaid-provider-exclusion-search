import csv
from datetime import datetime
from pathlib import Path
from exclusions.models import StagingOIG
from django.core.management.base import BaseCommand, CommandError

# This command imports exclusion data from a CSV file into the database.
def parse_date(value):
    # the CSV stores the date as an 8-digit number (YYYYMMDD). This function converts it to a string.
    # zfill(8) ensures that the string is 8 characters long, padding with zeros if necessary.
    # Returns None if the value is empty, zero, or cannot be parsed as a date.
    # strptime is used to convert string into a real date
    if not value:
        return None
    try:
        s = str(int(float(value))).zfill(8)
        if s == '0' or s == '00000000':
            return None
        return datetime.strptime(s, '%Y%m%d').date()
    except (ValueError, TypeError):
        return None

# This function cleans string values by stripping whitespace and converting certain values to empty strings.
def clean_str(value):
    if value is None:
        return ''
    s = str(value).strip()
    return '' if s.lower() in ('nan', 'none', '') else s

# Inherits Django's BaseCommand to create a custom management command.
# Gives all managements command functionality
class Command(BaseCommand):
    # A short description of the command, shown when running `python manage.py help`.
    help = 'Import OIG exclusions from the monthly LEIE CSV file.'
    
    # Defines what arguments the command accepts.
    def add_arguments(self, parser):
        # Positional argument for the path to the CSV file.
        parser.add_argument('csv_file', type=str, help='Path to the OIG LEIE CSV file')
        # Optional flag to clear existing records before importing.
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete all existing records before importing'
        )
        # Optional argument to specify batch size for bulk_create, with a default of 500.
        parser.add_argument(
            '--batch-size', type=int, default=500,
            help='Number of rows per bulk_create batch (default: 500)'
        )

    # Django calls this automatically when command runs.
    def handle(self, *args, **options):
        # Coverts file path string into a Path object and checks if the file exists. If not, raises an error.
        csv_path = Path(options['csv_file'])
        if not csv_path.exists():
            raise CommandError(f'File not found: {csv_path}')

        batch_size = options['batch_size']

        # If --clear flag is passed, delete all existing records first.
        if options['clear']:
            count, _ = StagingOIG.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing records.'))

        self.stdout.write(f'Importing from {csv_path} ...')

        # Counters for tracking how many records were created and skipped.
        created = 0
        skipped = 0
        batch   = []

        # utf-8-sig — handles the invisible BOM character that Microsoft adds to CSV files.
        # csv.DictReader — reads each row as a dictionary so we can access columns by name like row.get('LASTNAME').
        # enumerate(reader, start=1) — gives us a row number alongside each row, useful for error messages.
        # batch.append(obj) — we don't save each record one by one (that would be 83,000 database calls!). 
        # We collect them in a batch and insert them all at once.
        # bulk_create — inserts the whole batch in a single database call, much faster.

        with open(csv_path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=1):
                try:
                    obj = StagingOIG(
                        last_name     = clean_str(row.get('LASTNAME')),
                        first_name    = clean_str(row.get('FIRSTNAME')),
                        middle_name   = clean_str(row.get('MIDNAME')),
                        business_name = clean_str(row.get('BUSNAME')),
                        npi           = clean_str(row.get('NPI')) if clean_str(row.get('NPI')) not in ('0', '') else '',
                        upin          = clean_str(row.get('UPIN')),
                        dob           = parse_date(row.get('DOB')),
                        general       = clean_str(row.get('GENERAL')),
                        specialty     = clean_str(row.get('SPECIALTY')),
                        address       = clean_str(row.get('ADDRESS')),
                        city          = clean_str(row.get('CITY')),
                        state         = clean_str(row.get('STATE')),
                        zip_code      = clean_str(row.get('ZIP')),
                        exclusion_type     = clean_str(row.get('EXCLTYPE')).lower(),
                        exclusion_date     = parse_date(row.get('EXCLDATE')),
                        reinstatement_date = parse_date(row.get('REINDATE')),
                        waiver_date        = parse_date(row.get('WAIVERDATE')),
                        waiver_state       = clean_str(row.get('WVRSTATE')),
                    )
                    batch.append(obj)
                except Exception as e:
                    skipped += 1
                    self.stderr.write(f'  Row {row_num}: skipped — {e}')
                    continue

                if len(batch) >= batch_size:
                    StagingOIG.objects.bulk_create(batch)
                    created += len(batch)
                    batch = []
                    self.stdout.write(f'  Inserted {created} rows...', ending='\r')
                    self.stdout.flush()
                
            if batch:
                StagingOIG.objects.bulk_create(batch)
                created += len(batch)

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(
                f'Done. Imported {created} records. Skipped {skipped}.'
            ))
            