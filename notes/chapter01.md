# Darak — Phase 1: Foundation

> **Mentor note:** Before touching any code, understand the most important Flask pattern you'll use for the entire project.

---

## The Concept: App Factory Pattern

A beginner writes Flask like this:

```python
# bad — beginner style
app = Flask(__name__)
app.run()
```

The problem? That `app` is created **once, globally, forever**. You can't create a test version. You can't have different configs. It's rigid.

A senior engineer uses the **App Factory**:

```python
# good — professional style
def create_app(config):
    app = Flask(__name__)
    # configure it
    # register blueprints
    return app
```

Now you can call `create_app("development")` or `create_app("testing")` and get different versions of the same app. This is how every production Flask project works.

---

## What We're Building in Phase 1

```
Phase 1 checklist:
  ├── Create the folder structure
  ├── Write config.py        ← manage environments cleanly
  ├── Write extensions.py    ← initialize DB and JWT once
  ├── Write app/__init__.py  ← the app factory
  ├── Write run.py           ← entry point
  └── Write .env             ← secrets
```

---

## Step 1 of 6 — Project Setup & Folder Creation

### Goal

Create the physical project structure on your machine.

### Why this matters

A clear folder structure means:

- You always know where to put new code
- New team members understand the project immediately
- Your IDE gives you better autocomplete and navigation

### Do this now

Open your terminal and run these commands:

```bash
# Create the project root
mkdir darak
cd darak

# Create the app package and all blueprints
mkdir -p app/auth app/listings app/brokers app/leads app/uploads
mkdir -p app/templates/auth app/templates/listings app/templates/brokers
mkdir -p static/css static/js static/images
mkdir tests

# Create all the empty Python files
touch app/__init__.py
touch app/config.py
touch app/extensions.py

touch app/auth/__init__.py app/auth/routes.py app/auth/schemas.py app/auth/utils.py
touch app/listings/__init__.py app/listings/routes.py app/listings/models.py app/listings/schemas.py
touch app/brokers/__init__.py app/brokers/routes.py app/brokers/models.py app/brokers/schemas.py
touch app/leads/__init__.py app/leads/routes.py app/leads/models.py app/leads/schemas.py
touch app/uploads/__init__.py app/uploads/routes.py

touch app/templates/base.html

touch run.py
touch .env
touch .env.example
touch requirements.txt
touch README.md
touch tests/__init__.py
```

Then verify your structure looks correct:

```bash
find . -not -path './.git/*' | sort
```

---

## Step 2 of 6 — Install Dependencies

### Why we pick these specific packages

| Package              | Why                                                |
| -------------------- | -------------------------------------------------- |
| `flask`              | The framework                                      |
| `flask-jwt-extended` | JWT auth tokens — login system                     |
| `mongoengine`        | MongoDB ORM — cleaner than raw PyMongo             |
| `marshmallow`        | Input validation — never trust user data           |
| `cloudinary`         | Image uploads                                      |
| `python-dotenv`      | Load `.env` secrets into your app                  |
| `bcrypt`             | Password hashing — **never store plain passwords** |

### Do this now

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate       # Mac/Linux
# venv\Scripts\activate        # Windows

# Install packages
pip install flask flask-jwt-extended mongoengine marshmallow cloudinary python-dotenv bcrypt

# Save exact versions
pip freeze > requirements.txt
```

---

## Step 3 of 6 — The `.env` File

### Goal

Store all secrets and environment-specific values outside your code.

### Why this matters

If you hardcode your MongoDB password in `config.py` and push to GitHub, your database is compromised. This is one of the most common real-world security mistakes. The `.env` file is **never committed to Git**.

### `.env` (your actual secrets — never commit)

```bash
FLASK_ENV=development
SECRET_KEY=your-super-secret-key-change-this
JWT_SECRET_KEY=another-secret-key-change-this

MONGODB_URI=mongodb://localhost:27017/darak_dev

CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

### `.env.example` (template — always commit this)

```bash
FLASK_ENV=development
SECRET_KEY=change-me
JWT_SECRET_KEY=change-me

MONGODB_URI=mongodb://localhost:27017/darak_dev

CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
```

### `.gitignore` — create this now

```bash
touch .gitignore
```

```
# .gitignore
venv/
__pycache__/
*.pyc
.env
*.egg-info/
.DS_Store
```

---

## Step 4 of 6 — `config.py`

### Goal

One place to manage all configuration for all environments.

### Why this matters

- **Development:** debug on, verbose errors, local database
- **Production:** debug off, real database, strict security
- **Testing:** isolated database, no real side effects

```python
# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()  # reads your .env file into environment variables

class Config:
    """Base configuration — shared across all environments."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-secret-key")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "fallback-jwt-key")
    MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/darak_dev")

    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 hours in seconds


class DevelopmentConfig(Config):
    """Development — debug on, local database."""
    DEBUG = True


class ProductionConfig(Config):
    """Production — debug off, strict settings."""
    DEBUG = False


class TestingConfig(Config):
    """Testing — separate database, no real side effects."""
    TESTING = True
    MONGODB_URI = "mongodb://localhost:27017/darak_test"


# This dictionary lets us select config by name string
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
```

---

## Step 5 of 6 — `extensions.py`

### Goal

Initialize Flask extensions **once**, import them anywhere.

### Why this matters

Flask extensions like MongoEngine and JWTManager need a Flask `app` object to initialize. But your models need MongoEngine _before_ the app exists.

The solution: initialize extensions **without** the app first, then bind them to the app inside the factory. This is called the **deferred initialization pattern**.

```python
# app/extensions.py
from flask_jwt_extended import JWTManager
from mongoengine import connect
import cloudinary

# JWT manager — initialized without app yet
jwt = JWTManager()


def init_extensions(app):
    """
    Bind all extensions to the Flask app.
    Called once inside create_app().
    """
    # JWT
    jwt.init_app(app)

    # MongoDB — connect using URI from config
    connect(host=app.config["MONGODB_URI"])

    # Cloudinary
    cloudinary.config(
        cloud_name=app.config["CLOUDINARY_CLOUD_NAME"],
        api_key=app.config["CLOUDINARY_API_KEY"],
        api_secret=app.config["CLOUDINARY_API_SECRET"],
    )
```

---

## Step 6 of 6 — App Factory & Entry Point

### `app/__init__.py` — the factory

```python
# app/__init__.py
from flask import Flask
from .config import config_map
from .extensions import init_extensions


def create_app(config_name="development"):
    """
    App factory — creates and configures the Flask application.

    Args:
        config_name: "development", "production", or "testing"

    Returns:
        Configured Flask app instance
    """
    app = Flask(__name__)

    # Load config class
    app.config.from_object(config_map[config_name])

    # Initialize extensions (DB, JWT, Cloudinary)
    init_extensions(app)

    # Register blueprints — we'll add these as we build each feature
    # from .auth import auth_bp
    # app.register_blueprint(auth_bp, url_prefix="/auth")

    @app.route("/health")
    def health_check():
        """Simple route to verify the app is running."""
        return {"status": "ok", "project": "Darak"}

    return app
```

### `run.py` — the entry point

```python
# run.py
import os
from app import create_app

config_name = os.environ.get("FLASK_ENV", "development")
app = create_app(config_name)

if __name__ == "__main__":
    app.run()
```

---

## Test That Everything Works

```bash
# Make sure venv is active, then:
python run.py
```

Open your browser at:

```
http://localhost:5000/health
```

You should see:

```json
{ "project": "Darak", "status": "ok" }
```

If you see that — **Phase 1 is complete.**

---

## What You Just Built

| File              | What it does                                 |
| ----------------- | -------------------------------------------- |
| `config.py`       | Manages dev/prod/test environments cleanly   |
| `extensions.py`   | Initializes DB, JWT, Cloudinary in one place |
| `app/__init__.py` | App factory — professional Flask pattern     |
| `run.py`          | Clean entry point                            |
| `.env`            | Secrets stay out of your code                |

---

## Common Mistakes at This Stage

- **Committing `.env` to Git** — add it to `.gitignore` immediately
- **Hardcoding secrets in `config.py`** — always use `os.environ.get()`
- **Not using a virtual environment** — always activate `venv` before running
- **Skipping the health check route** — always have a way to verify your app boots

---

> ⏸️ **Waiting for you.**
> Run the steps, start the server, and hit `/health`.
> Paste any errors here and we'll debug together.
> Say **"continue"** or **"done"** when Phase 1 is working on your machine.
