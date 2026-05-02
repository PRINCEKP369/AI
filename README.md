# Local AI Chat with MySQL

This folder is the MySQL version of the Flask app. It uses your existing MySQL database named `AI` and creates these tables automatically:

- `users`
- `conversations`
- `messages`

## 1. Make sure the database exists

Log in to MySQL and create the database if it does not already exist:

```sql
CREATE DATABASE IF NOT EXISTS AI CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 2. Install dependencies in the existing venv

From `/Users/princekp/AI`:

```bash
.venv/bin/python -m pip install -r local_ai_mysql/requirements.txt
```

## 3. Add your MySQL login

Open `app.py` and edit this block near the top:

```python
DEFAULT_MYSQL_HOST = "127.0.0.1"
DEFAULT_MYSQL_PORT = 3306
DEFAULT_MYSQL_USER = "root"
DEFAULT_MYSQL_PASSWORD = "your_mysql_password"
DEFAULT_MYSQL_DATABASE = "AI"
```

Then run:

```bash
cd /Users/princekp/AI/local_ai_mysql
../.venv/bin/python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## 4. Keep llama.cpp running

The app expects llama.cpp's OpenAI-compatible server at:

```text
http://127.0.0.1:8080
```

If your llama.cpp server uses another port, edit this value in `app.py`:

```python
DEFAULT_MODEL1_URL = "http://127.0.0.1:8080"
DEFAULT_MODEL2_URL = "http://127.0.0.1:8081"
DEFAULT_MODEL3_URL = "http://127.0.0.1:8082"
DEFAULT_APP_HOST = "0.0.0.0"
DEFAULT_APP_PORT = 5000
DEFAULT_TOKEN_DAILY_LIMIT = 500000
```
