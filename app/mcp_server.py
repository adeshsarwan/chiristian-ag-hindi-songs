import os
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx
from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

API_BASE_URL = os.getenv("MCP_API_BASE_URL", "http://127.0.0.1:8766").rstrip("/")
API_KEY = os.getenv("API_KEY", "")
MCP_ACCESS_TOKEN = os.getenv("MCP_ACCESS_TOKEN", "")

if not API_KEY:
    raise RuntimeError("API_KEY is required")
if not MCP_ACCESS_TOKEN:
    raise RuntimeError("MCP_ACCESS_TOKEN is required")

mcp = FastMCP(
    "Christian AG Hindi Songs",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/mcp",
)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    with httpx.Client(timeout=20.0) as client:
        response = client.request(method, f"{API_BASE_URL}{path}", headers=_headers(), json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"Songs API {response.status_code}: {response.text[:1000]}")
    return response.json() if response.content else {"ok": True}


def _code(song_code: str) -> str:
    return song_code.strip().upper()


@mcp.tool()
def mcp_health() -> dict[str, Any]:
    """Check MCP connectivity to the Christian Songs REST API."""
    return _request("GET", "/health")


@mcp.tool()
def list_songs(status: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
    """List songs, optionally filtering by research status or search text."""
    params = {k: v for k, v in {"status": status, "q": query}.items() if v}
    suffix = f"?{urlencode(params)}" if params else ""
    return _request("GET", f"/api/songs{suffix}")


@mcp.tool()
def get_song(song_code: str) -> dict[str, Any]:
    """Get one canonical song by code such as P10, W01 or S1."""
    return _request("GET", f"/api/songs/{_code(song_code)}")


@mcp.tool()
def add_song(song_code: str, title_hindi: str, category: str | None = None,
             title_roman: str | None = None, first_line_hindi: str | None = None,
             first_line_roman: str | None = None, lyrics: str | None = None,
             book_page: int | None = None, book_source: str | None = None,
             status: str = "researching", notes: str | None = None) -> dict[str, Any]:
    """Create one canonical song record. Recordings are stored separately."""
    return _request("POST", "/api/songs", {
        "song_code": _code(song_code), "category": category, "title_hindi": title_hindi,
        "title_roman": title_roman, "first_line_hindi": first_line_hindi,
        "first_line_roman": first_line_roman, "lyrics": lyrics, "book_page": book_page,
        "book_source": book_source, "status": status, "notes": notes,
    })


@mcp.tool()
def update_song(song_code: str, category: str | None = None,
                title_hindi: str | None = None, title_roman: str | None = None,
                first_line_hindi: str | None = None, first_line_roman: str | None = None,
                lyrics: str | None = None, book_page: int | None = None,
                book_source: str | None = None, status: str | None = None,
                notes: str | None = None) -> dict[str, Any]:
    """Update supplied fields on an existing song."""
    payload = {k: v for k, v in {
        "category": category, "title_hindi": title_hindi, "title_roman": title_roman,
        "first_line_hindi": first_line_hindi, "first_line_roman": first_line_roman,
        "lyrics": lyrics, "book_page": book_page, "book_source": book_source,
        "status": status, "notes": notes,
    }.items() if v is not None}
    return _request("PATCH", f"/api/songs/{_code(song_code)}", payload)


@mcp.tool()
def list_recordings(song_code: str) -> list[dict[str, Any]]:
    """List all recording/tune candidates for a song."""
    return _request("GET", f"/api/songs/{_code(song_code)}/recordings")


@mcp.tool()
def add_recording_candidate(song_code: str, url: str, title: str | None = None,
                            platform: str = "youtube", video_id: str | None = None,
                            channel_name: str | None = None, channel_url: str | None = None,
                            publication_year: int | None = None, language: str | None = "Hindi",
                            version_label: str | None = None, match_score: float | None = None,
                            match_reason: str | None = None,
                            verification_status: str = "candidate",
                            is_primary: bool = False, notes: str | None = None) -> dict[str, Any]:
    """Add a possible tune/recording. Keep alternate candidates when the correct tune is uncertain."""
    return _request("POST", f"/api/songs/{_code(song_code)}/recordings", {
        "platform": platform, "url": url, "video_id": video_id, "title": title,
        "channel_name": channel_name, "channel_url": channel_url,
        "publication_year": publication_year, "language": language,
        "version_label": version_label, "match_score": match_score,
        "match_reason": match_reason, "verification_status": verification_status,
        "is_primary": is_primary, "rejected_reason": None, "notes": notes,
    })


def _find_recording(song_code: str, recording_id: int) -> dict[str, Any]:
    for item in list_recordings(song_code):
        if int(item["id"]) == int(recording_id):
            return item
    raise RuntimeError(f"Recording {recording_id} is not attached to {_code(song_code)}")


def _recording_payload(item: dict[str, Any]) -> dict[str, Any]:
    fields = ("platform", "url", "video_id", "title", "channel_name", "channel_url",
              "publication_year", "language", "version_label", "match_score", "match_reason",
              "verification_status", "is_primary", "rejected_reason", "notes")
    return {field: item.get(field) for field in fields}


@mcp.tool()
def verify_recording(song_code: str, recording_id: int, make_primary: bool = False,
                     verification_note: str = "Manually verified") -> dict[str, Any]:
    """Mark a candidate verified and optionally make it the primary tune."""
    item = _find_recording(song_code, recording_id)
    item["verification_status"] = "verified"
    item["rejected_reason"] = None
    item["notes"] = "\n".join(x for x in [item.get("notes"), verification_note] if x)
    updated = _request("PATCH", f"/api/recordings/{recording_id}", _recording_payload(item))
    if make_primary:
        _request("POST", f"/api/songs/{_code(song_code)}/primary-recording/{recording_id}")
        updated["is_primary"] = True
    return updated


@mcp.tool()
def reject_recording(song_code: str, recording_id: int, reason: str) -> dict[str, Any]:
    """Reject but retain a candidate so research does not rediscover the same wrong version."""
    item = _find_recording(song_code, recording_id)
    item["verification_status"] = "rejected"
    item["is_primary"] = False
    item["rejected_reason"] = reason
    return _request("PATCH", f"/api/recordings/{recording_id}", _recording_payload(item))


@mcp.tool()
def set_primary_recording(song_code: str, recording_id: int) -> dict[str, Any]:
    """Set the selected primary recording for a song."""
    return _request("POST", f"/api/songs/{_code(song_code)}/primary-recording/{recording_id}")


@mcp.tool()
def list_artists() -> list[dict[str, Any]]:
    """List singers, gospel groups, churches, choirs, composers and lyricists."""
    return _request("GET", "/api/artists")


@mcp.tool()
def add_artist(name: str, artist_type: str | None = None, website: str | None = None,
               youtube_channel: str | None = None, instagram: str | None = None,
               facebook: str | None = None, notes: str | None = None) -> dict[str, Any]:
    """Create an artist/group credit record. Never infer composer/lyricist from performer identity."""
    return _request("POST", "/api/artists", {
        "name": name, "type": artist_type, "website": website,
        "youtube_channel": youtube_channel, "instagram": instagram,
        "facebook": facebook, "notes": notes,
    })


@mcp.tool()
def add_recording_credit(recording_id: int, artist_id: int, role: str) -> dict[str, Any]:
    """Attach a credit to a recording with an explicit role."""
    return _request("POST", f"/api/recordings/{recording_id}/credits", {
        "artist_id": artist_id, "role": role,
    })


@mcp.tool()
def get_research(song_code: str) -> list[dict[str, Any]]:
    """Read previous research sources/findings for a song before doing new research."""
    return _request("GET", f"/api/songs/{_code(song_code)}/research")


@mcp.tool()
def add_research(song_code: str, finding: str, source_type: str | None = None,
                 source_url: str | None = None, source_title: str | None = None) -> dict[str, Any]:
    """Save research evidence or an inconclusive finding for future work."""
    return _request("POST", f"/api/songs/{_code(song_code)}/research", {
        "source_type": source_type, "source_url": source_url,
        "source_title": source_title, "finding": finding,
    })


async def require_mcp_token(request: Request, call_next):
    if request.url.path.startswith("/mcp"):
        expected = f"Bearer {MCP_ACCESS_TOKEN}"
        supplied = request.headers.get("authorization", "")
        if not secrets.compare_digest(supplied, expected):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
    return await call_next(request)


app = mcp.streamable_http_app()
app.add_middleware(BaseHTTPMiddleware, dispatch=require_mcp_token)
