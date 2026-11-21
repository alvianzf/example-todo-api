# todo-api

A small to-do list API for the deployment course: **Flask + PostgreSQL**, with schema changes managed by **Flask-Migrate** (Alembic).

| Method | Route | What it does |
|---|---|---|
| GET | `/api/health` | `{"status":"ok"}`. Never touches the database |
| GET | `/api/health/db` | Runs `SELECT 1`. Returns 503 if PostgreSQL is down |
| GET | `/api/todos` | List all todos |
| POST | `/api/todos` | Create one: `{"title": "Buy milk"}` |
| PATCH | `/api/todos/<id>` | Update `done` and/or `title` |
| DELETE | `/api/todos/<id>` | Delete one |

The entry point is `app:app`. The database URL comes from the `DATABASE_URL` environment variable and the app refuses to start without it.

## Run it locally

You need Python 3 and a PostgreSQL database (any local one will do).

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL="postgresql://appuser:change-me@localhost/appdb"
flask db upgrade                 # create the tables
flask run --port 8000            # or: gunicorn --bind 127.0.0.1:8000 app:app
```

Try it:

```bash
curl -s -X POST localhost:8000/api/todos -H 'content-type: application/json' -d '{"title":"Learn nginx"}'
curl -s localhost:8000/api/todos
```

## Migrations

The table is not created by the app. It is created by the migration in `migrations/versions/0001_create_todos_table.py`. The migration history lives in git next to the code, and every environment (your laptop, the server) runs the same files.

```bash
flask db upgrade        # apply every migration that has not run yet
flask db current        # which revision is this database at?
flask db history        # list all revisions
flask db downgrade      # undo the latest one
```

PostgreSQL remembers the current revision in a table called `alembic_version`.

### Exercise: add a column

1. Add a column to the `Todo` model in `app.py`, for example `due_date = db.Column(db.Date)` (nullable, so existing rows stay valid).
2. Generate the migration and **read it** before you trust it:
   ```bash
   flask db migrate -m "add due date" --rev-id 0002
   ```
3. Apply it with `flask db upgrade`, then check with `psql -h localhost -U appuser appdb -c '\d todos'`.
4. Commit the new file in `migrations/versions/`.

## Tests

```bash
pip install pytest
python -m pytest
```

The tests set `DATABASE_URL` to an in-memory SQLite database, so they run anywhere with no PostgreSQL. That is what makes them suitable as a CI gate.

## Deploy notes (the course server)

Install it as in session 2 (`/srv/flask-app`, supervisor, nginx `/api/` block), then create the tables once:

```bash
cd /srv/flask-app
export DATABASE_URL="postgresql://appuser:change-me@localhost/appdb"
venv/bin/flask db upgrade
```

The supervisor `environment=` line gives gunicorn its `DATABASE_URL`, but your shell has its own environment, so you export it yourself to run `flask db` commands.

When a push adds a migration, the deploy has to apply it. Add one line to `~/deploy-flask.sh`, **before** the restart, and put the URL in a file only you can read so it is not in git or in the script:

```bash
echo 'export DATABASE_URL="postgresql://appuser:change-me@localhost/appdb"' > ~/.flask-env
chmod 600 ~/.flask-env
```

```bash
#!/bin/bash
set -euo pipefail
cd /srv/flask-app
git pull --ff-only
venv/bin/pip install -r requirements.txt
source ~/.flask-env
venv/bin/flask db upgrade
sudo supervisorctl restart flask
```

Because of `set -e`, a failing migration stops the deploy before the restart, so the old code keeps serving.
