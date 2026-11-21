import os
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)

# The database URL comes from the environment, never from the code.
# Example: postgresql://appuser:change-me@localhost/appdb
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL is not set")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)  # adds the `flask db ...` commands


class Todo(db.Model):
    __tablename__ = "todos"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    done = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "done": self.done,
            "created_at": self.created_at.isoformat(),
        }


def error(message, status):
    return jsonify({"error": message}), status


@app.get("/api/health")
def health():
    # Never touches the database, so it answers even when PostgreSQL is down.
    return jsonify({"status": "ok"})


@app.get("/api/health/db")
def health_db():
    # Touches the database, so it tells you when PostgreSQL is the problem.
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        return error("database unreachable", 503)
    return jsonify({"status": "ok", "database": "ok"})


@app.get("/api/todos")
def list_todos():
    todos = Todo.query.order_by(Todo.id).all()
    return jsonify([t.to_dict() for t in todos])


@app.post("/api/todos")
def create_todo():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    if not title:
        return error("title is required", 400)
    if len(title) > 200:
        return error("title must be 200 characters or fewer", 400)

    todo = Todo(title=title)
    db.session.add(todo)
    db.session.commit()
    return jsonify(todo.to_dict()), 201


@app.patch("/api/todos/<int:todo_id>")
def update_todo(todo_id):
    todo = db.session.get(Todo, todo_id)
    if todo is None:
        return error("todo not found", 404)

    data = request.get_json(silent=True) or {}
    if "done" in data:
        if not isinstance(data["done"], bool):
            return error("done must be true or false", 400)
        todo.done = data["done"]
    if "title" in data:
        title = str(data["title"]).strip()
        if not title or len(title) > 200:
            return error("title must be 1 to 200 characters", 400)
        todo.title = title

    db.session.commit()
    return jsonify(todo.to_dict())


@app.delete("/api/todos/<int:todo_id>")
def delete_todo(todo_id):
    todo = db.session.get(Todo, todo_id)
    if todo is None:
        return error("todo not found", 404)
    db.session.delete(todo)
    db.session.commit()
    return "", 204


@app.errorhandler(404)
def not_found(_):
    return error("not found", 404)


@app.errorhandler(500)
def server_error(_):
    return error("internal server error", 500)
