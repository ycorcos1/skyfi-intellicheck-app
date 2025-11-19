# Migrations

Alembic migration scripts will live in this directory once the database schema is defined (see PR #6).

## Workflow

1. Initialize Alembic (first time only):
   ```bash
   alembic init app/db/migrations
   ```
2. Create a new migration:
   ```bash
   alembic revision --autogenerate -m "create companies table"
   ```
3. Apply migrations:
   ```bash
   alembic upgrade head
   ```



