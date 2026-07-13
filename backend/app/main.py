import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import client
from app.routers import auth, chat, efficiency, explainability, history, prediction, volatility

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nepse-ai")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(efficiency.router)
app.include_router(volatility.router)
app.include_router(prediction.router)
app.include_router(explainability.router)
app.include_router(history.router)
app.include_router(chat.router)


@app.on_event("startup")
async def check_mongo_connection():
    try:
        await client.admin.command("ping")
        logger.info("MongoDB connection successful (%s)", settings.MONGO_URI)
    except Exception as exc:
        logger.error("MongoDB connection failed: %s", exc)


@app.get("/")
async def health_check():
    return {"status": "ok"}
