# FitFact Database Setup Guide
## Week 1 - Database Foundation

### Prerequisites
- PostgreSQL 14+
- Python 3.9+
- psql command line tool

### Installation Steps

1. **Install PostgreSQL**
```bash
# macOS
brew install postgresql@14
brew services start postgresql@14

# Ubuntu/Linux
sudo apt install postgresql-14
sudo systemctl start postgresql
```

2. **Create Database and User**
```sql
psql postgres
CREATE DATABASE fitfact_db;
CREATE USER fitfact_user WITH PASSWORD 'fitfact2024';
GRANT ALL PRIVILEGES ON DATABASE fitfact_db TO fitfact_user;
\c fitfact_db
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;
\q
```

3. **Run Schema Scripts**
```bash
psql -U postgres -d fitfact_db -f database_schema.sql
psql -U postgres -d fitfact_db -f database_indexes.sql
psql -U postgres -d fitfact_db -f database_functions.sql
```

4. **Grant Permissions**
```sql
psql -d fitfact_db
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO fitfact_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fitfact_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO fitfact_user;
\q
```

### Verification
```bash
psql -U fitfact_user -d fitfact_db -h localhost
\dt  # List tables
\q
```