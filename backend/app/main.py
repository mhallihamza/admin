"""FastAPI application — the security gateway and the ONLY entry point to
data and tools for the platform. Frontends and agents talk to this service;
databases are never exposed directly."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import (admin, chat, conversations, documents, incidents, logs,
                       me, processes, public_chat, redteam, reminders,
                       review_cases, saved_procedures, security, tools)


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    app = FastAPI(
        title="Administrative Guide — Security Gateway",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Agent-Token"],
    )

    app.include_router(me.router)
    app.include_router(chat.router)
    app.include_router(conversations.router)
    app.include_router(documents.router)
    app.include_router(tools.router)
    app.include_router(security.router)
    app.include_router(incidents.router)
    app.include_router(logs.router)
    app.include_router(public_chat.router)
    app.include_router(redteam.router)
    app.include_router(processes.router)
    app.include_router(reminders.router)
    app.include_router(saved_procedures.router)
    app.include_router(review_cases.router)
    app.include_router(admin.router)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "service": "security-gateway"}

    return app


app = create_app()
