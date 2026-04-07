from mcp.server.fastmcp import FastMCP

from dotenv import load_dotenv
import json

mcp = FastMCP("Weather")

@mcp.tool()
async def get_weather(city: str) -> str:
    """Get weather of a city"""
    return f"Weather in {city} is like VEDIKA"



if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
    )
