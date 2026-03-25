from mcp.server.fastmcp import FastMCP
from langchain_tavily import TavilySearch
from langchain_community.tools.tavily_search import TavilySearchResults
from dotenv import load_dotenv
import json
import os
load_dotenv()
mcp = FastMCP("Weather")

@mcp.tool()
async def get_weather(city: str) -> str:
    """Get weather of a city"""
    return f"Weather in {city} is bvidfbvibdfivbijdfb"

@mcp.tool()
async def search_web(query:str)->str:
    """Search the web for information."""

    search = TavilySearchResults(api_key=os.getenv("TAVILY_API_KEY"),max_results=3)
    results=await search.ainvoke(query)
    return str(results)


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
    )
