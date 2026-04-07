import asyncio
import json
from typing import List
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize the LLM
llm = ChatOpenAI(
    model="nvidia/nemotron-3-super-120b-a12b:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API"),
    temperature=0,
)

class Agent:
    _tools_cache = None

    def __init__(self, name: str, prompt: str, tools: List[str]):
        self.name = name
        self.prompt = prompt
        self.tool_names = tools

        # MCP Client using the JSON config
        self.mcp_client = MultiServerMCPClient(json.load(open("new_tools.json")))
        self.agent = None  # Will hold the actual LangChain agent

    async def load_tools(self):
        """Load tools from MCP servers asynchronously"""
        tool_lists = await asyncio.gather(
            *[self.mcp_client.get_tools(server_name=name) for name in self.tool_names]
        )
        # Flatten the list
        return [tool for sublist in tool_lists for tool in sublist]

    async def setup(self):
        """Setup the agent with tools and prompt"""
        tools = await self.load_tools()
        self.agent = create_agent(
            model=llm,
            tools=tools,
            name=self.name,
            system_prompt=self.prompt
        )
        return self.agent

    async def ainvoke(self, query: str, config=None):
        """Invoke the agent with a query"""
        if self.agent is None:
            await self.setup()
        return await self.agent.ainvoke(query, config)

    async def llm_access(self, query: str):
        """Direct access to the agent's LLM for a query"""
        if self.agent is None:
            await self.setup()
        return await self.agent.ainvoke(query)