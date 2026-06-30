# Medicaid Provider Exclusion Search

A Django web application for searching federal and state Medicaid/Medicare 
provider exclusion records across multiple data sources.

## Data Sources
- Federal OIG LEIE (List of Excluded Individuals/Entities)
- California exclusion list
- Georgia DCH exclusion list
- New York exclusion list
- North Carolina exclusion list
- North Dakota exclusion list
- Ohio exclusion list

## States/Territories Without Lists (Use Federal List)
- New Mexico
- Oklahoma
- Puerto Rico

## Tech Stack
- Python / Django
- PostgreSQL
- HTML/CSS

## Features
- Search across federal and state exclusion lists simultaneously
- Unified main exclusion table aggregating all sources
- Filter results by source
- Bulk import via CSV/Excel management commands
- Full-text search with GIN indexing

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
