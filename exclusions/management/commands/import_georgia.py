import pandas as pd  # reads Excel files
from datetime import datetime  # converts date integers to real dates
from django.core.management.base import BaseCommand, CommandError  # base class for management commands
from pathlib import Path  # lets us work with file paths cleanly
from exclusions.models import StagingGeorgia  # the new Georgia table model


def parse_date(value):
    # the Excel file stores dates as integers like 19820415
    # converts them into real Python date objects that Django and PostgreSQL understand
    if not value:
        return None
    try:
        s = str(int(float(value))).zfill(8)  # convert to 8 character string, pad with zeros if needed
        if s == '0' or s == '00000000':  # skip empty/zero dates
            return None
        return datetime.strptime(s, '%Y%m%d').date()  # convert string to real date
    except (ValueError, TypeError):
        return None  # if anything goes wrong, return None instead of crashing


def clean_str(value):
    # the Excel file has messy empty values stored as 'nan' or 'None' from pandas
    # this function converts those to empty strings and strips extra whitespace
    if value is None:
        return ''
    s = str(value).strip()  # remove leading/trailing whitespace
    return '' if s.lower() in ('nan', 'none', '') else s  # return empty string for messy values


class Command(BaseCommand):
    # inherits from Django's BaseCommand to create a custom management command
    help = 'Import Georgia DCH exclusions into the georgia_exclusion table.'

    def add_arguments(self, parser):
        # path to the Excel file, required
        parser.add_argument('excel_file', type=str, help='Path to the Georgia DCH Excel file')
        # optional flag to wipe existing records before importing
        # useful for monthly refreshes
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete all existing Georgia records before importing'
        )

    def handle(self, *args, **options):
        # convert file path string into a Path object and check it exists
        excel_path = Path(options['excel_file'])
        if not excel_path.exists():
            raise CommandError(f'File not found: {excel_path}')

        # if --clear flag passed, wipe all existing Georgia records first
        if options['clear']:
            count, _ = StagingGeorgia.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing Georgia records.'))

        self.stdout.write(f'Reading {excel_path} ...')

        # read the Excel file into a pandas dataframe
        # header=1 skips the first row which is the DCH title, uses second row as column names
        df = pd.read_excel(excel_path, header=1)

        # rename columns to cleaner names we control
        df.columns = ['last_name', 'first_name', 'middle_name',
                      'business_name', 'general', 'state',
                      'sanction_date', 'npi', 'extra']

        # counters to track progress
        created = 0
        skipped = 0
        batch = []  # collect records before bulk inserting

        for row_num, row in df.iterrows():  # loop through every row in the Excel file
            try:
                # skip the header row if it snuck into the data
                if clean_str(row.get('last_name')) == 'LAST NAME':
                    continue

                # clean the NPI value and convert '0' to empty string
                # NPI of 0 means no NPI was provided
                npi = clean_str(row.get('npi'))
                npi = '' if npi in ('0', '0.0') else npi

                # create a GeorgiaExclusion object for each row
                # we don't save yet, just collect in the batch list
                obj = StagingGeorgia(
                    last_name      = clean_str(row.get('last_name')),
                    first_name     = clean_str(row.get('first_name')),
                    middle_name    = clean_str(row.get('middle_name')),
                    business_name  = clean_str(row.get('business_name')),
                    npi            = npi,
                    general        = clean_str(row.get('general')),
                    state          = 'GA',  # hardcoded since state column is unreliable
                    exclusion_date = parse_date(row.get('sanction_date')),
                )
                batch.append(obj)

            except Exception as e:
                # if a row fails, skip it and keep going
                skipped += 1
                self.stderr.write(f'  Row {row_num}: skipped — {e}')
                continue

        # insert all records in one database call instead of one at a time
        if batch:
            StagingGeorgia.objects.bulk_create(batch)
            created += len(batch)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Imported {created} Georgia records. Skipped {skipped}.'
        ))