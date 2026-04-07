import asyncio
import os
import json
import time

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from deepagents import create_deep_agent
from agent_c2 import load_tools, llm

# =========================
# 🔹 LOAD AGENTS
# =========================
async def load_agents_from_directory(base_path="agents"):
    agents = []
    if not os.path.exists(base_path):
        print(f"❌ Error: {base_path} directory not found.")
        return agents

    for folder in os.listdir(base_path):
        agent_path = os.path.join(base_path, folder)
        if not os.path.isdir(agent_path): continue

        config_file = os.path.join(agent_path, "config.json")
        prompt_file = os.path.join(agent_path, "prompt.md")

        if os.path.exists(config_file) and os.path.exists(prompt_file):
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt = f.read()

            # Pass the tool list from config to the tool loader
            tools = await load_tools(config["tools"])
            
            agents.append({
                "name": config["name"],
                "description": config["description"],
                "tools": tools,
                "system_prompt": f"You are agent: {config['name']}\n\n{prompt}"
            })
    return agents





# =========================
# 🔹 MAIN EXECUTION LOOP
# =========================



async def main():
    # Load the Supervisor's system prompt
    with open("systemprompt.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    subagents = await load_agents_from_directory("agents")
      # Cache the loaded agents for tool access
    print(f"\n✅ Fleet Initialized: {len(subagents)} agents ready.")
    memory = MemorySaver()
    workflow = create_deep_agent(
        subagents=subagents,
        model=llm,
        system_prompt=system_prompt,
        checkpointer=memory
    )
    app = workflow
    # ✅ NEW: Export graph as PNG
    try:
        png_bytes = app.get_graph().draw_mermaid_png()
        with open("deep_agent_graph.png", "wb") as f:
            f.write(png_bytes)
        print("📊 Graph saved as deep_agent_graph.png")

    except Exception as e:
        print("⚠️ PNG export failed, saving Mermaid instead:", e)

        mermaid_code = app.get_graph().draw_mermaid()
        with open("deep_agent_graph.mmd", "w") as f:
            f.write(mermaid_code)

        print("📄 Mermaid file saved as deep_agent_graph.mmd")

    # 🛠️ CONFIG: Increase recursion limit slightly, but we monitor for loops
    config = {
        "configurable": {"thread_id": "session_001"},
        "recursion_limit": 200 
    }

    while True:
        user_input = input("\nUser: ")
        if user_input.lower() in ["exit", "q", "quit"]: break

        try:
            print("\n" + "="*80 + "\n🚀 STARTING TASK\n" + "="*80)
            start_perf = time.perf_counter()

            # Stream events to catch every agent and tool transition
            async for event in workflow.astream_events(
                {"messages": [HumanMessage(content=user_input)]},
                config=config,
                version="v2"
            ):
                kind = event["event"]
                name = event["name"]

                # 🧠 Detect when an Agent (LLM) starts a new reasoning turn
                if kind == "on_chat_model_start":
                    print(f"\n[AGENT: {name}] 🧠 Thinking...")

                # 🛠️ Detect when a Tool is called by an agent
                elif kind == "on_tool_start":
                    inputs = event['data'].get('input', {})
                    print(f"    └── 🛠️  TOOL: {name}")
                    print(f"        📝 ARGS: {json.dumps(inputs)}")
                    
                    # 🚦 THROTTLE: Physically prevent 20k RPM spikes
                    await asyncio.sleep(0.5)

                elif kind == "on_tool_end":
                    print(f"    └── ✅ COMPLETED: {name}")

            # Fetch the final output from the thread state
            final_state = await workflow.aget_state(config)
            print("\n" + "—"*40 + "\n🤖 FINAL RESPONSE:\n")
            print(final_state.values["messages"][-1].content)
            
            elapsed = time.perf_counter() - start_perf
            print(f"\n⏱️ Total Execution Time: {round(elapsed, 2)}s\n" + "="*80)

        except Exception as e:
            print(f"\n❌ CRITICAL ERROR: {e}")
            # If a recursion limit is hit, delete the thread to stop the loop
            memory.delete_thread("session_001")
            print("⚠️ Thread cleared to prevent persistent looping.")

if __name__ == "__main__":
    asyncio.run(main())