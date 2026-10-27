
from dotenv import load_dotenv
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langchain_core.messages import HumanMessage

from src.agent import agent

load_dotenv()

langfuse = get_client()
langfuse_handler = CallbackHandler()

question = "How many orders are in the database?"

print("Running agent with Langfuse tracing...")

result = agent.invoke(
    {
        "messages": [
            HumanMessage(content=question)
        ]
    },
    config={
        "configurable": {
            "thread_id": "langfuse-test-001"
        },
        "callbacks": [langfuse_handler],
        "recursion_limit": 20,
    },
)

print("\n=== AGENT RESPONSE ===")
print(result["messages"][-1].content)

langfuse.flush()

print("\nLangfuse tracing completed.")
