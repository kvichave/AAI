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



class State(TypedDict):
    messages: Annotated[list, add_messages]


skills_dir = "skills"

tools = []
skills_prompt = ""

for skill_name in os.listdir(skills_dir):

    skill_path = os.path.join(skills_dir, skill_name)

    md_path = os.path.join(skill_path, "skill.md")
    tool_path = os.path.join(skill_path, "tool.py")

    if os.path.exists(md_path) and os.path.exists(tool_path):

        with open(md_path) as f:
            description = f.read()

        spec = importlib.util.spec_from_file_location(
            skill_name, tool_path
        )

        module = importlib.util.module_from_spec(spec)

        spec.loader.exec_module(module)

        tools.append(
            Tool(
                name=skill_name,
                func=module.run,
                description=description
            )
        )




llm = ChatOpenAI(
    model="openai/gpt-oss-120b", 
    base_url="https://api.groq.com/openai/v1",
    temperature=0.7,
    api_key=os.getenv("GROQ_API_KEY"),
)

llm_with_tools = llm.bind_tools(tools)


def chatbot(state: State):

    response = llm_with_tools.invoke(state["messages"])

    return {"messages": [response]}



builder = StateGraph(State)

builder.add_node("chatbot", chatbot)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "chatbot")

builder.add_conditional_edges(
    "chatbot",
    tools_condition
)

builder.add_edge("tools", "chatbot")

graph = builder.compile(checkpointer=memory)
config={"configurable":{"thread_id":"1"}}


while True:

    query = input("User: ")

    result = graph.invoke(
        {"messages": [HumanMessage(content=query)]},
        config=config
    )

    print(result["messages"][-1].content)
    print(result)






