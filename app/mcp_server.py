import os
from typing import Any
from urllib.parse import urlencode

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

API_BASE_URL = os.getenv("MCP_API_BASE_URL", "http://127.0.0.1:8766").rstrip("/")
API_KEY = os.getenv("API_KEY", "")
MCP_WRITES_ENABLED = os.getenv("MCP_WRITES_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
if not API_KEY: raise RuntimeError("API_KEY is required")

mcp = FastMCP("Christian AG Hindi Songs", stateless_http=True, json_response=True, streamable_http_path="/mcp")
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
WRITE_NONDESTRUCTIVE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)


def _headers(): return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
def _request(method, path, payload=None):
    with httpx.Client(timeout=20.0) as client: response = client.request(method, f"{API_BASE_URL}{path}", headers=_headers(), json=payload)
    if response.status_code >= 400: raise RuntimeError(f"Songs API {response.status_code}: {response.text[:1000]}")
    return response.json() if response.content else {"ok": True}
def _code(song_code): return song_code.strip().upper()
def _blocked(tool, requested):
    if MCP_WRITES_ENABLED: return None
    return {"ok": False, "mode": "dry_run", "tool": tool, "message": "Write tools are disabled until authenticated production mode is enabled.", "requested": requested}


@mcp.tool(annotations=READ_ONLY)
def mcp_health() -> dict[str, Any]:
    """Check MCP connectivity to the Christian Songs REST API."""
    result = _request("GET", "/health"); result["mcp_writes_enabled"] = MCP_WRITES_ENABLED; return result

@mcp.tool(annotations=READ_ONLY)
def list_songs(status: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
    """List songs, optionally filtering by research status or search text."""
    params = {k:v for k,v in {"status":status,"q":query}.items() if v}; suffix = f"?{urlencode(params)}" if params else ""; return _request("GET", f"/api/songs{suffix}")

@mcp.tool(annotations=READ_ONLY)
def get_song(song_code: str) -> dict[str, Any]:
    """Get one canonical song by code."""
    return _request("GET", f"/api/songs/{_code(song_code)}")

@mcp.tool(annotations=WRITE_NONDESTRUCTIVE)
def add_song(song_code: str, title_hindi: str, category: str | None=None, title_roman: str | None=None, first_line_hindi: str | None=None, first_line_roman: str | None=None, lyrics: str | None=None, lyrics_book_hindi: str | None=None, lyrics_normalized_hindi: str | None=None, lyrics_roman: str | None=None, book_page: int | None=None, book_source: str | None=None, status: str="researching", notes: str | None=None) -> dict[str, Any]:
    """Create one canonical song record."""
    payload=locals().copy(); payload["song_code"]=_code(song_code); blocked=_blocked("add_song",payload); return blocked or _request("POST","/api/songs",payload)

@mcp.tool(annotations=WRITE_NONDESTRUCTIVE)
def update_song(song_code: str, category: str | None=None, title_hindi: str | None=None, title_roman: str | None=None, first_line_hindi: str | None=None, first_line_roman: str | None=None, lyrics: str | None=None, lyrics_book_hindi: str | None=None, lyrics_normalized_hindi: str | None=None, lyrics_roman: str | None=None, book_page: int | None=None, book_source: str | None=None, status: str | None=None, notes: str | None=None) -> dict[str, Any]:
    """Update supplied fields on an existing song."""
    payload={k:v for k,v in locals().items() if k != "song_code" and v is not None}; requested={"song_code":_code(song_code),**payload}; blocked=_blocked("update_song",requested); return blocked or _request("PATCH",f"/api/songs/{_code(song_code)}",payload)

@mcp.tool(annotations=WRITE_NONDESTRUCTIVE)
def set_normalized_lyrics(song_code: str, lyrics_normalized_hindi: str, lyrics_roman: str | None=None) -> dict[str, Any]:
    """Set editorially normalized Hindi lyrics and optional Roman transliteration without overwriting book transcription."""
    payload={"lyrics_normalized_hindi":lyrics_normalized_hindi};
    if lyrics_roman is not None: payload["lyrics_roman"]=lyrics_roman
    blocked=_blocked("set_normalized_lyrics",{"song_code":_code(song_code),**payload}); return blocked or _request("PATCH",f"/api/songs/{_code(song_code)}",payload)

@mcp.tool(annotations=READ_ONLY)
def list_recordings(song_code: str) -> list[dict[str, Any]]:
    """List all recording/tune candidates for a song."""
    return _request("GET",f"/api/songs/{_code(song_code)}/recordings")

@mcp.tool(annotations=WRITE_NONDESTRUCTIVE)
def add_recording_candidate(song_code: str, url: str, title: str | None=None, platform: str="youtube", video_id: str | None=None, channel_name: str | None=None, channel_url: str | None=None, publication_year: int | None=None, language: str | None="Hindi", version_label: str | None=None, match_score: float | None=None, match_reason: str | None=None, verification_status: str="candidate", is_primary: bool=False, start_seconds: int | None=None, end_seconds: int | None=None, notes: str | None=None) -> dict[str, Any]:
    """Add a possible tune/recording, optionally with its usable tune segment."""
    payload={k:v for k,v in locals().items() if k != "song_code"}; blocked=_blocked("add_recording_candidate",{"song_code":_code(song_code),**payload}); return blocked or _request("POST",f"/api/songs/{_code(song_code)}/recordings",payload)

@mcp.tool(annotations=WRITE_NONDESTRUCTIVE)
def set_recording_segment(song_code: str, recording_id: int, start_seconds: int | None=None, end_seconds: int | None=None) -> dict[str, Any]:
    """Set the exact usable tune segment within an external recording."""
    payload={"start_seconds":start_seconds,"end_seconds":end_seconds}; requested={"song_code":_code(song_code),"recording_id":recording_id,**payload}; blocked=_blocked("set_recording_segment",requested)
    if blocked: return blocked
    recordings=list_recordings(song_code)
    if not any(int(x["id"])==int(recording_id) for x in recordings): raise RuntimeError(f"Recording {recording_id} is not attached to {_code(song_code)}")
    return _request("PATCH",f"/api/recordings/{recording_id}",payload)

def _find_recording(song_code,recording_id):
    for item in list_recordings(song_code):
        if int(item["id"])==int(recording_id): return item
    raise RuntimeError(f"Recording {recording_id} is not attached to {_code(song_code)}")

@mcp.tool(annotations=WRITE_NONDESTRUCTIVE)
def verify_recording(song_code: str, recording_id: int, make_primary: bool=False, verification_note: str="Manually verified") -> dict[str, Any]:
    """Mark a candidate verified and optionally make it the primary tune."""
    requested={"song_code":_code(song_code),"recording_id":recording_id,"make_primary":make_primary,"verification_note":verification_note}; blocked=_blocked("verify_recording",requested)
    if blocked:return blocked
    item=_find_recording(song_code,recording_id); notes="\n".join(x for x in [item.get("notes"),verification_note] if x); updated=_request("PATCH",f"/api/recordings/{recording_id}",{"verification_status":"verified","rejected_reason":None,"notes":notes})
    if make_primary: _request("POST",f"/api/songs/{_code(song_code)}/primary-recording/{recording_id}"); updated["is_primary"]=True
    return updated

@mcp.tool(annotations=WRITE_NONDESTRUCTIVE)
def reject_recording(song_code: str, recording_id: int, reason: str) -> dict[str, Any]:
    """Reject but retain a candidate so research does not rediscover the same wrong version."""
    requested={"song_code":_code(song_code),"recording_id":recording_id,"reason":reason}; blocked=_blocked("reject_recording",requested)
    if blocked:return blocked
    _find_recording(song_code,recording_id); return _request("PATCH",f"/api/recordings/{recording_id}",{"verification_status":"rejected","is_primary":False,"rejected_reason":reason})

@mcp.tool(annotations=WRITE_NONDESTRUCTIVE)
def set_primary_recording(song_code: str, recording_id: int) -> dict[str, Any]:
    """Set the selected external reference recording as primary."""
    requested={"song_code":_code(song_code),"recording_id":recording_id}; blocked=_blocked("set_primary_recording",requested); return blocked or _request("POST",f"/api/songs/{_code(song_code)}/primary-recording/{recording_id}")

@mcp.tool(annotations=READ_ONLY)
def list_lyric_variants(song_code: str) -> list[dict[str, Any]]:
    """List preserved lyric variants and their sources."""
    return _request("GET",f"/api/songs/{_code(song_code)}/lyric-variants")

@mcp.tool(annotations=WRITE_NONDESTRUCTIVE)
def add_lyric_variant(song_code: str, lyrics_hindi: str, source_type: str | None=None, source_title: str | None=None, source_url: str | None=None, difference_notes: str | None=None, confidence: float | None=None) -> dict[str, Any]:
    """Preserve a sourced lyric variant without overwriting canonical book or normalized lyrics."""
    payload={k:v for k,v in locals().items() if k != "song_code"}; blocked=_blocked("add_lyric_variant",{"song_code":_code(song_code),**payload}); return blocked or _request("POST",f"/api/songs/{_code(song_code)}/lyric-variants",payload)

@mcp.tool(annotations=READ_ONLY)
def list_arrangements(song_code: str) -> list[dict[str, Any]]:
    """List planned or produced house arrangements for a song."""
    return _request("GET",f"/api/songs/{_code(song_code)}/arrangements")

@mcp.tool(annotations=WRITE_NONDESTRUCTIVE)
def add_arrangement(song_code: str, arrangement_type: str="congregational", preferred_key: str | None=None, tempo_bpm: int | None=None, tempo_style: str | None=None, lead_instrument: str | None=None, accompaniment_notes: str | None=None, vocal_notes: str | None=None, production_status: str="planned", audio_url: str | None=None, notes: str | None=None) -> dict[str, Any]:
    """Create a house-arrangement plan, kept separate from external reference recordings."""
    payload={k:v for k,v in locals().items() if k != "song_code"}; blocked=_blocked("add_arrangement",{"song_code":_code(song_code),**payload}); return blocked or _request("POST",f"/api/songs/{_code(song_code)}/arrangements",payload)

@mcp.tool(annotations=WRITE_NONDESTRUCTIVE)
def update_arrangement(arrangement_id: int, preferred_key: str | None=None, tempo_bpm: int | None=None, tempo_style: str | None=None, lead_instrument: str | None=None, accompaniment_notes: str | None=None, vocal_notes: str | None=None, production_status: str | None=None, audio_url: str | None=None, notes: str | None=None) -> dict[str, Any]:
    """Update supplied fields on a house arrangement."""
    payload={k:v for k,v in locals().items() if k != "arrangement_id" and v is not None}; blocked=_blocked("update_arrangement",{"arrangement_id":arrangement_id,**payload}); return blocked or _request("PATCH",f"/api/arrangements/{arrangement_id}",payload)

@mcp.tool(annotations=READ_ONLY)
def list_artists() -> list[dict[str, Any]]:
    """List singers, gospel groups, churches, choirs, composers and lyricists."""
    return _request("GET","/api/artists")

@mcp.tool(annotations=WRITE_NONDESTRUCTIVE)
def add_artist(name: str, artist_type: str | None=None, website: str | None=None, youtube_channel: str | None=None, instagram: str | None=None, facebook: str | None=None, notes: str | None=None) -> dict[str, Any]:
    """Create an artist/group credit record. Never infer composer/lyricist from performer identity."""
    payload={"name":name,"type":artist_type,"website":website,"youtube_channel":youtube_channel,"instagram":instagram,"facebook":facebook,"notes":notes}; blocked=_blocked("add_artist",payload); return blocked or _request("POST","/api/artists",payload)

@mcp.tool(annotations=WRITE_NONDESTRUCTIVE)
def add_recording_credit(recording_id: int, artist_id: int, role: str) -> dict[str, Any]:
    """Attach a credit to a recording with an explicit role."""
    payload={"recording_id":recording_id,"artist_id":artist_id,"role":role}; blocked=_blocked("add_recording_credit",payload); return blocked or _request("POST",f"/api/recordings/{recording_id}/credits",{"artist_id":artist_id,"role":role})

@mcp.tool(annotations=READ_ONLY)
def get_research(song_code: str) -> list[dict[str, Any]]:
    """Read previous research sources/findings for a song before doing new research."""
    return _request("GET",f"/api/songs/{_code(song_code)}/research")

@mcp.tool(annotations=WRITE_NONDESTRUCTIVE)
def add_research(song_code: str, finding: str, source_type: str | None=None, source_url: str | None=None, source_title: str | None=None) -> dict[str, Any]:
    """Save research evidence or an inconclusive finding for future work."""
    payload={"source_type":source_type,"source_url":source_url,"source_title":source_title,"finding":finding}; blocked=_blocked("add_research",{"song_code":_code(song_code),**payload}); return blocked or _request("POST",f"/api/songs/{_code(song_code)}/research",payload)

app=mcp.streamable_http_app()
