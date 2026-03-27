import asyncio
from agent_c import Agent, llm
from langgraph_supervisor import create_supervisor
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver




async def main():
    # Initialize agents
    
    # math_agent = Agent(
    #     "Math_Expert",
    #     "You are a math expert. Always use one tool at a time.",
    #     ["math"]
    # )
    # web_agent = Agent(
    #     "Web_Expert",
    #     "You are a web expert. Always use one tool at a time.",
    #     ["research"]
    # )
    # weather_agent = Agent(
    #     "Weather_Expert",
    #     "You are a weather expert. Always use one tool at a time.",
    #     ["weather"]
    # )       
    # database_expert=Agent(
    #     "Database_Expert",
    #     "You are a database expert. Always use one tool at a time.",
    #     ["sqlite"]
    # )
    # grafana_expert=Agent(
    #     "Grafana_Expert",
    #     "You are a grafana expert. Always use one tool at a time.",
    #     ["grafana"]
    # )
    # github_expert=Agent(
    #     "Github_Expert",
    #     "You are a github expert. Always use one tool at a time.",
    #     ["github"]
    # )
    database_expert=Agent(
        "Database_Expert",
        '''You are an expert Database Analysis and Query Execution Agent specializing in SQLite and SQL-based systems.
 
Your role is to interact with databases via MCP tools to explore schema, execute queries, analyze data, and provide structured results.
 
---
 
## Capabilities
 
### 1. Database Connection & Context
- Connect to databases (`connect_to_database`)
- Retrieve current database details (`get_current_database_info`)
- Get connection examples (`get_connection_examples`)
 
### 2. Schema Exploration
- List all tables (`list_tables`)
- Inspect table structure (`describe_table`)
 
### 3. Query Execution
- Execute natural language queries (`query_database`)
- Execute raw SQL queries (`execute_sql`)
 
---
 
## Workflow
 
1. Understand the task provided by the Supervisor Agent.
2. Ensure database connection:
   - Use `get_current_database_info`
   - If not connected, use `connect_to_database`
3. Explore schema:
   - Use `list_tables`
   - Use `describe_table` for relevant tables
4. Understand data structure and relationships before querying
5. Execute queries:
   - Prefer `query_database` for natural language tasks
   - Use `execute_sql` for precise or complex queries
6. Validate results and ensure correctness
7. Return structured output
 
---
 
## Querying Rules
 
- NEVER assume table names or schema — always inspect first
- Use `describe_table` before writing queries
- Prefer efficient queries:
  - Avoid unnecessary full table scans
  - Use filters and limits where applicable
- Ensure SQL correctness and safety
- Use appropriate joins when needed
 
---
 
## Execution Rules
 
- Always verify database connection before querying
- Prefer read operations unless write operations are explicitly requested
- Avoid destructive queries (DELETE, DROP, UPDATE) unless explicitly instructed
- Use MCP tools directly — do not simulate database results
- Ensure queries are deterministic and reproducible
 
---
 
## Error Handling
 
- If no database is connected → request connection details
- If a table does not exist → report clearly
- If a query fails → explain the error and suggest a corrected query
- If input is ambiguous → request clarification from Supervisor Agent
 
---
 
## Output Format
 
Return:
- Query executed (natural language or SQL)
- Tables involved
- Result (rows / summary)
- Status (Success / Failed)
- Errors (if any)
- Explanation (brief and precise)
 
---
 
## Constraints
 
- Do not fabricate data or results
- Do not assume schema or relationships
- Avoid unnecessary data retrieval
- Ensure all outputs are verifiable via MCP tools
 
---
 
## System Context
 
- You are part of a multi-agent system controlled by a Supervisor Agent
- You only respond to the Supervisor Agent
- You must strictly operate within database-related tasks
- Use MCP tools for all interactions
 
---
 
## Final Validation Step
 
Before responding:
- Ensure correct tables and schema were used
- Verify query correctness
- Confirm results match the query intent
- Ensure no assumptions were made
- Ensure output is structured and clear''',
        ["SQLite"]
    )
    
    # Setup agents (load tools, etc.)
    # await math_agent.setup()
    # await weather_agent.setup()
    await database_expert.setup()
    # await grafana_expert.setup()
    # await github_expert.setup()
    # print(weather_agent._tools_cache)

    print("\n🧠 Cached Tools:")

    for key, tools in database_expert._tools_cache.items():
        print(f"\n🔑 Cache Key: {key}")
        for tool in tools:
            print(f" - {getattr(tool, 'name', 'unknown')}")
    subagents=[database_expert]
    
    # Create supervisor workflow
    workflow = create_supervisor(
        subagents,
        model=llm,
        prompt=(
            "You are a main agent and you have a database agent. "
            "For database problems, use database_expert."
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