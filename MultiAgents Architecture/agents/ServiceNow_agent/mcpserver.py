from servicenow_mcp.server import ServiceNowMCP
from servicenow_mcp.server_sse import create_starlette_app
from servicenow_mcp.utils.config import ServerConfig, AuthConfig, AuthType, BasicAuthConfig
import uvicorn

# Create server configuration
config = ServerConfig(
    instance_url="https://dev315873.service-now.com/",
    auth=AuthConfig(
        type=AuthType.BASIC,
        config=BasicAuthConfig(
            username="admin",
            password="Uhvc*6bD8-TA"
        )
    ),
    debug=True,
)

# Create ServiceNow MCP server
servicenow_mcp = ServiceNowMCP(config)

# Create Starlette app with SSE transport
app = create_starlette_app(servicenow_mcp, debug=True)

# Start the web server
uvicorn.run(app, host="0.0.0.0", port=8080)