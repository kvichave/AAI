import asyncio
import json
from langchain_mcp_adapters.client import MultiServerMCPClient

async def main():
    # Load config
    with open("new_tools.json", "r") as f:
        config = json.load(f)

    # Initialize client
    client = MultiServerMCPClient(config)

    print("🔌 Connecting to MCP...\n")

    try:
        # ✅ Correct method (no arguments)
        tools = await client.get_tools()

        print(f"✅ Total tools found: {len(tools)}\n")

        for i, tool in enumerate(tools, 1):
            name = getattr(tool, "name", str(tool))
            print(f"{i}. {name}")

    except Exception as e:
        print("❌ Error:")
        print(e)

if __name__ == "__main__":
    asyncio.run(main())