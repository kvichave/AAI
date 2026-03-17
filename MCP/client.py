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
    model="stepfun/step-3.5-flash:free",
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
        json.load(open("tools.json"))
    )

    try:
        # Fetching tools from the Dockerized SQLite and Math servers
        tools = await mcp_client.get_tools()
        llm_with_tools = llm.bind_tools(tools)
        print(f"Successfully loaded {len(tools)} tools.")
    except Exception as e:
        print("Failed to load MCP tools:", e)
        return

    # 5. Node Definitions
    def chatbot(state: State):
        # We can add a system message here to guide the agent
        system_prompt = SystemMessage(
            content=("""You are an expert Grafana dashboard engineer and data analyst.
 
Your job is to:
1. Inspect a SQLite database using the sqlite MCP tools to understand its schema and data.
2. Design and create a meaningful Grafana dashboard using the grafana MCP tools.
3. Add panels that are appropriate for the data (time-series, bar charts, stat panels, tables, etc.).
4. Return a summary of what was created.
 
## Workflow
1. Use `list_tables` / `describe_table` to explore the SQLite schema.
2. Run sample queries (`read_query`) to understand the data shape and ranges.
3. Use `search_datasources` to find the right Grafana data source (prefer the SQLite one).
4. Call  `update_dashboard` with a well-structured JSON payload.
5. Verify the dashboard exists with `get_dashboard`.
6. Report back with the dashboard URL and a brief description of every panel.

## Dashboard JSON tips
- Always set `"schemaVersion": 38` and `"version": 1`.
- For SQLite panels use `"type": "grafana-sqlite-datasource"` as the datasource type.
- Use sensible panel titles, descriptions, and units.
- Lay out panels in a 24-column grid; typical widths are 12 (half) or 24 (full).
- Use `"id": null` for new panels so Grafana auto-assigns IDs.
You are calling a Go-based MCP server. The 'dashboard' parameter must be a raw JSON object. Do not escape quotes, do not add newlines inside the string, and do not wrap the entire object in a string.

#SQLite Tools
- `query_database`: Execute natural language queries against the database and convert them to SQL.
- `list_tables`: List all available tables in the current database.
- `describe_table`: Get detailed schema information for a specific table including columns, types, and constraints.
- `execute_sql`: Execute raw SQL queries with safety checks and validation.
- `connect_to_database`: Connect to a new database using provided connection details.
- `get_connection_examples`: Get example connection strings for different database types (SQLite, PostgreSQL, MySQL).
- `get_current_database_info`: Get information about the currently connected database including type, version, and connection status.

# Grafana Tools
- `add_activity_to_incident`: Add activity to an incident.
- `alerting_manage_routing`: Manage alerting routing.
- `alerting_manage_rules`: Manage alert rules.
- `create_annotation`: Create an annotation.
- `create_folder`: Create a folder.
- `create_incident`: Create a new incident.
- `fetch_pyroscope_profile`: Fetch Pyroscope profiling data.
- `find_error_pattern_logs`: Find error patterns in logs.
- `find_slow_requests`: Find slow requests.
- `generate_deeplink`: Generate a navigation deeplink.
- `get_alert_group`: Get IRM alert group details.
- `get_annotation_tags`: Get annotation tags.
- `get_annotations`: Get annotations.
- `get_assertions`: Get assertions summary.
- `get_current_oncall_users`: Get currently on-call users.
- `get_dashboard_by_uid`: Get dashboard details by UID.
- `get_dashboard_panel_queries`: Get queries used in dashboard panels.
- `get_dashboard_property`: Get a specific dashboard property.
- `get_dashboard_summary`: Get dashboard summary.
- `get_datasource`: Get datasource details.
- `get_incident`: Get incident details.
- `get_oncall_shift`: Get OnCall shift details.
- `get_panel_image`: Get panel or dashboard image.
- `get_sift_analysis`: Get Sift analysis results.
- `get_sift_investigation`: Get Sift investigation details.
- `list_alert_groups`: List all IRM alert groups.
- `list_datasources`: List all datasources.
- `list_incidents`: List incidents.
- `list_loki_label_names`: List Loki label names.
- `list_loki_label_values`: List Loki label values.
- `list_oncall_schedules`: List OnCall schedules.
- `list_oncall_teams`: List OnCall teams.
- `list_oncall_users`: List OnCall users.
- `list_prometheus_label_names`: List Prometheus label names.
- `list_prometheus_label_values`: List Prometheus label values.
- `list_prometheus_metric_metadata`: List Prometheus metric metadata.
- `list_prometheus_metric_names`: List Prometheus metric names.
- `list_pyroscope_label_names`: List Pyroscope label names.
- `list_pyroscope_label_values`: List Pyroscope label values.
- `list_pyroscope_profile_types`: List Pyroscope profile types.
- `list_sift_investigations`: List Sift investigations.
- `query_loki_logs`: Query logs from Loki.
- `query_loki_patterns`: Query log patterns from Loki.
- `query_loki_stats`: Get Loki log statistics.
- `query_prometheus`: Query Prometheus metrics.
- `query_prometheus_histogram`: Query Prometheus histogram percentile.
- `search_dashboards`: Search dashboards.
- `search_folders`: Search folders.
- `update_annotation`: Update an annotation.
- `update_dashboard`: Update a dashboard.
Always think step-by-step before calling tools.
"""
        ))
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

            # Print the last message from the assistant
            last_message = result["messages"][-1]
            print(f"\nAssistant: {last_message.content}\n")
            
        except Exception as e:
            memory.delete_thread("1")

            print(f"\nAn error occurred during graph execution: {e}\n")
    

    # Cleanup MCP connections on exit
    # This ensures Docker containers are shut down properly
    await mcp_client.close()

if __name__ == "__main__":
    asyncio.run(main())