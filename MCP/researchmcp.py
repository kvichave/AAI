from mcp.server.fastmcp import FastMCP
from langchain_tavily import TavilySearch
from langchain_community.tools.tavily_search import TavilySearchResults

import os
from dotenv import load_dotenv
load_dotenv()
mcp=FastMCP("Research")

@mcp.tool()
async def search_web(query:str)->str:
    """Search the web for information."""

    search = TavilySearchResults(api_key=os.getenv("TAVILY_API_KEY"),max_results=3)
    results=await search.ainvoke(query)
    return str(results)

if __name__ == "__main__":
    mcp.run(transport="stdio")