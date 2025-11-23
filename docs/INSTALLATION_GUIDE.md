\# FitFact Chatbot - Installation Guide



\## Complete Setup Instructions for Development Environment



---



\## Prerequisites



\- Windows 10/11, macOS, or Linux

\- Internet connection

\- 4GB+ RAM

\- 2GB free disk space



---



\## Part 1: Python Installation



\### Windows



1\. Go to https://www.python.org/downloads/

2\. Download Python 3.14.0 (or latest 3.x version)

3\. Run installer

4\. \*\*IMPORTANT:\*\* Check "Add python.exe to PATH"

5\. Click "Install Now"

6\. Verify installation:

```bash

python --version

\# Should show: Python 3.14.0

```



\### macOS

```bash

brew install python@3.14

python3 --version

```



\### Linux

```bash

sudo apt update

sudo apt install python3.14 python3-pip

python3 --version

```



---



\## Part 2: PostgreSQL Installation



\### Windows



1\. Download from: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads

2\. Select \*\*PostgreSQL 14.x for Windows\*\*

3\. Run installer

4\. Set password: `fitfact2024` (or your preferred password)

5\. Port: `5432` (default)

6\. Install all components

7\. Add to PATH: `C:\\Program Files\\PostgreSQL\\14\\bin`

8\. Verify:

```bash

psql --version

\# Should show: psql (PostgreSQL) 14.x

```



\### macOS

```bash

brew install postgresql@14

brew services start postgresql@14

psql --version

```



\### Linux

```bash

sudo apt install postgresql-14

sudo systemctl start postgresql

psql --version

```



---



\## Part 3: Project Setup



\### Clone Repository

```bash

cd Desktop

git clone https://github.com/rahulg2469/FitFact-Chatbot.git

cd FitFact-Chatbot

```



\### Create Virtual Environment

```bash

\# Create venv

python -m venv venv



\# Activate (Windows)

venv\\Scripts\\activate



\# Activate (macOS/Linux)

source venv/bin/activate



\# You should see (venv) in your prompt

```



\### Install Dependencies

```bash

pip install -r requirements.txt

```



---



\## Part 4: API Keys Setup



\### Get PubMed API Key



1\. Go to https://www.ncbi.nlm.nih.gov/account/

2\. Create account (free)

3\. Navigate to Settings → API Key Management

4\. Click "Create an API Key"

5\. Copy your key



\### Get Claude API Key



1\. Go to https://console.anthropic.com/

2\. Sign up for account

3\. Go to API Keys section

4\. Click "Create Key"

5\. Copy your key (you can't see it again!)



\### Create .env File



Create `.env` in project root:

```bash

\# PubMed API

PUBMED\_API\_KEY=your\_pubmed\_key\_here

PUBMED\_EMAIL=your\_email@example.com



\# Claude API

CLAUDE\_API\_KEY=your\_claude\_key\_here



\# Database

DB\_NAME=fitfact\_db

DB\_USER=fitfact\_user

DB\_PASSWORD=fitfact2024

DB\_HOST=localhost

DB\_PORT=5432

```



\*\*IMPORTANT:\*\* Never commit `.env` to Git! It's already in `.gitignore`.



---



\## Part 5: Database Setup



\### Create Database and User

```bash

\# Connect to PostgreSQL

psql -U postgres



\# In psql, run:

CREATE DATABASE fitfact\_db;

CREATE USER fitfact\_user WITH PASSWORD 'fitfact2024';

GRANT ALL PRIVILEGES ON DATABASE fitfact\_db TO fitfact\_user;

\\c fitfact\_db

\\q

```



\### Run Schema Scripts

```bash

psql -U postgres -d fitfact\_db -f database\_files/database\_schema.sql

psql -U postgres -d fitfact\_db -f database\_files/database\_indexes.sql

psql -U postgres -d fitfact\_db -f database\_files/database\_functions.sql

```



\### Grant Permissions

```bash

psql -d fitfact\_db



\# In psql:

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO fitfact\_user;

GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fitfact\_user;

\\q

```



\### Verify Database

```bash

psql -U fitfact\_user -d fitfact\_db -h localhost



\# In psql:

\\dt  # Should show 10 tables

SELECT COUNT(\*) FROM research\_papers;  # Check if tables work

\\q

```



---



\## Part 6: Testing Installation



\### Test Database Connection

```bash

python database\_files/test\_database.py

```



Expected output: `✓ Database connected successfully`



\### Test PubMed API

```bash

python src/etl/pubmed\_test.py

```



Expected output: Successfully fetches 3 papers about resistance training



\### Test Claude API

```bash

python src/llm/claude\_test.py

```



Expected output: Generates response about creatine



\### Test Complete Pipeline

```bash

python src/llm/query\_processor.py

```



Expected output: Full question → answer with citations



---



\## Part 7: Load Sample Data

```bash

python src/etl/insert\_papers.py

```



This inserts 10 sample research papers into your database.



---



\## Troubleshooting



\### Python not found



\- Windows: Make sure "Add to PATH" was checked during install

\- Restart Command Prompt after installation

\- Check: `where python` (should show path)



\### PostgreSQL connection failed



\- Check PostgreSQL service is running

\- Verify password is correct

\- Check port 5432 is not blocked by firewall



\### PubMed API errors



\- Verify API key in `.env` file

\- Check email is correct

\- Try again later if "502 Bad Gateway" (maintenance)



\### Import errors



\- Make sure virtual environment is activated (see `(venv)` in prompt)

\- Run `pip install -r requirements.txt` again

\- Check you're in project directory



\### Database permission errors

```bash

psql -d fitfact\_db

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO fitfact\_user;

GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fitfact\_user;

\\q

```



---



\## Quick Start Summary

```bash

\# 1. Clone repo

git clone https://github.com/rahulg2469/FitFact-Chatbot.git

cd FitFact-Chatbot



\# 2. Create venv and install

python -m venv venv

venv\\Scripts\\activate  # Windows

pip install -r requirements.txt



\# 3. Setup .env file with your API keys



\# 4. Create database

psql -U postgres

\# Run CREATE DATABASE and CREATE USER commands



\# 5. Run schema

psql -U postgres -d fitfact\_db -f database\_files/database\_schema.sql

psql -U postgres -d fitfact\_db -f database\_files/database\_indexes.sql



\# 6. Load sample data

python src/etl/insert\_papers.py



\# 7. Test the system

python src/llm/query\_processor.py

```



---



\## System Requirements



\- Python 3.9+

\- PostgreSQL 14+

\- 4GB RAM minimum

\- Internet connection for API calls



---



\## Support



For issues, contact team members or check GitHub Issues:

https://github.com/rahulg2469/FitFact-Chatbot/issues



---



\*\*Installation complete! You're ready to use the FitFact Chatbot!\*\* 

