import asyncio
import json
from typing import Dict, Tuple, List, Any
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
import os
from dotenv import load_dotenv
import time
load_dotenv()

# Initialize the LLM
llm = ChatOpenAI(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
)

class Agent:
    # 🔥 Class-level cache (shared across all agents)
    _tools_cache: Dict[Tuple[str, ...], List[Any]] = {}

    def __init__(self, name: str, prompt: str, tools: List[str]):
        self.name = name
        self.prompt = prompt
        self.tool_names = tools

        self.mcp_client = MultiServerMCPClient(json.load(open("new_tools.json")))
        self.agent = None

    async def load_tools(self):
        key = tuple(sorted(self.tool_names))  # ✅ stable key

        # ✅ Return cached tools
        if key in Agent._tools_cache:
            print(f"⚡ Using cached tools for {key}")
            return Agent._tools_cache[key]

        print(f"🔄 Loading tools for {key}...")

        try:

            # ✅ IMPORTANT: your MCP version likely does NOT support server_name
            all_tools = await self.mcp_client.get_tools()
            # ✅ Filter tools manually (instead of server_name)
            filtered_tools = []
            for tool in all_tools:
                name = getattr(tool, "name", "").lower()
                # print("tool",tool)

                if any(t in name for t in self.tool_names):
                    filtered_tools.append(tool)
                    print("tool",tool)

            # fallback: if nothing matched, use all tools
            if not filtered_tools:
                print("⚠️ No filtered tools found, using all tools")
                filtered_tools = all_tools

            # ✅ Remove duplicates
            unique_tools = {getattr(t, "name", str(t)): t for t in filtered_tools}
            tools = list(unique_tools.values())

            # ✅ Store in cache
            Agent._tools_cache[key] = tools

            print(f"✅ Cached {len(tools)} tools for {key}")
            return tools

        except Exception as e:
            print("❌ Tool loading failed:", e)
            return []

    async def setup(self):
        """Setup the agent"""
        if self.agent is not None:
            return self.agent  # already initialized

        tools = await self.load_tools()

        self.agent = create_agent(
            model=llm,
            tools=tools,
            name=self.name,
            system_prompt=self.prompt
        )

        return self.agent

    async def ainvoke(self, query: str, config=None):
        """Invoke the agent"""
        if self.agent is None:
            await self.setup()


        start_time = time.perf_counter()
        print("giving to agent")
        result = await self.agent.ainvoke(query, config)
        end_time = time.perf_counter()
        print(f"Agent {self.name} took {end_time - start_time} seconds to complete")
        return result

    async def llm_access(self, query: str):
        """Direct LLM access"""
        if self.agent is None:
            await self.setup()
        return await self.agent.ainvoke(query)