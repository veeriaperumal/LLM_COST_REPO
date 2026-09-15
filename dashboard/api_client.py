# ---------------------------------------------------------------------------
# api_client.py — HTTP client for the FastAPI backend
# ---------------------------------------------------------------------------
# Wraps httpx calls to every endpoint the dashboard consumes.  Returns
# None when the server is unreachable so pages can fall back to mock data.
# ---------------------------------------------------------------------------

from __future__ import annotations

import httpx

_API_TIMEOUT = 5.0


class APIClient:
    """Thin async client for the LLM Cost Router API."""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self._base = base_url.rstrip("/")

    # -- Internal helpers -----------------------------------------------------

    async def _get(self, path: str) -> dict | list | None:
        try:
            async with httpx.AsyncClient(timeout=_API_TIMEOUT) as client:
                resp = await client.get(f"{self._base}{path}")
                resp.raise_for_status()
                return resp.json()
        except Exception:
            return None

    async def _post(self, path: str, json: dict) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=_API_TIMEOUT) as client:
                resp = await client.post(f"{self._base}{path}", json=json)
                resp.raise_for_status()
                return resp.json()
        except Exception:
            return None

    # -- Endpoints ------------------------------------------------------------

    async def get_health(self) -> dict | None:
        """GET /health (raw JSON, no envelope)."""
        return await self._get("/health")

    async def get_models(self) -> list[dict] | None:
        """GET /api/v1/models — returns list of ModelMetadata dicts."""
        data = await self._get("/api/v1/models")
        if data and data.get("success"):
            return data["data"]
        return None

    async def route_request(self, payload: dict) -> dict | None:
        """POST /api/v1/route — returns RoutingResult dict."""
        data = await self._post("/api/v1/route", payload)
        if data and data.get("success"):
            return data["data"]
        return None

    async def route_graph(self, payload: dict) -> dict | None:
        """POST /api/v1/route/graph — returns graph result dict."""
        data = await self._post("/api/v1/route/graph", payload)
        if data and data.get("success"):
            return data["data"]
        return None
