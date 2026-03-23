import asyncio
from agent_c import Agent, llm
from langgraph_supervisor import create_supervisor
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver




async def main():
    # Initialize agents
    
    math_agent = Agent(
        "Math_Expert",
        "You are a math expert. Always use one tool at a time.",
        ["math"]
    )
    web_agent = Agent(
        "Web_Expert",
        "You are a web expert. Always use one tool at a time.",
        ["research"]
    )
    database_expert=Agent(
        "Database_Expert",
        "You are a database expert. Always use one tool at a time.",
        ["sqlite"]
    )
    grafana_expert=Agent(
        "Grafana_Expert",
        "You are a grafana expert. Always use one tool at a time.",
        ["grafana"]
    )
    github_expert=Agent(
        "Github_Expert",
        "You are a github expert. Always use one tool at a time.",
        ["github"]
    )
    
    # Setup agents (load tools, etc.)
    await math_agent.setup()
    await web_agent.setup()
    await database_expert.setup()
    await grafana_expert.setup()
    await github_expert.setup()
    subagents=[math_agent,web_agent,database_expert,grafana_expert,github_expert]
    
    # Create supervisor workflow
    workflow = create_supervisor(
        subagents,
        model=llm,
        prompt=(
            "You are a team supervisor managing a research expert and a math expert,database expert,grafana expert,github expert. "
            "For current events, use web_agent. "
            "For math problems, use math_agent."
            "For database problems, use database_expert."
            "For grafana problems, use grafana_expert."
            "For github problems, use github_expert."
        )
    )

    # Compile the workflow into an executable app
    memory = MemorySaver()
    memory.delete_thread("1")
    config = {"configurable": {"thread_id": "1"}}
    app = workflow.compile(checkpointer=memory)

    # --- INVOKE QUERY ---
    # query = "what is 2+2? and give me a sone line news on latest news on AI use websearch"
    # response = await app.ainvoke({"messages":[{"role":"user","content":query}]})  # pass simple string

    # --- HANDLE RESPONSE ---
    # Check the type of response and print final content safely
    # print(response["messages"][-1].content)





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