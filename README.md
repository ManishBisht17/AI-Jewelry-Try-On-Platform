# JewelryTryOn

JewelryTryOn is an MVP for previewing jewelry on pre-made AI model photos. The
standalone generation script is available first; the FastAPI backend and web
interface will be added in the next steps.

## Step 1: Run the standalone image generation

1. Create and activate a Python 3.11+ virtual environment:

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure the OpenAI API key:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set `OPENAI_API_KEY` to your key. The key is loaded from the
   environment and is never stored in source code.

4. Run the standalone test with a model photo followed by a jewelry photo:

   ```bash
   python test_generate.py path/to/model.png path/to/jewelry.png
   ```

   The script calls `gpt-image-1` with `quality="low"` and saves the result as
   `output.png` in the project root.

## Running the web app

The FastAPI application and frontend will be implemented in the next steps.
Once they are present, start the app with:

```bash
uvicorn app.main:app --reload
```

## Project structure

```text
.
├── app/
│   └── __init__.py
├── storage/
│   ├── models/
│   ├── results/
│   └── uploads/
├── .env.example
├── models.json
├── requirements.txt
└── test_generate.py
```

## Planned scope

The MVP will include upload validation, background removal, model selection,
background generation jobs, fallback compositing, SQLite persistence, and a
simple Tailwind CDN frontend. It intentionally does not include authentication,
payments, user accounts, Redis/Celery, cloud storage, or an LLM quality checker.
