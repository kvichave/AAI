from mcp.server.fastmcp import FastMCP
from langchain_tavily import TavilySearch
from langchain_community.tools.tavily_search import TavilySearchResults

import os
from dotenv import load_dotenv
load_dotenv()
mcp=FastMCP("Math")


@mcp.tool()
def add(a:int,b:int)->int:
    """Add two numbers"""
    return a+b

@mcp.tool()
def sub(a:int,b:int)->int:
    """Subtract two numbers"""
    return a-b

@mcp.tool()
def mul(a:int,b:int)->int:
    """Multiply two numbers"""
    return a*b

@mcp.tool()
def div(a:int,b:int)->float:
    """Divide two numbers"""
    return float(a/b)



if __name__ == "__main__":
    mcp.run(transport="stdio")