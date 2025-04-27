import os

from python_a2a import A2AServer, skill, agent, run_server, TaskStatus, TaskState, AgentCard
from dotenv import load_dotenv

load_dotenv()


@agent(
    name="DispatcherAgent",
    description="Dispatches",
    version="1.0.0"
)
class DispatcherAgent(A2AServer):

    @skill(
        name="Route task",
        description="Route a task to the appropriate agent",
        tags=["routing", "task management"]
    )
    def route(self, task):
        message_data = task.message or {}
        content = message_data.get("content", {})
        text = content.get("text", "") if isinstance(content, dict) else ""
        text = text.strip()
        if not text:
            task.status = TaskStatus(
                state=TaskState.INPUT_REQUIRED,
                message={"role": "agent", "content": {"type": "text",
                         "text": "Please provide a mathematical expression to calculate."}}
            )
            return task
        try:
            # Evaluate the expression
            result = self.calculate(text)
            task.artifacts = [{
                "parts": [{"type": "text", "text": result}]
            }]
            task.status = TaskStatus(state=TaskState.COMPLETED)

        except Exception as e:
            task.status = TaskStatus(
                state=TaskState.FAILED,
                message={"role": "agent", "content": {"type": "text",
                         "text": f"Error calculating expression: {str(e)}"}}
            )
        return task

    def handle_task(self, task):
        result = self.route(task)
        return result


# Run the server
if __name__ == "__main__":
    agent = DispatcherAgent()
    port = int(os.getenv("DISPATCHER_AGENT_PORT", "25001"))
    run_server(agent, port=port)
