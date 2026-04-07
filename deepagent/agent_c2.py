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

# =========================
# 🔹 LLM CONFIG
# =========================
llm = ChatOpenAI(
    model="DeepSeek-V3.2",
    base_url="https://agent-factory.openai.azure.com/openai/v1/",
    api_key=os.getenv("AZURE_MODEL"),
    temperature=0,
)

# =========================
# 🔹 TOOL WRAPPER (LOGGING)
# =========================
def wrap_tool(tool):
    """Wrap MCP tool to log usage"""
    original_ainvoke = getattr(tool, "ainvoke", None)

    if not original_ainvoke:
        return tool  # skip if not async tool

    async def wrapped(*args, **kwargs):
        print(f"\n🛠️ TOOL START: {tool.name}")
        print(f"📥 Input: {args} {kwargs}")

        start = time.perf_counter()
        result = await original_ainvoke(*args, **kwargs)
        end = time.perf_counter()

        print(f"📤 Output: {str(result)[:300]}...")
        print(f"⏱️ Tool Time: {end - start:.2f}s")
        print(f"🛠️ TOOL END: {tool.name}\n")

        return result

    tool.ainvoke = wrapped
    return tool


# =========================
# 🔹 AGENT CLASS
# =========================
class Agent:
    # 🔥 Shared tool cache
    _tools_cache: Dict[Tuple[str, ...], List[Any]] = {}

    def __init__(self, name: str, prompt: str, tools: List[str]):
        self.name = name
        self.prompt = prompt
        self.tool_names = tools

        self.mcp_client = MultiServerMCPClient(json.load(open("new_tools.json")))
        self.agent = None

    async def load_tools(self):
        key = tuple(sorted(self.tool_names))

        # ✅ Use cache
        if key in Agent._tools_cache:
            print(f"⚡ Using cached tools for {key}")
            return Agent._tools_cache[key]

        print(f"🔄 Loading tools for {key}...")

        try:
            all_tools = await self.mcp_client.get_tools()

            # 🔍 Filter tools manually
            filtered_tools = []
            for tool in all_tools:
                name = getattr(tool, "name", "").lower()

                if any(t in name for t in self.tool_names):
                    filtered_tools.append(tool)

            # fallback
            if not filtered_tools:
                print("⚠️ No filtered tools found, using all tools")
                filtered_tools = all_tools

            # 🧹 Remove duplicates
            unique_tools = {
                getattr(t, "name", str(t)): t for t in filtered_tools
            }

            # 🛠️ Wrap tools for logging
            tools = [wrap_tool(t) for t in unique_tools.values()]

            # ✅ Cache
            Agent._tools_cache[key] = tools

            print(f"✅ Cached {len(tools)} tools for {key}")
            return tools

        except Exception as e:
            print("❌ Tool loading failed:", e)
            return []

    async def setup(self):
        """Initialize agent"""
        if self.agent is not None:
            return self.agent

        tools = await self.load_tools()

        self.agent = create_agent(
            model=llm,
            tools=tools,
            name=self.name,
            system_prompt=self.prompt,
        )

        return self.agent

    async def ainvoke(self, query: Dict, config=None):
        """Invoke agent with logging"""

        if self.agent is None:
            await self.setup()

        user_input = query["messages"][-1].content

        # 🔥 AGENT START LOG
        print("\n" + "=" * 70)
        print(f"🤖 AGENT START: {self.name}")
        print(f"🧠 TASK: {user_input}")
        print("=" * 70)

        start_time = time.perf_counter()

        result = await self.agent.ainvoke(query, config)

        end_time = time.perf_counter()

        # 🔥 AGENT END LOG
        print("=" * 70)
        print(f"✅ AGENT END: {self.name}")
        print(f"⏱️ Time Taken: {end_time - start_time:.2f}s")
        print("=" * 70 + "\n")

        return result

    async def llm_access(self, query: str):
        """Direct LLM access"""
        if self.agent is None:
            await self.setup()

        return await self.agent.ainvoke(query)
