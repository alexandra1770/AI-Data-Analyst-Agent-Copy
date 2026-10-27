
from dotenv import load_dotenv
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langchain_core.messages import HumanMessage

from src.agent import agent


def main():
    # Incarca variabilele din .env
    load_dotenv()

    # Initializeaza Langfuse
    langfuse = get_client()
    langfuse_handler = CallbackHandler()

    # Intrebare de test
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

    # Trimite evenimentele ramase catre Langfuse
    langfuse.flush()

    print("\nLangfuse tracing completed.")


if __name__ == "__main__":
    main()
