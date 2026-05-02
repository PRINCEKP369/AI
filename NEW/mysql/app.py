import json
import os
from datetime import date
from functools import wraps
from pathlib import Path

import mysql.connector
import requests
from flask import (
    Flask,
    Response,
    flash,
    g,
    jsonify,
    redirect,
    render_template_string,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent

# Edit these values for your local setup.
# Environment variables with the same names still override these defaults.
DEFAULT_MODEL1_URL = "http://127.0.0.1:8080"
DEFAULT_MODEL2_URL = "http://127.0.0.1:8081"
DEFAULT_MODEL3_URL = "http://127.0.0.1:8082"
DEFAULT_APP_HOST = "0.0.0.0"
DEFAULT_APP_PORT = 5000
DEFAULT_MYSQL_HOST = "127.0.0.1"
DEFAULT_MYSQL_PORT = 3306
DEFAULT_MYSQL_USER = "root"
DEFAULT_MYSQL_PASSWORD = "your_mysql_password"
DEFAULT_MYSQL_DATABASE = "AI"
DEFAULT_SECRET_KEY = "change-me-for-local-ai"

MODEL_CONFIG = {
    "model1": os.environ.get("MODEL1_URL", DEFAULT_MODEL1_URL),
    "model2": os.environ.get("MODEL2_URL", DEFAULT_MODEL2_URL),
    "model3": os.environ.get("MODEL3_URL", DEFAULT_MODEL3_URL),
}
APP_HOST = os.environ.get("APP_HOST", DEFAULT_APP_HOST)
APP_PORT = int(os.environ.get("APP_PORT", DEFAULT_APP_PORT))
MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", DEFAULT_MYSQL_HOST),
    "port": int(os.environ.get("MYSQL_PORT", DEFAULT_MYSQL_PORT)),
    "user": os.environ.get("MYSQL_USER", DEFAULT_MYSQL_USER),
    "password": os.environ.get("MYSQL_PASSWORD", DEFAULT_MYSQL_PASSWORD),
    "database": os.environ.get("MYSQL_DATABASE", DEFAULT_MYSQL_DATABASE),
    "autocommit": False,
}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", DEFAULT_SECRET_KEY)


LOGIN_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ mode|title }} - Local AI</title>
  <style>
    :root {
      --bg: #f9f7f4;
      --surface: #ffffff;
      --border: #e3ddd7;
      --text: #1a1814;
      --muted: #6b6560;
      --accent: #c96442;
      --accent-hover: #b8572f;
      --danger: #b42318;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    main {
      width: min(420px, calc(100vw - 32px));
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      box-shadow: 0 16px 50px rgba(38, 30, 24, 0.12);
      padding: 28px;
    }
    h1 { margin: 0 0 6px; font-size: 26px; letter-spacing: 0; }
    p { margin: 0 0 24px; color: var(--muted); line-height: 1.5; }
    label { display: block; margin: 14px 0 7px; font-size: 13px; color: var(--muted); }
    input {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 11px 12px;
      font: inherit;
      color: var(--text);
      background: #fffdfb;
      outline: none;
    }
    input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(201, 100, 66, 0.12); }
    .password-field { position: relative; }
    .password-field input { padding-right: 46px; }
    .password-toggle {
      position: absolute;
      right: 8px;
      top: 50%;
      transform: translateY(-50%);
      width: 32px;
      height: 32px;
      display: grid;
      place-items: center;
      margin: 0;
      padding: 0;
      border: none;
      border-radius: 7px;
      background: transparent;
      color: var(--muted);
      cursor: pointer;
    }
    .password-toggle:hover { background: #f3eee9; color: var(--text); }
    .password-toggle svg { width: 18px; height: 18px; }
    button {
      width: 100%;
      margin-top: 20px;
      border: none;
      border-radius: 8px;
      padding: 11px 14px;
      background: var(--accent);
      color: white;
      font: inherit;
      font-weight: 600;
      cursor: pointer;
    }
    button:hover { background: var(--accent-hover); }
    .switch { margin-top: 18px; text-align: center; font-size: 14px; color: var(--muted); }
    a { color: var(--accent); text-decoration: none; font-weight: 600; }
    .flash {
      margin-bottom: 16px;
      padding: 10px 12px;
      border-radius: 8px;
      background: #fff1ef;
      color: var(--danger);
      font-size: 14px;
      border: 1px solid #ffd6d1;
    }
  </style>
</head>
<body>
  <main>
    <h1>{{ "Create account" if mode == "register" else "Welcome back" }}</h1>
    <p>{{ "Save your local AI conversations under your own account." if mode == "register" else "Log in to continue your saved local AI chats." }}</p>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for message in messages %}<div class="flash">{{ message }}</div>{% endfor %}
      {% endif %}
    {% endwith %}
    <form method="post">
      <label for="username">Username</label>
      <input id="username" name="username" autocomplete="username" required autofocus>
      <label for="password">Password</label>
      <div class="password-field">
        <input id="password" name="password" type="password" autocomplete="{{ 'new-password' if mode == 'register' else 'current-password' }}" required>
        <button class="password-toggle" type="button" onclick="togglePassword()" aria-label="Show password" title="Show password">
          <svg id="eye-open" viewBox="0 0 24 24" fill="currentColor"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zm0 12.5a5 5 0 1 1 0-10 5 5 0 0 1 0 10zm0-2a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/></svg>
          <svg id="eye-closed" viewBox="0 0 24 24" fill="currentColor" style="display:none"><path d="M2.1 3.51 3.51 2.1 21.9 20.49l-1.41 1.41-3.02-3.02A12.72 12.72 0 0 1 12 19.5C7 19.5 2.73 16.39 1 12c.8-2.03 2.15-3.76 3.83-5.02L2.1 3.51zM12 6.5a5.5 5.5 0 0 1 5.5 5.5c0 .76-.15 1.48-.43 2.14L14.9 11.97A3 3 0 0 0 12.03 9.1L9.86 6.93A5.45 5.45 0 0 1 12 6.5zm0-2c5 0 9.27 3.11 11 7.5a13.12 13.12 0 0 1-2.48 3.86l-1.42-1.42A10.75 10.75 0 0 0 20.82 12C19.17 8.63 15.82 6.5 12 6.5c-.66 0-1.31.06-1.93.19L8.49 5.11A12.7 12.7 0 0 1 12 4.5zM4.18 12C5.83 15.37 9.18 17.5 12 17.5c1.36 0 2.66-.27 3.84-.76l-2-2A3 3 0 0 1 9.26 10.16l-3-3A10.9 10.9 0 0 0 4.18 12z"/></svg>
        </button>
      </div>
      <button type="submit">{{ "Create account" if mode == "register" else "Log in" }}</button>
    </form>
    <div class="switch">
      {% if mode == "register" %}
        Already have an account? <a href="{{ url_for('login') }}">Log in</a>
      {% else %}
        New here? <a href="{{ url_for('register') }}">Create an account</a>
      {% endif %}
    </div>
  </main>
  <script>
    function togglePassword() {
      const input = document.getElementById('password');
      const button = document.querySelector('.password-toggle');
      const openIcon = document.getElementById('eye-open');
      const closedIcon = document.getElementById('eye-closed');
      const showing = input.type === 'text';
      input.type = showing ? 'password' : 'text';
      openIcon.style.display = showing ? '' : 'none';
      closedIcon.style.display = showing ? 'none' : '';
      button.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
      button.title = showing ? 'Show password' : 'Hide password';
    }
  </script>
</body>
</html>
"""


def get_db():
    if "db" not in g:
        g.db = mysql.connector.connect(**MYSQL_CONFIG)
    return g.db


def fetch_one(query, params=()):
    cursor = get_db().cursor(dictionary=True)
    cursor.execute(query, params)
    row = cursor.fetchone()
    cursor.close()
    return row


def fetch_all(query, params=()):
    cursor = get_db().cursor(dictionary=True)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    return rows


def execute(query, params=()):
    cursor = get_db().cursor()
    cursor.execute(query, params)
    return cursor


def serialize_message(message):
    return {
        "id": message["id"],
        "role": message["role"],
        "content": message["content"],
        "created_at": message["created_at"].isoformat(sep=" ") if message["created_at"] else None,
    }


def normalize_user_content(raw_content):
    if isinstance(raw_content, dict) and raw_content.get("kind") == "user_message":
        display_text = (raw_content.get("display_text") or "").strip()
        api_content = (raw_content.get("api_content") or display_text).strip()
        stored_content = json.dumps(raw_content)
        return stored_content, display_text, api_content
    text = str(raw_content or "").strip()
    return text, text, text


def estimate_tokens(text):
    if not text:
        return 0
    return max(1, (len(str(text)) + 3) // 4)


def today_key():
    return date.today().isoformat()


def get_token_usage(user_id):
    row = fetch_one(
        "SELECT tokens_used FROM daily_token_usage WHERE user_id = %s AND usage_date = %s",
        (user_id, today_key()),
    )
    used = row["tokens_used"] if row else 0
    return {"used": used}


def add_token_usage(user_id, tokens):
    if tokens <= 0:
        return
    cursor = execute(
        """
        INSERT INTO daily_token_usage (user_id, usage_date, tokens_used)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE tokens_used = tokens_used + VALUES(tokens_used)
        """,
        (user_id, today_key(), tokens),
    )
    cursor.close()


def add_token_usage_direct(user_id, tokens):
    if tokens <= 0:
        return
    db = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO daily_token_usage (user_id, usage_date, tokens_used)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE tokens_used = tokens_used + VALUES(tokens_used)
            """,
            (user_id, today_key(), tokens),
        )
        db.commit()
    finally:
        cursor.close()
        db.close()


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    cursor = db.cursor()
    statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(80) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            title VARCHAR(255) NOT NULL DEFAULT 'New conversation',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_conversations_user_updated (user_id, updated_at),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            conversation_id INT NOT NULL,
            role ENUM('user', 'assistant', 'system') NOT NULL,
            content MEDIUMTEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_messages_conversation_created (conversation_id, created_at),
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS daily_token_usage (
            user_id INT NOT NULL,
            usage_date DATE NOT NULL,
            tokens_used INT NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, usage_date),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
    ]
    for statement in statements:
        cursor.execute(statement)
    cursor.close()
    db.commit()


@app.before_request
def ensure_db():
    init_db()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def current_user():
    if "user_id" not in session:
        return None
    return fetch_one("SELECT id, username FROM users WHERE id = %s", (session["user_id"],))


def get_owned_conversation(conversation_id):
    return fetch_one(
        "SELECT * FROM conversations WHERE id = %s AND user_id = %s",
        (conversation_id, session["user_id"]),
    )


@app.route("/")
@login_required
def index():
    return send_file(BASE_DIR / "claude.html")


@app.get("/static_app.js")
@login_required
def static_app():
    return send_file(BASE_DIR / "static_app.js", mimetype="application/javascript")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = fetch_one("SELECT * FROM users WHERE username = %s", (username,))
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("index"))
        flash("Invalid username or password.")
    return render_template_string(LOGIN_TEMPLATE, mode="login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if len(username) < 3:
            flash("Username must be at least 3 characters.")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.")
        else:
            try:
                db = get_db()
                cursor = execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
                session.clear()
                cursor.close()
                flash("Account created. Please log in.")
                return redirect(url_for("login"))
            except mysql.connector.IntegrityError:
                flash("That username is already taken.")
    return render_template_string(LOGIN_TEMPLATE, mode="register")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/api/me")
@login_required
def me():
    user = current_user()
    return jsonify({"id": user["id"], "username": user["username"]})


@app.get("/api/models")
@login_required
def models():
    return jsonify(
        {
            "default": "model1",
            "models": [
                {"id": model_id, "name": model_id, "url": url}
                for model_id, url in MODEL_CONFIG.items()
            ],
        }
    )


@app.get("/api/usage")
@login_required
def usage():
    return jsonify(get_token_usage(session["user_id"]))


@app.get("/api/conversations")
@login_required
def list_conversations():
    rows = fetch_all(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        WHERE user_id = %s
        ORDER BY updated_at DESC, id DESC
        """,
        (session["user_id"],),
    )
    conversations = []
    for row in rows:
        messages = fetch_all(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE conversation_id = %s
            ORDER BY id ASC
            """,
            (row["id"],),
        )
        conversations.append(
            {
                "id": str(row["id"]),
                "title": row["title"],
                "created_at": row["created_at"].isoformat(sep=" ") if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat(sep=" ") if row["updated_at"] else None,
                "messages": [serialize_message(message) for message in messages],
            }
        )
    return jsonify({"conversations": conversations})


@app.post("/api/conversations")
@login_required
def create_conversation():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "New conversation").strip()[:80]
    db = get_db()
    cursor = execute(
        "INSERT INTO conversations (user_id, title) VALUES (%s, %s)",
        (session["user_id"], title),
    )
    db.commit()
    conversation_id = cursor.lastrowid
    cursor.close()
    return jsonify({"id": str(conversation_id), "title": title, "messages": []}), 201


@app.delete("/api/conversations/<int:conversation_id>")
@login_required
def delete_conversation(conversation_id):
    db = get_db()
    cursor = execute(
        "DELETE FROM conversations WHERE id = %s AND user_id = %s",
        (conversation_id, session["user_id"]),
    )
    db.commit()
    cursor.close()
    return ("", 204)


@app.post("/api/conversations/<int:conversation_id>/clear")
@login_required
def clear_conversation(conversation_id):
    if not get_owned_conversation(conversation_id):
        return jsonify({"error": "Conversation not found"}), 404
    db = get_db()
    cursor = execute("DELETE FROM messages WHERE conversation_id = %s", (conversation_id,))
    cursor.close()
    cursor = execute(
        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        (conversation_id,),
    )
    db.commit()
    cursor.close()
    return ("", 204)


@app.post("/api/chat/completions")
@login_required
def chat_completions():
    data = request.get_json(silent=True) or {}
    conversation_id = data.get("conversation_id")
    user_content, display_text, api_content = normalize_user_content(data.get("user_content"))
    messages = data.get("messages") or []
    model_id = data.get("model") or "model1"
    model_url = MODEL_CONFIG.get(model_id)

    if not conversation_id or not get_owned_conversation(conversation_id):
        return jsonify({"error": "Conversation not found"}), 404
    if not model_url:
        return jsonify({"error": "Unknown model"}), 400
    if not api_content:
        return jsonify({"error": "Message is empty"}), 400

    usage_snapshot = get_token_usage(session["user_id"])
    input_tokens = estimate_tokens(json.dumps(messages))

    db = get_db()
    cursor = execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (%s, 'user', %s)",
        (conversation_id, user_content),
    )
    cursor.close()
    first_message_count = fetch_one(
        "SELECT COUNT(*) AS count FROM messages WHERE conversation_id = %s",
        (conversation_id,),
    )["count"]
    if first_message_count == 1:
        title_source = display_text or api_content or "New conversation"
        title = (title_source.splitlines()[0] or "New conversation")[:40]
        if len(title_source) > 40:
            title += "..."
        cursor = execute(
            "UPDATE conversations SET title = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (title, conversation_id),
        )
    else:
        cursor = execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (conversation_id,),
        )
    db.commit()
    add_token_usage(session["user_id"], input_tokens)
    db.commit()
    cursor.close()
    user_id = session["user_id"]

    payload = {
        "model": model_id,
        "messages": messages,
        "stream": True,
    }

    def stream():
        full_reply = ""
        output_tokens = 0
        try:
            with requests.post(
                f"{model_url.rstrip('/')}/v1/chat/completions",
                json=payload,
                stream=True,
                timeout=(5, None),
            ) as upstream:
                upstream.raise_for_status()
                for line in upstream.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    yield f"{line}\n\n"
                    if not line.startswith("data:"):
                        continue
                    raw = line.removeprefix("data:").strip()
                    if raw == "[DONE]":
                        break
                    try:
                        chunk = json.loads(raw)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content") or ""
                        full_reply += content
                        output_tokens = estimate_tokens(full_reply)
                    except (json.JSONDecodeError, IndexError, AttributeError):
                        pass
        except requests.RequestException as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        finally:
            if full_reply:
                db = mysql.connector.connect(**MYSQL_CONFIG)
                try:
                    cursor = db.cursor()
                    cursor.execute(
                        "INSERT INTO messages (conversation_id, role, content) VALUES (%s, 'assistant', %s)",
                        (conversation_id, full_reply),
                    )
                    cursor.execute(
                        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                        (conversation_id,),
                    )
                    db.commit()
                finally:
                    cursor.close()
                    db.close()
                add_token_usage_direct(user_id, estimate_tokens(full_reply))

    return Response(stream(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(host=APP_HOST, port=APP_PORT, debug=True, use_reloader=False)
