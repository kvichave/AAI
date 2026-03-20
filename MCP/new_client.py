import asyncio
import json
import os
from typing import TypedDict, Annotated

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

# -------------------- SETUP --------------------
load_dotenv()

llm = ChatOpenAI(
    model="stepfun/step-3.5-flash:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API"),
    temperature=0,
)

# -------------------- STATE --------------------
class State(TypedDict):
    messages: Annotated[list, add_messages]
    next_agent: str  # supervisor decision

# -------------------- LOADERS --------------------
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
    skill_prompts = [load_skill_prompt(skill) for skill in skills]
    return agent_prompt + "\n\n" + "\n\n".join(skill_prompts)

# -------------------- SUPERVISOR NODE --------------------
def supervisor_node(state: State, agent_names):
    user_message = state["messages"][-1].content

    prompt = f"""
    You are a Supervisor AI.

    Agents available: {', '.join(agent_names)}

    Decide which agent should handle the task.

    Return ONLY one agent name from the list.
    """

    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=user_message)
    ])
    agent = response.content.strip()
    if agent not in agent_names:
        agent = agent_names[0]

    # Do not remove messages, propagate the original messages
    return {"next_agent": agent, "messages": state["messages"]}

# -------------------- AGENT NODE FACTORY --------------------
def create_agent_node(agent_name: str, tools):
    agent_prompt, skills = load_agent(agent_name)
    system_prompt = build_system_prompt(agent_prompt, skills)
    llm_with_tools = llm.bind_tools(tools)

    def agent_node(state: State):
        # Include supervisor + previous messages
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        # Append the agent's response to state messages
        state["messages"].append(response)
        return {"messages": state["messages"]}  # propagate updated messages

    return agent_node



# -------------------- MAIN --------------------
async def main():

    # MCP TOOLS
    mcp_client = MultiServerMCPClient(
        json.load(open("new_tools.json"))
    )
    tools = await mcp_client.get_tools()

    # ---------------- DISCOVER AGENTS ----------------
    agent_names = [name for name in os.listdir("agents") 
                   if os.path.isdir(os.path.join("agents", name))]

    print("Discovered Agents:", agent_names)

    # ---------------- BUILD GRAPH ----------------
    builder = StateGraph(State)

    # Supervisor Node
    builder.add_node("supervisor", lambda state: supervisor_node(state, agent_names))
    builder.add_edge(START, "supervisor")


    # Dynamic Agent Nodes
    for agent_name in agent_names:
        builder.add_node(agent_name, create_agent_node(agent_name, tools))
        # route each agent to tools
        builder.add_edge(agent_name, "tools")

    # Tools Node
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge("tools", END)

    # Supervisor → Conditional edges → agents dynamically
    builder.add_conditional_edges(
        "supervisor",
        lambda state: state["next_agent"],
        {agent: agent for agent in agent_names}
    )

    # Memory
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    print(graph.get_graph().draw_ascii())


    config = {"configurable": {"thread_id": "1"}}

    print("\n--- Supervisor Multi-Agent System (Dynamic) Ready ---\n")

    while True:
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config
        )

        print("\nAssistant:", result["messages"][-1].content, "\n")

    await mcp_client.close()

# ---------------- RUN ----------------
if __name__ == "__main__":
    asyncio.run(main())