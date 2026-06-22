from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField

# Model
class StagingOIG(models.Model):
    # identity fields
    last_name     = models.CharField(max_length=255, blank=True, db_index=True)
    first_name    = models.CharField(max_length=255, blank=True, db_index=True)
    middle_name   = models.CharField(max_length=255, blank=True)
    business_name = models.CharField(max_length=512, blank=True, db_index=True)

    # provider ID fields
    npi  = models.CharField(max_length=20, blank=True, db_index=True)
    upin = models.CharField(max_length=20, blank=True)
    dob  = models.DateField(null=True, blank=True)

    # classification fields
    general   = models.CharField(max_length=255, blank=True)
    specialty = models.CharField(max_length=255, blank=True)

    # address fields
    address  = models.CharField(max_length=512, blank=True)
    city     = models.CharField(max_length=255, blank=True, db_index=True)
    state    = models.CharField(max_length=2,   blank=True, db_index=True)
    zip_code = models.CharField(max_length=10,  blank=True)

    # exclusion detail fields
    exclusion_type     = models.CharField(max_length=20, blank=True, db_index=True)
    exclusion_date     = models.DateField(null=True, blank=True, db_index=True)
    reinstatement_date = models.DateField(null=True, blank=True)
    waiver_date        = models.DateField(null=True, blank=True)
    waiver_state       = models.CharField(max_length=2, blank=True)

    #search vector field and timestamp fields
    search_vector = SearchVectorField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    # Meta class controls how Django interacts with the model
    class Meta:
        # Specifies name of the database table to use for this model
        db_table = 'oig_exclusion'
        # Default ordering for query results (by last name, then first name, then business name)
        ordering = ['last_name', 'first_name', 'business_name']
        # extra database indexes to optimize search queries
        indexes = [
            # Generalized Inverted Index. Designed for full-text search.
            # Breaks up the lookup value into tokens and creates an index on those tokens, 
            # allowing for fast search queries.
            GinIndex(fields=['search_vector'], name='exclusion_search_gin'),
            # creating indexes on commonly searched fields to speed up queries that filter by these fields
            models.Index(fields=['state', 'exclusion_date'], name='exclusion_state_date_idx'),
            models.Index(fields=['exclusion_type'],          name='exclusion_type_idx'),
            models.Index(fields=['npi'],                     name='exclusion_npi_idx'),

        ]

    # How the code below works:
    # @property lets us access methods like it's a field, so we don't need parentheses when we call it.
    # self in __str__ refers to the current record.

    # controls how a record displays as text, such as in the Django admin interface or when printed
    def __str__(self):
        if self.last_name:
            return f'{self.last_name}, {self.first_name} ({self.exclusion_type})'
        return f'{self.business_name} ({self.exclusion_type})'
        
    # combines first, middle, and last name into a string. 
    # Business name will show if it's a business
    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(p for p in parts if p).strip() or self.business_name
        
    # True if person, false if business
    @property
    def is_individual(self):
        return bool(self.last_name)
        
    # True if reinstated, False if still excluded
    @property
    def is_reinstated(self):
        return self.reinstatement_date is not None
class StagingGeorgia(models.Model):
    last_name     = models.CharField(max_length=255, blank=True, db_index=True)
    first_name    = models.CharField(max_length=255, blank=True, db_index=True)
    middle_name   = models.CharField(max_length=255, blank=True)
    business_name = models.CharField(max_length=512, blank=True, db_index=True)
    npi           = models.CharField(max_length=20, blank=True, db_index=True)
    general       = models.CharField(max_length=255, blank=True)
    state         = models.CharField(max_length=2, blank=True, db_index=True)
    exclusion_date = models.DateField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'georgia_exclusion'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        if self.last_name:
            return f'{self.last_name}, {self.first_name}'
        return self.business_name

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(p for p in parts if p).strip() or self.business_name

class StagingCalifornia(models.Model):
    last_name     = models.CharField(max_length=255, blank=True, db_index=True)
    first_name    = models.CharField(max_length=255, blank=True, db_index=True)
    middle_name   = models.CharField(max_length=255, blank=True)
    business_name = models.CharField(max_length=512, blank=True, db_index=True)
    npi           = models.CharField(max_length=20, blank=True, db_index=True)
    provider_type = models.CharField(max_length=255, blank=True)
    license_number = models.CharField(max_length=255, blank=True)
    address       = models.CharField(max_length=512, blank=True)
    state         = models.CharField(max_length=2, blank=True, db_index=True)
    exclusion_date = models.DateField(null=True, blank=True)
    active_period  = models.CharField(max_length=255, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'california_exclusion'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        if self.last_name:
            return f'{self.last_name}, {self.first_name}'
        return self.business_name

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(p for p in parts if p).strip() or self.business_name

class StagingNewYork(models.Model):
    business_name  = models.CharField(max_length=512, blank=True, db_index=True)
    npi            = models.CharField(max_length=20, blank=True, db_index=True)
    license_number = models.CharField(max_length=255, blank=True)
    provider_type  = models.CharField(max_length=255, blank=True)
    state          = models.CharField(max_length=2, blank=True, db_index=True)
    exclusion_date = models.DateField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staging_new_york'
        ordering = ['business_name']

    def __str__(self):
        return self.business_name

    @property
    def full_name(self):
        return self.business_name
    
class StagingOhio(models.Model):
    # individual fields
    last_name     = models.CharField(max_length=255, blank=True, db_index=True)
    first_name    = models.CharField(max_length=255, blank=True, db_index=True)
    middle_name   = models.CharField(max_length=255, blank=True)
    dob           = models.DateField(null=True, blank=True)

    # organization fields
    business_name = models.CharField(max_length=512, blank=True, db_index=True)
    address       = models.CharField(max_length=512, blank=True)
    city          = models.CharField(max_length=255, blank=True)
    zip_code      = models.CharField(max_length=10, blank=True)

    # shared fields
    npi           = models.CharField(max_length=20, blank=True, db_index=True)
    provider_type = models.CharField(max_length=255, blank=True)
    status        = models.CharField(max_length=50, blank=True)
    state         = models.CharField(max_length=2, blank=True, db_index=True)
    exclusion_date = models.DateField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staging_ohio'
        ordering = ['last_name', 'first_name', 'business_name']

    def __str__(self):
        if self.last_name:
            return f'{self.last_name}, {self.first_name}'
        return self.business_name

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(p for p in parts if p).strip() or self.business_name

class StagingNorthDakota(models.Model):
    provider_name  = models.CharField(max_length=512, blank=True, db_index=True)
    business_name  = models.CharField(max_length=512, blank=True, db_index=True)
    npi            = models.CharField(max_length=20, blank=True, db_index=True)
    license_number = models.CharField(max_length=255, blank=True)
    provider_type  = models.CharField(max_length=255, blank=True)
    sanction_type  = models.CharField(max_length=255, blank=True)
    address        = models.CharField(max_length=512, blank=True)
    city           = models.CharField(max_length=255, blank=True)
    state          = models.CharField(max_length=2, blank=True, db_index=True)
    zip_code       = models.CharField(max_length=10, blank=True)
    exclusion_date = models.DateField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staging_north_dakota'
        ordering = ['provider_name']

    def __str__(self):
        return self.provider_name or self.business_name

    @property
    def full_name(self):
        return self.provider_name or self.business_name


class StagingNorthCarolina(models.Model):
    excluded_entity = models.CharField(max_length=512, blank=True, db_index=True)
    npi             = models.CharField(max_length=20, blank=True, db_index=True)
    exclusion_date  = models.DateField(null=True, blank=True)
    reason          = models.CharField(max_length=255, blank=True)
    city            = models.CharField(max_length=255, blank=True)
    state           = models.CharField(max_length=2, blank=True, db_index=True)
    zip_code        = models.CharField(max_length=10, blank=True)
    ownership       = models.CharField(max_length=512, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staging_north_carolina'
        ordering = ['excluded_entity']

    def __str__(self):
        return self.excluded_entity

    @property
    def full_name(self):
        return self.excluded_entity

class MainExclusion(models.Model):
    # identity fields
    first_name    = models.CharField(max_length=255, blank=True, db_index=True)
    last_name     = models.CharField(max_length=255, blank=True, db_index=True)
    middle_name   = models.CharField(max_length=255, blank=True)
    business_name = models.CharField(max_length=512, blank=True, db_index=True)

    # provider identifiers
    npi = models.CharField(max_length=20, blank=True, db_index=True)

    # classification
    general       = models.CharField(max_length=255, blank=True)
    specialty     = models.CharField(max_length=255, blank=True)
    provider_type = models.CharField(max_length=255, blank=True)

    # location
    address  = models.CharField(max_length=512, blank=True)
    city     = models.CharField(max_length=255, blank=True)
    state    = models.CharField(max_length=2, blank=True, db_index=True)
    zip_code = models.CharField(max_length=10, blank=True)

    # exclusion details
    exclusion_type     = models.CharField(max_length=20, blank=True)
    exclusion_date     = models.DateField(null=True, blank=True, db_index=True)
    reinstatement_date = models.DateField(null=True, blank=True)

    # source tracking
    source    = models.CharField(max_length=50, blank=True, db_index=True)
    source_id = models.BigIntegerField(null=True, blank=True)

    # timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'main_exclusion'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['state', 'exclusion_date'], name='main_state_date_idx'),
            models.Index(fields=['source'],                  name='main_source_idx'),
            models.Index(fields=['npi'],                     name='main_npi_idx'),
        ]

    def __str__(self):
        if self.last_name:
            return f'{self.last_name}, {self.first_name} ({self.source})'
        return f'{self.business_name} ({self.source})'

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(p for p in parts if p).strip() or self.business_name

    @property
    def is_reinstated(self):
        return self.reinstatement_date is not None