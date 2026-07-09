# NEPSE AI-Driven Analysis Web App

AI-driven information analysis of the NEPSE (Nepal Stock Exchange) equity market: weak-form
market efficiency tests, GARCH(1,1) volatility modeling, XGBoost/LSTM next-day return
prediction with SHAP explainability, and an LLM chat layer (local Ollama) that explains the
results in plain English.

**Stack:** FastAPI + MongoDB backend, a pure-Python ML/stats engine (`backend/app/ml/`), and a
Vite + React frontend.

## Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB running locally (default expected at `mongodb://localhost:27017`)
- [Ollama](https://ollama.com) installed locally, with the model pulled:
  ```
  ollama pull llama3.2
  ```

## Setup

### Backend

```
cd backend
pip install -r requirements.txt
cp .env.example .env
# edit .env: set JWT_SECRET to a real random value, adjust MONGO_URI if needed
```

### Frontend

```
cd frontend
npm install
```

## Raw data

Raw NEPSE data is one CSV per trading day (filename format `YYYY-MM-DD.csv`), and is **not**
committed to this repo (see `.gitignore` — CSVs, parquet, and model artifacts are excluded to
keep the repo small).

1. Place the daily CSV files in `backend/data/raw/`.
2. Download the dataset from: **[TODO: add the GitHub Release asset link or Drive link for the
   zipped CSVs here]** — see this repo's [Releases page](https://github.com/AbhishekPandey233/nepse-ai-app/releases)
   once an asset has been uploaded there.
3. Build the combined dataset (run once, or whenever new daily CSVs are added):
   ```
   cd backend
   python -m app.ml.ingest
   ```
   This reads every CSV in `backend/data/raw/` and writes
   `backend/data/processed/nepse_history.parquet`, which everything else (data loader, ML
   models, API) reads from.

## Running the demo

Start things in this order — each one depends on the previous being up:

1. **MongoDB** — must be running and reachable at the `MONGO_URI` in `backend/.env`.
2. **Ollama** — start the server (if not already running as a background service):
   ```
   ollama serve
   ```
3. **Backend**:
   ```
   cd backend
   uvicorn app.main:app --reload
   ```
   Runs at `http://localhost:8000`. Check `http://localhost:8000/` for `{"status": "ok"}`.
4. **Frontend**:
   ```
   cd frontend
   npm run dev
   ```
   Runs at `http://localhost:5173`.

Then open `http://localhost:5173`, register an account, log in, pick a ticker on the
dashboard, and run the analysis. The first request for any given ticker trains its models
on-demand (a few seconds); subsequent requests are served from MongoDB's cache until the
underlying dataset changes.
