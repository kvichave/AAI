import os
import importlib.util
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from typing import TypedDict, Annotated
from langchain_core.messages import HumanMessage
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
load_dotenv()

from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()



llm = ChatOpenAI(
    model="qwen/qwen3-32b",
    base_url="https://api.groq.com/openai/v1",
    temperature=0.7,
    api_key=os.getenv("GROQ_API_KEY"),
)

def chatbot(state: State):

    response = llm.invoke(state["messages"])

    return {"messages": [response]}

async def main():
    mcp_client = MultiServerMCPClient(
        json.load(open("tools.json"))
    )
    
    

    
    try:
        tools = await mcp_client.get_tools()
    except Exception as e:
        print("Failed to load MCP tools:", e)
        return

    
    # agent=create_agent(llm,tools)
    # weather_response=await agent.ainvoke({"messages":[{"role":"user","content":"what is "}]})
    # print(weather_response["messages"][-1].content)


asyncio.run(main())