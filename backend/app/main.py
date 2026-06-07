from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.schemas import HealthResponse

APP_VERSION = "0.1.0"

app = FastAPI(
    title="Cyber Companion Local API",
    version=APP_VERSION,
    summary="Local API shell for the text-first desktop companion MVP.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="cyber-companion-api",
        version=APP_VERSION,
    )
