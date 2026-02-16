from __future__ import annotations

from fastapi import Request

from .config import Settings
from .openrouter_client import OpenRouterClient


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_openrouter(request: Request) -> OpenRouterClient:
    return request.app.state.openrouter
