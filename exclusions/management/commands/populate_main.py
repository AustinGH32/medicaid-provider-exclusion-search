from django.core.management.base import BaseCommand
from exclusions.models import (
    StagingOIG, StagingGeorgia, StagingCalifornia,
    StagingNewYork, StagingOhio, StagingNorthDakota, StagingNorthCarolina,
    StagingOregon, StagingPennsylvania, StagingNewJersey,
    MainExclusion
)
class Command(BaseCommand):
    help = 'Populate main_exclusion table from all staging tables.'

    def add_arguments(self, parser):
        # optional flag to wipe main_exclusion before repopulating
        # useful when re-running after a monthly data refresh
        parser.add_argument(
            '--clear', action='store_true',
            help='Clear main_exclusion before populating'
        )

    def handle(self, *args, **options):
        # if --clear flag passed, delete all existing main_exclusion records first
        # this lets us re-run the command cleanly after importing new staging data
        if options['clear']:
            count, _ = MainExclusion.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing records.'))

        # track total records inserted across all three staging tables
        total = 0

        
        # Populate from federal OIG staging table (StagingOIG)
        # This is the largest table with 83,256 records
        # Maps all available federal fields to the unified main_exclusion fields
        
        self.stdout.write('Populating from StagingOIG...')
        batch = []
        for record in StagingOIG.objects.all():
            # create a MainExclusion object for each federal record
            # we don't save yet, collect in batch for bulk insert
            batch.append(MainExclusion(
                first_name         = record.first_name,
                last_name          = record.last_name,
                middle_name        = record.middle_name,
                business_name      = record.business_name,
                npi                = record.npi,
                general            = record.general,
                specialty          = record.specialty,    # federal only field
                address            = record.address,      # federal only field
                city               = record.city,         # federal only field
                state              = record.state,
                zip_code           = record.zip_code,     # federal only field
                exclusion_type     = record.exclusion_type, # federal only field
                exclusion_date     = record.exclusion_date,
                reinstatement_date = record.reinstatement_date, # federal only field
                source             = 'Medicare',          # label for this source
                source_id          = record.id,           # preserves link back to staging record
            ))
            # insert in batches of 500 instead of one at a time
            # bulk_create is much faster for large datasets
            if len(batch) >= 500:
                MainExclusion.objects.bulk_create(batch)
                total += len(batch)
                batch = []
                self.stdout.write(f'  Inserted {total} records...', ending='\r')
                self.stdout.flush()

        # insert any remaining records that didn't fill a full batch
        if batch:
            MainExclusion.objects.bulk_create(batch)
            total += len(batch)
        self.stdout.write(f'  Done. {total} Medicare records.')

        
        # Populate from Georgia staging table (StagingGeorgia)
        # Georgia has fewer fields than federal so some main_exclusion
        # fields will be left empty (specialty, city, zip_code, etc.)
        
        self.stdout.write('Populating from StagingGeorgia...')
        batch = []
        ga_count = 0  # separate counter to report Georgia-specific count
        for record in StagingGeorgia.objects.all():
            batch.append(MainExclusion(
                first_name     = record.first_name,
                last_name      = record.last_name,
                middle_name    = record.middle_name,
                business_name  = record.business_name,
                npi            = record.npi,
                general        = record.general,
                state          = record.state,
                exclusion_date = record.exclusion_date,
                source         = 'GA - State Level',  # label identifies Georgia records
                source_id      = record.id,            # links back to staging_georgia
                # fields not available in Georgia data are left empty:
                # specialty, address, city, zip_code, exclusion_type, reinstatement_date
            ))
            if len(batch) >= 500:
                MainExclusion.objects.bulk_create(batch)
                ga_count += len(batch)
                batch = []

        if batch:
            MainExclusion.objects.bulk_create(batch)
            ga_count += len(batch)
        total += ga_count
        self.stdout.write(f'  Done. {ga_count} Georgia records.')

       
        # Populate from California staging table (StagingCalifornia)
        # California has different fields than both federal and Georgia
        # provider_type is California's equivalent of specialty/general
        
        self.stdout.write('Populating from StagingCalifornia...')
        batch = []
        ca_count = 0  # separate counter to report California-specific count
        for record in StagingCalifornia.objects.all():
            batch.append(MainExclusion(
                first_name     = record.first_name,
                last_name      = record.last_name,
                middle_name    = record.middle_name,
                business_name  = record.business_name,
                npi            = record.npi,
                provider_type  = record.provider_type,  # California's version of specialty
                address        = record.address,         # California has full address field
                state          = record.state,
                exclusion_date = record.exclusion_date,
                source         = 'CA - State Level',    # label identifies California records
                source_id      = record.id,              # links back to staging_california
                # fields not available in California data are left empty:
                # general, specialty, city, zip_code, exclusion_type, reinstatement_date
            ))
            if len(batch) >= 500:
                MainExclusion.objects.bulk_create(batch)
                ca_count += len(batch)
                batch = []

        if batch:
            MainExclusion.objects.bulk_create(batch)
            ca_count += len(batch)
        total += ca_count
        self.stdout.write(f'  Done. {ca_count} California records.')

        
        # Populate from New York staging table (StagingNewYork)
        # NY stores full name in business_name since no separate first/last fields
        
        self.stdout.write('Populating from StagingNewYork...')
        batch = []
        ny_count = 0
        for record in StagingNewYork.objects.all():
            batch.append(MainExclusion(
                business_name  = record.business_name,
                npi            = record.npi,
                provider_type  = record.provider_type,
                state          = record.state,
                exclusion_date = record.exclusion_date,
                source         = 'NY - State Level',
                source_id      = record.id,
            ))
            if len(batch) >= 500:
                MainExclusion.objects.bulk_create(batch)
                ny_count += len(batch)
                batch = []
        if batch:
            MainExclusion.objects.bulk_create(batch)
            ny_count += len(batch)
        total += ny_count
        self.stdout.write(f'  Done. {ny_count} New York records.')

        
        # Populate from Ohio staging table (StagingOhio)
        # Ohio has both individuals (first/last name) and organizations
        # also has address fields for organizations and DOB for individuals
        
        self.stdout.write('Populating from StagingOhio...')
        batch = []
        oh_count = 0
        for record in StagingOhio.objects.all():
            batch.append(MainExclusion(
                first_name     = record.first_name,
                last_name      = record.last_name,
                middle_name    = record.middle_name,
                business_name  = record.business_name,
                npi            = record.npi,
                provider_type  = record.provider_type,
                address        = record.address,
                city           = record.city,
                state          = record.state,
                zip_code       = record.zip_code,
                exclusion_date = record.exclusion_date,
                source         = 'OH - State Level',
                source_id      = record.id,
            ))
            if len(batch) >= 500:
                MainExclusion.objects.bulk_create(batch)
                oh_count += len(batch)
                batch = []
        if batch:
            MainExclusion.objects.bulk_create(batch)
            oh_count += len(batch)
        total += oh_count
        self.stdout.write(f'  Done. {oh_count} Ohio records.')

        
        # Populate from North Dakota staging table (StagingNorthDakota)
        # ND stores full name in provider_name field
        # also has address, city, zip and sanction type
        
        self.stdout.write('Populating from StagingNorthDakota...')
        batch = []
        nd_count = 0
        for record in StagingNorthDakota.objects.all():
            batch.append(MainExclusion(
                business_name  = record.provider_name or record.business_name,
                npi            = record.npi,
                provider_type  = record.provider_type,
                address        = record.address,
                city           = record.city,
                state          = record.state,
                zip_code       = record.zip_code,
                exclusion_date = record.exclusion_date,
                source         = 'ND - State Level',
                source_id      = record.id,
            ))
            if len(batch) >= 500:
                MainExclusion.objects.bulk_create(batch)
                nd_count += len(batch)
                batch = []
        if batch:
            MainExclusion.objects.bulk_create(batch)
            nd_count += len(batch)
        total += nd_count
        self.stdout.write(f'  Done. {nd_count} North Dakota records.')

        # ---------------------------------------------------------------
        # STEP 7: Populate from North Carolina staging table (StagingNorthCarolina)
        # NC stores full name in excluded_entity field
        # also has city, zip, reason for exclusion and ownership info
        # ---------------------------------------------------------------
        self.stdout.write('Populating from StagingNorthCarolina...')
        batch = []
        nc_count = 0
        for record in StagingNorthCarolina.objects.all():
            batch.append(MainExclusion(
                business_name  = record.excluded_entity,
                npi            = record.npi,
                city           = record.city,
                state          = record.state,
                zip_code       = record.zip_code,
                exclusion_date = record.exclusion_date,
                source         = 'NC - State Level',
                source_id      = record.id,
            ))
            if len(batch) >= 500:
                MainExclusion.objects.bulk_create(batch)
                nc_count += len(batch)
                batch = []
        if batch:
            MainExclusion.objects.bulk_create(batch)
            nc_count += len(batch)
        total += nc_count
        self.stdout.write(f'  Done. {nc_count} North Carolina records.')
        
        

        # ---------------------------------------------------------------
        # STEP 8: Populate from Oregon staging table (StagingOregon)
        # Oregon has separate first/last name fields and business name
        # also has provider type and duration fields
        # ---------------------------------------------------------------
        self.stdout.write('Populating from StagingOregon...')
        batch = []
        or_count = 0
        for record in StagingOregon.objects.all():
            batch.append(MainExclusion(
                first_name     = record.first_name,
                last_name      = record.last_name,
                business_name  = record.business_name,
                npi            = record.npi,
                provider_type  = record.provider_type,
                state          = record.state,
                exclusion_date = record.exclusion_date,
                source         = 'OR - State Level',
                source_id      = record.id,
            ))
            if len(batch) >= 500:
                MainExclusion.objects.bulk_create(batch)
                or_count += len(batch)
                batch = []
        if batch:
            MainExclusion.objects.bulk_create(batch)
            or_count += len(batch)
        total += or_count
        self.stdout.write(f'  Done. {or_count} Oregon records.')

        # ---------------------------------------------------------------
        # STEP 9: Populate from Pennsylvania staging table (StagingPennsylvania)
        # Pennsylvania has separate first/last/middle name fields
        # also has status (Precluded/Terminated) and end_date fields
        # ---------------------------------------------------------------
        self.stdout.write('Populating from StagingPennsylvania...')
        batch = []
        pa_count = 0
        for record in StagingPennsylvania.objects.all():
            batch.append(MainExclusion(
                first_name     = record.first_name,
                last_name      = record.last_name,
                middle_name    = record.middle_name,
                business_name  = record.business_name,
                npi            = record.npi,
                state          = record.state,
                exclusion_date = record.exclusion_date,
                source         = 'PA - State Level',
                source_id      = record.id,
            ))
            if len(batch) >= 500:
                MainExclusion.objects.bulk_create(batch)
                pa_count += len(batch)
                batch = []
        if batch:
            MainExclusion.objects.bulk_create(batch)
            pa_count += len(batch)
        total += pa_count
        self.stdout.write(f'  Done. {pa_count} Pennsylvania records.')

        # ---------------------------------------------------------------
        # STEP 10: Populate from New Jersey staging table (StagingNewJersey)
        # NJ combines all names into business_name field
        # also has action type and expiration date fields
        # ---------------------------------------------------------------
        self.stdout.write('Populating from StagingNewJersey...')
        batch = []
        nj_count = 0
        for record in StagingNewJersey.objects.all():
            batch.append(MainExclusion(
                business_name  = record.business_name,
                npi            = record.npi,
                address        = record.address,
                city           = record.city,
                state          = record.state,
                zip_code       = record.zip_code,
                exclusion_date = record.exclusion_date,
                source         = 'NJ - State Level',
                source_id      = record.id,
            ))
            if len(batch) >= 500:
                MainExclusion.objects.bulk_create(batch)
                nj_count += len(batch)
                batch = []
        if batch:
            MainExclusion.objects.bulk_create(batch)
            nj_count += len(batch)
        total += nj_count
        self.stdout.write(f'  Done. {nj_count} New Jersey records.')

        # print final summary showing records inserted from each source
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Total {total} records in main_exclusion.'
        ))