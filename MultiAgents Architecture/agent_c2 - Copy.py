import asyncio
import json
import time
import os
from typing import Dict, Tuple, List, Any, Optional
from contextvars import ContextVar
from collections import defaultdict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)

load_dotenv()

# =========================
# 🔹 AGENT CONTEXT TRACKING
# =========================
current_agent: ContextVar[str] = ContextVar("current_agent", default="UnknownAgent")
current_task: ContextVar[str] = ContextVar("current_task", default="UnknownTask")

call_counter = defaultdict(int)

# =========================
# 🔹 GLOBAL TOOL CACHE
# =========================
_tools_cache: Dict[Tuple[str, ...], List[Any]] = {}

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
# 🔹 MCP CLIENT
# =========================
mcp_client = MultiServerMCPClient(json.load(open("new_tools.json")))

# =========================
# 🔹 TOOL MATCHING
# =========================
TOOL_ALIASES = {
    "search": ["search", "tavily", "google"],
    "weather": ["weather", "forecast"],
    "sql": ["sql", "database", "query"],
    "finance": ["stock", "finance", "crypto"],
}


def match_tool(tool_name: str, keywords: list) -> bool:
    tool_name = tool_name.lower()
    expanded = []
    for key in keywords:
        expanded.append(key)
        expanded.extend(TOOL_ALIASES.get(key, []))
    return any(keyword in tool_name for keyword in expanded)


# =========================
# 🔹 SCHEMA HELPERS
# =========================

# JSON Schema structural keys that are NEVER real parameter names.
# Pydantic RootModel also serialises its single field as "root" — also noise.
_SCHEMA_NOISE_KEYS = frozenset({
    "root", "title", "description", "type", "default",
    "examples", "anyOf", "allOf", "oneOf", "$ref", "$defs",
    "additionalProperties", "required",
})


def get_schema_param_names(tool: Any) -> List[str]:
    """
    Return all real parameter names from a tool's schema.

    Checks both args_schema (LangChain) and input_schema (MCP) and handles:
      - Pydantic v2 model classes  (model_fields)
      - Pydantic v1 model classes  (.schema())
      - Raw JSON Schema dicts      (MCP tools)
    """
    # MCP tools store their schema in input_schema; LangChain uses args_schema
    schema = getattr(tool, "args_schema", None) or getattr(tool, "input_schema", None)

    if schema is None:
        return []

    # Pydantic v2
    if hasattr(schema, "model_fields"):
        return [k for k in schema.model_fields if k not in _SCHEMA_NOISE_KEYS]

    # Pydantic v1
    if hasattr(schema, "schema"):
        props = schema.schema().get("properties", {})
        return [k for k in props if k not in _SCHEMA_NOISE_KEYS]

    # Raw JSON Schema dict (most MCP tools)
    if isinstance(schema, dict):
        props = schema.get("properties", {})
        return [k for k in props if k not in _SCHEMA_NOISE_KEYS]

    return []


def build_tool_input(tool: Any, args: tuple, kwargs: dict) -> dict:
    """
    Normalise all the messy calling conventions LangChain / MCP adapters
    produce into a clean {param_name: value} dict.
    """

    # STEP 1: unwrap nested kwargs  e.g. {'kwargs': {'kwargs': {...}}}
    while isinstance(kwargs, dict) and "kwargs" in kwargs:
        kwargs = kwargs["kwargs"]

    # STEP 2: {'args': [...]} → treat list contents as positional args
    if (
        isinstance(kwargs, dict)
        and list(kwargs.keys()) == ["args"]
        and isinstance(kwargs.get("args"), list)
    ):
        args = tuple(kwargs["args"])
        kwargs = {}

    # STEP 3: clean kwargs present → use directly
    if kwargs:
        return kwargs

    # STEP 4: fall back to positional args
    if not args:
        return {}

    positional = list(args)

    # STEP 5: map positionals → named params via schema
    param_names = get_schema_param_names(tool)
    if param_names:
        return dict(zip(param_names, positional))

    # STEP 6: no schema at all — fail loudly rather than guess a key name
    raise ValueError(
        f"Tool '{getattr(tool, 'name', tool)}' has no introspectable schema. "
        f"Cannot map positional arg(s) {positional!r} to parameter names. "
        "Ensure the tool exposes a valid args_schema or input_schema."
    )


# =========================
# 🔹 ASYNC TOOL WRAPPER
# =========================
class AsyncToolWrapper(BaseTool):
    tool: Any

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, tool: Any):
        super().__init__(
            name=getattr(tool, "name", "unknown"),
            description=getattr(tool, "description", "No description"),
            tool=tool,
        )

    def _run(
        self,
        *args: Any,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Any:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        *args: Any,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Any:

        agent_name = current_agent.get()
        task_name = current_task.get()

        call_counter[agent_name] += 1
        call_id = int(time.time() * 1000)

        print("\n" + "=" * 70)
        print(f"🔁 CALL ID    : {call_id}")
        print(f"🤖 AGENT      : {agent_name}")
        print(f"🧠 TASK       : {task_name}")
        print(f"📊 CALL COUNT : {call_counter[agent_name]}")
        print(f"🛠️  TOOL START: {self.name}")
        print(f"📥 Input      : args={args} kwargs={kwargs}")

        start = time.perf_counter()

        tool_input = build_tool_input(self.tool, args, kwargs)
        print(f"📦 tool_input : {tool_input}")

        try:
            # Always invoke with a dict — LangChain requires this for any tool
            # that declares an args_schema or input_schema.
            if hasattr(self.tool, "ainvoke"):
                result = await self.tool.ainvoke(tool_input)
            elif hasattr(self.tool, "invoke"):
                result = await asyncio.to_thread(self.tool.invoke, tool_input)
            elif callable(self.tool):
                result = await asyncio.to_thread(self.tool, tool_input)
            else:
                raise RuntimeError(f"Tool '{self.name}' is not callable")

        except Exception as exc:
            print(f"❌ TOOL ERROR ({self.name}): {exc}")
            raise

        elapsed = time.perf_counter() - start

        print(f"📤 Output     : {str(result)[:300]}...")
        print(f"⏱️  Tool Time  : {round(elapsed, 2)}s")
        print(f"🛠️  TOOL END  : {self.name}")
        print(f"🤖 AGENT DONE : {agent_name}")
        print("=" * 70 + "\n")

        return result


# =========================
# 🔹 LOAD MCP TOOLS
# =========================
async def load_tools(tool_names: List[str]):
    key = tuple(sorted(tool_names))

    if key in _tools_cache:
        print(f"⚡ Using cached tools for {key}")
        return _tools_cache[key]

    print(f"🔄 Loading tools for {key}...")

    try:
        all_tools = await mcp_client.get_tools()

        filtered = [
            t for t in all_tools
            if match_tool(getattr(t, "name", ""), tool_names)
        ]

        if not filtered:
            filtered = all_tools

        unique = {getattr(t, "name", str(t)): t for t in filtered}
        tools = [AsyncToolWrapper(t) for t in unique.values()]

        _tools_cache[key] = tools

        print(f"✅ Cached {len(tools)} tool(s)")
        return tools

    except Exception as exc:
        print(f"❌ Tool loading failed: {exc}")
        return []


# =========================
# 🔹 AGENT RUNNER
# =========================
async def run_agent(agent_name: str, task: str, agent_executor, input_data):

    token_agent = current_agent.set(agent_name)
    token_task = current_task.set(task)

    print("\n" + "🚀" * 20)
    print(f"🚀 AGENT START: {agent_name}")
    print(f"🧠 TASK       : {task}")
    print("🚀" * 20)

    try:
        result = await agent_executor.ainvoke(input_data)
        return result

    finally:
        print(f"🏁 AGENT END  : {agent_name}\n")
        current_agent.reset(token_agent)
        current_task.reset(token_task)


# =========================
# 🔹 EXAMPLE USAGE
# =========================
async def main():

    tools = await load_tools(["sql", "search"])

    from langchain.agents import create_tool_calling_agent, AgentExecutor
    from langchain_core.prompts import ChatPromptTemplate

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant"),
        ("user", "{input}")
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

    result = await run_agent(
        agent_name="MainAgent",
        task="Find user data and search info",
        agent_executor=executor,
        input_data={"input": "Find user details from DB and latest news"}
    )

    print("\n✅ FINAL RESULT:\n", result)


if __name__ == "__main__":
    asyncio.run(main())