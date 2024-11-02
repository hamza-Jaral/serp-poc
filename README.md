# FastAPI Project

A modern FastAPI project with SQLite database integration.

## Features

- FastAPI framework
- SQLite database
- SQLAlchemy ORM
- Swagger UI documentation
- Environment configuration

## Prerequisites

- Python 3.10 or higher
- pip (Python package installer)

## Setup Guide

### 1. Clone the repository
```bash
git clone <repository-url>
cd fastapi-project
```

### 2. Set up Python Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the root directory:
```
DATABASE_URL=sqlite:///./sql_app.db
```

### 5. Running the Application

**Development Server:**
```bash
uvicorn app.main:app --reload
```

The API will be available at:
- API Documentation (Swagger UI): http://localhost:8000/
- Health Check: http://localhost:8000/health

## Project Structure
```
fastapi-project/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── config.py
│   │
│   ├── api/
│   ├── core/
│   ├── models/
│   └── schemas/
│
├── requirements.txt
├── README.md
└── .env
```
```