# Medicaid Provider Exclusion Search

A Django web application for searching federal and state Medicaid/Medicare 
provider exclusion records across multiple data sources. 

## Data Sources
- Federal OIG LEIE (List of Excluded Individuals/Entities)
- Georgia DCH exclusion list
- California exclusion list

## Tech Stack
- Python / Django
- PostgreSQL
- HTML/CSS

## Features
- Search across federal and state exclusion lists simultaneously
- Filter results by source (Federal/State/Both)
- Bulk import via CSV/Excel management commands

## Setup
1. Clone the repo:
   git clone https://github.com/AustinGH32/medicaid-provider-exclusion-search.git

2. Install dependencies:
   pip install -r requirements.txt

3. Create a .env file with:
   SECRET_KEY=your_secret_key
   DB_PASSWORD=your_db_password

4. Run migrations:
   python manage.py migrate

5. Start the server:
   python manage.py runserver


## What is an excluded individual/entity?
"HHS-OIG can exclude individuals and entities from Federally funded health care 
programs for a variety of reasons, including a conviction for Medicare or Medicaid fraud. 
Those that are excluded can receive no payment from Federal health care programs for any 
items or services they furnish, order, or prescribe. This includes those that provide health 
benefits funded directly or indirectly by the United States 
(other than the Federal Employees Health Benefits Plan)." 
- (https://oig.hhs.gov/exclusions/)
