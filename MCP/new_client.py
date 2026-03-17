import asyncio
import json
import os
from typing import TypedDict, Annotated

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

# -------------------- 1. Setup --------------------
load_dotenv()

llm = ChatOpenAI(
    model="stepfun/step-3.5-flash:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API"),
    temperature=0,
)

# -------------------- 2. State --------------------
class State(TypedDict):
    messages: Annotated[list, add_messages]

# -------------------- 3. Agent + Skill Loaders --------------------

def load_agent(agent_name: str):
    base_path = f"agents/{agent_name}"

    with open(os.path.join(base_path, "prompt.md")) as f:
        agent_prompt = f.read()

    with open(os.path.join(base_path, "skills.json")) as f:
        skills = json.load(f)["skills"]

    return agent_prompt, skills


def load_skill_prompt(skill_name: str):
    path = f"skills/{skill_name}/skill.md"
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return ""


def build_system_prompt(agent_prompt: str, skills: list):
    skill_prompts = [
        load_skill_prompt(skill)
        for skill in skills
    ]
    return agent_prompt + "\n\n" + "\n\n".join(skill_prompts)


# -------------------- 4. MAIN --------------------

async def main():

    # 🔹 Load Agent
    agent_name = "research_agent"   # change dynamically later
    agent_prompt, active_skills = load_agent(agent_name)
    final_system_prompt = build_system_prompt(agent_prompt, active_skills)

    print(f"Loaded Agent: {agent_name}")
    print(f"Active Skills: {active_skills}")

    # 🔹 MCP Client
    mcp_client = MultiServerMCPClient(
        json.load(open("tools.json"))
    )

    try:
        tools = await mcp_client.get_tools()
        llm_with_tools = llm.bind_tools(tools)
        print(f"Loaded {len(tools)} MCP tools.")
    except Exception as e:
        print("Failed to load MCP tools:", e)
        return

    # -------------------- 5. Nodes --------------------

    def chatbot(state: State):
        system_message = SystemMessage(content=final_system_prompt)

        response = llm_with_tools.invoke(
            [system_message] + state["messages"]
        )

        return {"messages": [response]}

    # -------------------- 6. Graph --------------------

    builder = StateGraph(State)

    builder.add_node("chatbot", chatbot)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "chatbot")

    builder.add_conditional_edges(
        "chatbot",
        tools_condition
    )

    builder.add_edge("tools", "chatbot")

    # -------------------- 7. Memory --------------------

    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)

    config = {"configurable": {"thread_id": "1"}}

    print("\n--- Agentic Workstation Ready ---")
    print("Type 'exit' to quit.\n")

    # -------------------- 8. Loop --------------------

    while True:
        user_input = input("User: ")

        if user_input.lower() in ["exit", "quit", "q"]:
            break

        try:
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config
            )

            last_message = result["messages"][-1]
            print(f"\nAssistant: {last_message.content}\n")

        except Exception as e:
            print(f"\nError: {e}\n")

    await mcp_client.close()


# -------------------- RUN --------------------
if __name__ == "__main__":
    asyncio.run(main())