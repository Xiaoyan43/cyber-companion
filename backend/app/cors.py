from __future__ import annotations

import os

_DEFAULT_ORIGINS: tuple[str, ...] = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
)


def load_cors_origins() -> list[str]:
    configured = os.getenv("CYBER_COMPANION_CORS_ORIGINS", "")
    extra = [origin.strip() for origin in configured.split(",") if origin.strip()]

    for origin in extra:
        if "*" in origin:
            raise ValueError("Wildcard CORS origins are not allowed.")

    merged: list[str] = []
    seen: set[str] = set()
    for origin in (*_DEFAULT_ORIGINS, *extra):
        if origin in seen:
            continue
        seen.add(origin)
        merged.append(origin)

    return merged
