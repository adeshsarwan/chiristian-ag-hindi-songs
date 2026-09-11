import os
import mcp.server as mcp_server_package
from mcp.server.mcpserver.server import MCPServer

# mcp 1.30 does not re-export MCPServer from mcp.server.
# Provide the expected attribute before loading app.mcp_server.
if not hasattr(mcp_server_package, "MCPServer"):
    mcp_server_package.MCPServer = MCPServer

from .mcp_server import mcp


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=int(os.getenv("MCP_PORT", "8767")),
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )
