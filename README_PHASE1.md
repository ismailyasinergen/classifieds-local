# Classifieds Local — Phase 1

This is the Phase 1 repo root for the local-only Django classifieds project.

## Setup

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create the PostgreSQL database:

```bash
createdb classifieds_db
```

Or:

```bash
psql -U postgres -c "CREATE DATABASE classifieds_db;"
```

Run Django commands from `backend/`:

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```
