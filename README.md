# FastAPI App

A basic FastAPI project with a clean folder structure.

## Project Structure

```
├── app/
│   ├── api/
│   │   ├── endpoints/   # Route handlers
│   │   │   └── items.py
│   │   └── router.py    # Central API router
│   ├── core/
│   │   └── config.py    # App settings via pydantic-settings
│   ├── models/
│   │   └── item.py      # Pydantic schemas
│   └── main.py          # FastAPI app entrypoint
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

## Getting Started

```bash
# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload
```

The API docs are available at http://127.0.0.1:8000/docs once the server is running.

## API Endpoints

| Method | Path             | Description       |
|--------|------------------|-------------------|
| GET    | /health          | Health check      |
| GET    | /api/items/      | List all items    |
| GET    | /api/items/{id}  | Get item by ID    |
| POST   | /api/items/      | Create a new item |
| DELETE | /api/items/{id}  | Delete an item    |
