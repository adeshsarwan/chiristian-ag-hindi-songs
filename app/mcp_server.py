import os
import secrets
from typing import Any

import httpx
from mcp.server import MCPServer
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

API_BASE_URL = os.getenv("MCP_API_BASE_URL", "http://127.0.0.1:8766").rstrip("/")
API_KEY = os.getenv("API_KEY", "")
MCP_ACCESS_TOKEN = os.getenv("MCP_ACCESS_TOKEN", "")
MCP_PUBLIC_URL = os.getenv("MCP_PUBLIC_URL", "https://christiansongs.blazingtrail.in/mcp")
MCP_ISSUER_URL = os.getenv("MCP_ISSUER_URL", "https://christiansongs.blazingtrail.in")

if not API_KEY:
    raise RuntimeError("API_KEY is required")
if not MCP_ACCESS_TOKEN:
    raise RuntimeError("MCP_ACCESS_TOKEN is required")


class StaticTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        if not secrets.compare_digest(token, MCP_ACCESS_TOKEN):
            return None
        return AccessToken(
            token=token,
            client_id="christian-songs-mcp-client",
            scopes=["songs:read", "songs:write"],
            subject="christian-songs-admin",
        )


mcp = MCPServer(
    "Christian AG Hindi Songs",
    token_verifier=StaticTokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(MCP_ISSUER_URL),
        resource_server_url=AnyHttpUrl(MCP_PUBLIC_URL),
        required_scopes=["songs:read"],
    ),
)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    url = f"{API_BASE_URL}{path}"
    with httpx.Client(timeout=20.0) as client:
        response = client.request(method, url, headers=_headers(), json=payload)
    if response.status_code >= 400:
        detail = response.text[:1000]
        raise RuntimeError(f"Songs API {response.status_code} for {path}: {detail}")
    if not response.content:
        return {"ok": True}
    return response.json()


def _song_code(song_code: str) -> str:
    return song_code.strip().upper()


@mcp.tool()
def list_songs(status: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
    """List songs already stored in the tune-book database. Optionally filter by research status or search text."""
    params: list[str] = []
    if status:
        params.append(f"status={httpx.QueryParams({'x': status})['x']}")
    if query:
        params.append(f"q={httpx.QueryParams({'x': query})['x']}")
    suffix = "?" + "&".join(params) if params else ""
    return _request("GET", f"/api/songs{suffix}")


@mcp.tool()
def get_song(song_code: str) -> dict[str, Any]:
    """Get one canonical song record by book code such as P10, W01 or S1."""
    return _request("GET", f"/api/songs/{_song_code(song_code)}")


@mcp.tool()
def add_song(
    song_code: str,
    title_hindi: str,
    category: str | None = None,
    title_roman: str | None = None,
    first_line_hindi: str | None = None,
    first_line_roman: str | None = None,
    lyrics: str | None = None,
    book_page: int | None = None,
    book_source: str | None = None,
    status: str = "researching",
    notes: str | None = None,
) -> dict[str, Any]:
    """Create a canonical song record. Use one record per song-book code; recordings belong under the song separately."""
    payload = {
        "song_code": _song_code(song_code), "category": category, "title_hindi": title_hindi,
        "title_roman": title_roman, "first_line_hindi": first_line_hindi,
        "first_line_roman": first_line_roman, "lyrics": lyrics, "book_page": book_page,
        "book_source": book_source, "status": status, "notes": notes,
    }
    return _request("POST", "/api/songs", payload)


@mcp.tool()
def update_song(
    song_code: str,
    category: str | None = None,
    title_hindi: str | None = None,
    title_roman: str | None = None,
    first_line_hindi: str | None = None,
    first_line_roman: str | None = None,
    lyrics: str | None = None,
    book_page: int | None = None,
    book_source: str | None = None,
    status: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Update fields on an existing canonical song record."""
    payload = {k: v for k, v in {
        "category": category, "title_hindi": title_hindi, "title_roman": title_roman,
        "first_line_hindi": first_line_hindi, "first_line_roman": first_line_roman,
        "lyrics": lyrics, "book_page": book_page, "book_source": book_source,
        "status": status, "notes": notes,
    }.items() if v is not None}
    return _request("PATCH", f"/api/songs/{_song_code(song_code)}", payload)


@mcp.tool()
def list_recordings(song_code: str) -> list[dict[str, Any]]:
    """List all tune/recording candidates for a song, including alternates and rejected candidates."""
    return _request("GET", f"/api/songs/{_song_code(song_code)}/recordings")


@mcp.tool()
def add_recording_candidate(
    song_code: str,
    url: str,
    title: str | None = None,
    platform: str = "youtube",
    video_id: str | None = None,
    channel_name: str | None = None,
    channel_url: str | None = None,
    publication_year: int | None = None,
    language: str | None = "Hindi",
    version_label: str | None = None,
    match_score: float | None = None,
    match_reason: str | None = None,
    verification_status: str = "candidate",
    is_primary: bool = False,
    notes: str | None = None,
) -> dict[str, Any]:
    """Add a recording/tune candidate to a song. Keep multiple plausible versions rather than forcing an uncertain primary match."""
    payload = {
        "platform": platform, "url": url, "video_id": video_id, "title": title,
        "channel_name": channel_name, "channel_url": channel_url,
        "publication_year": publication_year, "language": language,
        "version_label": version_label, "match_score": match_score,
        "match_reason": match_reason, "verification_status": verification_status,
        "is_primary": is_primary, "rejected_reason": None, "notes": notes,
    }
    return _request("POST", f"/api/songs/{_song_code(song_code)}/recordings", payload)


def _find_recording(song_code: str, recording_id: int) -> dict[str, Any]:
    for item in list_recordings(song_code):
        if int(item["id"]) == int(recording_id):
            return item
    raise RuntimeError(f"Recording {recording_id} is not attached to {_song_code(song_code)}")


def _recording_update_payload(item: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "platform", "url", "video_id", "title", "channel_name", "channel_url",
        "publication_year", "language", "version_label", "match_score", "match_reason",
        "verification_status", "is_primary", "rejected_reason", "notes",
    }
    return {k: item.get(k) for k in allowed}


@mcp.tool()
def verify_recording(
    song_code: str,
    recording_id: int,
    make_primary: bool = False,
    verification_note: str = "Manually verified",
) -> dict[str, Any]:
    """Mark an existing recording as verified after manual or authoritative review. Optionally make it the primary tune."""
    item = _find_recording(song_code, recording_id)
    item["verification_status"] = "verified"
    item["rejected_reason"] = None
    prior = item.get("notes") or ""
    item["notes"] = (prior + "\n" + verification_note).strip()
    updated = _request("PATCH", f"/api/recordings/{recording_id}", _recording_update_payload(item))
    if make_primary:
        _request("POST", f"/api/songs/{_song_code(song_code)}/primary-recording/{recording_id}")
        updated["is_primary"] = True
    return updated


@mcp.tool()
def reject_recording(song_code: str, recording_id: int, reason: str) -> dict[str, Any]:
    """Reject a recording candidate but retain it in the research history so it is not rediscovered later."""
    item = _find_recording(song_code, recording_id)
    item["verification_status"] = "rejected"
    item["is_primary"] = False
    item["rejected_reason"] = reason
    return _request("PATCH", f"/api/recordings/{recording_id}", _recording_update_payload(item))


@mcp.tool()
def set_primary_recording(song_code: str, recording_id: int) -> dict[str, Any]:
    """Select the primary recording/tune for a song after verification."""
    return _request("POST", f"/api/songs/{_song_code(song_code)}/primary-recording/{recording_id}")


@mcp.tool()
def list_artists() -> list[dict[str, Any]]:
    """List known singers, gospel groups, churches, choirs, composers and lyricists used for recording credits."""
    return _request("GET", "/api/artists")


@mcp.tool()
def add_artist(
    name: str,
    artist_type: str | None = None,
    website: str | None = None,
    youtube_channel: str | None = None,
    instagram: str | None = None,
    facebook: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Create an artist/organization credit record. Do not infer composer or lyricist from performer identity."""
    return _request("POST", "/api/artists", {
        "name": name, "type": artist_type, "website": website,
        "youtube_channel": youtube_channel, "instagram": instagram,
        "facebook": facebook, "notes": notes,
    })


@mcp.tool()
def add_recording_credit(recording_id: int, artist_id: int, role: str) -> dict[str, Any]:
    """Attach an artist/group/church to a recording with an explicit role such as performer, singer, worship_group, composer, lyricist or source."""
    return _request("POST", f"/api/recordings/{recording_id}/credits", {"artist_id": artist_id, "role": role})


@mcp.tool()
def get_research(song_code: str) -> list[dict[str, Any]]:
    """Read prior research sources and findings for a song before doing new web research."""
    return _request("GET", f"/api/songs/{_song_code(song_code)}/research")


@mcp.tool()
def add_research(
    song_code: str,
    finding: str,
    source_type: str | None = None,
    source_url: str | None = None,
    source_title: str | None = None,
) -> dict[str, Any]:
    """Save a research source or finding, including inconclusive searches, so future work can build on prior investigation."""
    return _request("POST", f"/api/songs/{_song_code(song_code)}/research", {
        "source_type": source_type, "source_url": source_url,
        "source_title": source_title, "finding": finding,
    })


@mcp.tool()
def mcp_health() -> dict[str, Any]:
    """Check connectivity from MCP to the protected Christian Songs REST API."""
    return _request("GET", "/health")


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=int(os.getenv("MCP_PORT", "8767")),
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )
