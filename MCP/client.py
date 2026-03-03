from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

import asyncio

from dotenv import load_dotenv
import json
load_dotenv()
import os



llm = ChatOpenAI(
    model="qwen/qwen3-32b",
    base_url=os.getenv("GROQ_URL"),
    temperature=0.7,
    api_key=os.getenv("GROQ_API"),
)

async def main():
    mcp_client = MultiServerMCPClient(
        json.load(open("tools.json"))
    )
    
    

    
    try:
        tools = await mcp_client.get_tools()
    except Exception as e:
        print("Failed to load MCP tools:", e)
        return
    agent=create_agent(llm,tools)
    weather_response=await agent.ainvoke({"messages":[{"role":"user","content":"What is the latest news, websearch it"}]})
    print(weather_response["messages"][-1].content)


asyncio.run(main())