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
from langgraph.prebuilt import create_react_agent


# 1. Setup environment
load_dotenv()

# 2. Configuration & LLM Setup
# Using Groq/Qwen as specified in your setup
# llm = ChatOpenAI(
#     model="stepfun/step-3.5-flash:free",
#     base_url="https://openrouter.ai/api/v1",
#     temperature=0,  # Lower temperature is usually better for tool calling
#     api_key=os.getenv("OPENAI_API"),
# )

llm = ChatOpenAI(
    model="nvidia/nemotron-3-super-120b-a12b:free",
    base_url="https://openrouter.ai/api/v1", # Added /v1 for standard OpenAI compatibility
    api_key=os.getenv("OPENROUTER_API"),                    # Placeholder to prevent auth errors
    temperature=0,
   )


# 3. State Definition
class State(TypedDict):
    # add_messages ensures new messages are appended to the history
    messages: Annotated[list, add_messages]

async def main():
    # 4. Initialize MCP Client
    # This reads your tools.json and prepares the connections
    mcp_client = MultiServerMCPClient(
        json.load(open("new_tools.json"))
    )

    try:
        # Fetching tools from the Dockerized SQLite and Math servers
        tools = await mcp_client.get_tools(server_name=["math","research"])
        llm_with_tools = llm.bind_tools(tools)
        print(f"Successfully loaded {len(tools)} tools.")
    except Exception as e:
        print("Failed to load MCP tools:", e)
        return

    # 5. Node Definitions
    def chatbot(state: State):
        # We can add a system message here to guide the agent
        system_prompt = SystemMessage(
            content=("""You are a expert assistant that can answer questions about math and research. using the tools provided""")
        )
        # Combine system prompt with existing messages for the LLM
        response = llm_with_tools.invoke([system_prompt] + state["messages"])
        return {"messages": [response]}

    # 6. Graph Construction
    builder = StateGraph(State)

    builder.add_node("chatbot", chatbot)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "chatbot")
    builder.add_conditional_edges(
        "chatbot",
        tools_condition  # Routes to 'tools' if LLM wants to call a tool, otherwise to END
    )
    builder.add_edge("tools", "chatbot")

    # 7. Compile with Memory
    memory = MemorySaver()
    memory.delete_thread("1")
    graph = builder.compile(checkpointer=memory)

    # 8. Execution Loop
    config = {"configurable": {"thread_id": "1"}}
    
    print("\n--- Agentic Workstation Ready ---")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit", "q"]:
            break

        # CRITICAL FIX: Using ainvoke instead of invoke
        # This allows the MCP async tools to run correctly
        try:
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config
            )
            print(result)

            # Print the last message from the assistant
            
            # last_message = result["messages"][-1]
            # print(f"\nAssistant: {last_message.content}\n")
            
        except Exception as e:
            memory.delete_thread("1")

            print(f"\nAn error occurred during graph execution: {e}\n")
    

    # Cleanup MCP connections on exit
    # This ensures Docker containers are shut down properly
    await mcp_client.close()

if __name__ == "__main__":
    asyncio.run(main())