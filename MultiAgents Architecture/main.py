import asyncio
from agent_c import Agent, llm
from langgraph_supervisor import create_supervisor
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver

import os
import json
from agent_c import Agent


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

        # Load config
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Load prompt
        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read()

        # Create agent
        agent = Agent(
            config["name"],
            prompt,
            config["tools"]
        )

        await agent.setup()

        agents.append(agent)

    return agents


async def main():

    # Setup agents (load tools, etc.)
    system_prompt=""
    with open("systemprompt.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    subagents = await load_agents_from_directory("agents")    
    # Create supervisor workflow
    workflow = create_supervisor(
        subagents,
        model=llm,
        prompt=(str(system_prompt))   
    )  
 
    # Compile the workflow into an executable app
    memory = MemorySaver()
    memory.delete_thread("1")
    config = {"configurable": {"thread_id": "1"}}
    app = workflow.compile(checkpointer=memory)



    while True:
            user_input = input("User: ")
            if user_input.lower() in ["exit", "quit", "q"]:
                break

            # CRITICAL FIX: Using ainvoke instead of invoke
            # This allows the MCP async tools to run correctly
            try:
                result = await app.ainvoke(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=config
                )

                # Print the last message from the assistant
                last_message = result["messages"][-1]
                print(f"\nAssistant: {last_message.content}\n")
                
            except Exception as e:
                memory.delete_thread("1")

                print(f"\nAn error occurred during graph execution: {e}\n")
        

        # Cleanup MCP connections on exit
        # This ensures Docker containers are shut down properly





if __name__ == "__main__":
    asyncio.run(main())