import asyncio
from agent_c2 import Agent, llm
from langgraph_supervisor import create_supervisor
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
import os
import json
from deepagents import create_deep_agent





async def load_agents_from_directory(base_path="agents"):
    agents = []

    for folder in os.listdir(base_path):
        agent_path = os.path.join(base_path, folder)

        if not os.path.isdir(agent_path):
            continue

        config_file = os.path.join(agent_path, "config.json")
        prompt_file = os.path.join(agent_path, "prompt.md")

        if not os.path.exists(config_file) or not os.path.exists(prompt_file):
            continue

        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read()

        agent = Agent(
            config["name"],
            prompt,
            config["tools"]
        )

        await agent.setup()
        agents.append(agent)

    return agents


async def main():
    with open("systemprompt.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    subagents = await load_agents_from_directory("agents")

    workflow = create_deep_agent(
        subagents=subagents,
        model=llm,
        system_prompt=system_prompt
    )

    memory = MemorySaver()
    memory.delete_thread("1")

    config = {"configurable": {"thread_id": "1"}}
    app = workflow.compile(checkpointer=memory)

    while True:
        user_input = input("\nUser: ")
        if user_input.lower() in ["exit", "quit", "q"]:
            break

        try:
            result = await app.ainvoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config
            )

            print("\nAssistant:", result["messages"][-1].content)

        except Exception as e:
            memory.delete_thread("1")
            print(f"\n❌ ERROR: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())