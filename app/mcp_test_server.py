import os
from typing import Any
from urllib.parse import urlencode

import httpx
from mcp.server.fastmcp import FastMCP

API_BASE_URL = os.getenv("MCP_API_BASE_URL", "http://127.0.0.1:8766").rstrip("/")
API_KEY = os.getenv("API_KEY", "")

if not API_KEY:
    raise RuntimeError("API_KEY is required")

mcp = FastMCP(
    "Christian Songs MCP Diagnostic",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/mcp-test",
)


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }


def _request(method: str, path: str) -> Any:
    with httpx.Client(timeout=20.0) as client:
        response = client.request(method, f"{API_BASE_URL}{path}", headers=_headers())
    if response.status_code >= 400:
        raise RuntimeError(f"Songs API {response.status_code}: {response.text[:1000]}")
    return response.json() if response.content else {"ok": True}


@mcp.tool()
def mcp_health() -> dict[str, Any]:
    """Read-only diagnostic: verify the MCP server can reach the Christian Songs REST API."""
    return _request("GET", "/health")


@mcp.tool()
def list_songs(status: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
    """Read-only diagnostic: list songs from the Christian Songs database."""
    params = {k: v for k, v in {"status": status, "q": query}.items() if v}
    suffix = f"?{urlencode(params)}" if params else ""
    return _request("GET", f"/api/songs{suffix}")


app = mcp.streamable_http_app()
