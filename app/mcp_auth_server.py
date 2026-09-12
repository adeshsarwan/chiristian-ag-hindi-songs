import hmac
import os

from app.mcp_server import app as base_mcp_app

MCP_ACCESS_TOKEN = os.getenv("MCP_ACCESS_TOKEN", "").strip()

if not MCP_ACCESS_TOKEN:
    raise RuntimeError("MCP_ACCESS_TOKEN is required for the bearer-protected MCP endpoint")


class BearerProtectedMCP:
    """ASGI wrapper exposing the existing MCP app at /mcp-auth with Bearer auth.

    The underlying FastMCP app still routes on /mcp. This wrapper authenticates the
    external request, then rewrites /mcp-auth to /mcp before forwarding it.
    """

    def __init__(self, wrapped_app):
        self.wrapped_app = wrapped_app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.wrapped_app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path not in {"/mcp-auth", "/mcp-auth/"}:
            await self._json_response(send, 404, b'{"error":"not_found"}')
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        authorization = headers.get("authorization", "")
        expected = f"Bearer {MCP_ACCESS_TOKEN}"

        if not hmac.compare_digest(authorization, expected):
            await self._json_response(
                send,
                401,
                b'{"error":"unauthorized"}',
                extra_headers=[(b"www-authenticate", b"Bearer")],
            )
            return

        forwarded_scope = dict(scope)
        forwarded_scope["path"] = "/mcp"
        forwarded_scope["raw_path"] = b"/mcp"
        await self.wrapped_app(forwarded_scope, receive, send)

    @staticmethod
    async def _json_response(send, status, body, extra_headers=None):
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
        ]
        if extra_headers:
            headers.extend(extra_headers)

        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})


app = BearerProtectedMCP(base_mcp_app)
