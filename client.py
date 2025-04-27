import os
import asyncio
from dotenv import load_dotenv

from python_a2a import A2AClient, Message, TextContent, MessageRole
from python_a2a import Task, TaskStatus, TaskState
from python_a2a.models.conversation import Conversation

load_dotenv()

# Create a custom implementation of StreamingClient that implements the required abstract method


async def main():
    # Use 25002 which matches the actual port in .env
    agent_port = os.getenv("MATH_AGENT_PORT", "25002")
    client = A2AClient(
        f"http://localhost:{agent_port}", google_a2a_compatible=True)
    print(
        f"Agent at {client.endpoint_url} has skills: {client.agent_card.skills}")
    question = "2+2"
    print(f"Question: {question}")
    answer = client.ask(question)
    print(f"Answer: {answer}")
    print("\n" + "-" * 50)


if __name__ == "__main__":
    asyncio.run(main())
