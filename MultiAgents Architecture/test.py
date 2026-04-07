import asyncio
import json
from langchain_mcp_adapters.client import MultiServerMCPClient

async def main():
    mcp_client = MultiServerMCPClient(
        json.load(open("new_tools.json"))
    )

    li = ["math", "research"]

    tool_lists = await asyncio.gather(
        *[mcp_client.get_tools(server_name=name) for name in li]
    )

    # Flatten list
    mcptools = [tool for sublist in tool_lists for tool in sublist]

    # Print tools
    for tool in mcptools:
        print(tool.name)



if __name__ == "__main__":
    asyncio.run(main())