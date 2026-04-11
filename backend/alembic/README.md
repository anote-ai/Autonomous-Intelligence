# Alembic Database Migrations

This directory contains the Alembic migration environment for the Anote AI backend.

## Prerequisites

Install dependencies:

```bash
pip install -r requirements.txt
```

Set up your environment variables (copy `backend/.env.example` to `backend/.env` and fill in values):

```
DB_USER=root
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=anote
```

## Running Migrations

All commands should be run from the `backend/` directory.

### Apply all pending migrations (upgrade to latest)

```bash
alembic upgrade head
```

### Apply a specific number of migrations

```bash
alembic upgrade +1
```

### Revert the most recent migration

```bash
alembic downgrade -1
```

### Revert all migrations

```bash
alembic downgrade base
```

### Check current migration state

```bash
alembic current
```

### View migration history

```bash
alembic history --verbose
```

## Creating New Migrations

### Auto-generate a migration from model changes

```bash
alembic revision --autogenerate -m "describe your change"
```

> Note: Auto-generation requires SQLAlchemy models to be imported in `env.py` via `target_metadata`. The current setup uses raw SQL migrations; set `target_metadata` in `env.py` to enable autogenerate.

### Create a blank migration file

```bash
alembic revision -m "describe your change"
```

Edit the generated file in `alembic/versions/` and implement the `upgrade()` and `downgrade()` functions.

## Migration File Naming

Migration files are stored in `alembic/versions/`. Each file has:
- A unique revision ID
- A `down_revision` pointer to the previous migration (forms a chain)
- `upgrade()` — SQL to apply the change
- `downgrade()` — SQL to revert the change

## Initial Migration

The file `versions/0001_initial_schema.py` captures the full schema from `backend/database/schema.sql` and is the baseline for all future migrations.
