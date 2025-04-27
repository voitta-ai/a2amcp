import os

from python_a2a import Task,  Message, A2AServer, skill, agent, run_server, TaskStatus, TaskState, AgentCard
from dotenv import load_dotenv

load_dotenv()


@agent(
    name="MathAgent",
    description="Simple math",
    version="1.0.0"
)
class MathAgent(A2AServer):

    @skill(
        name="Calculate expression",
        description="Calculate a mathematical expression",
        tags=["math", "calculation"]
    )
    def calculate(self, expr):
        result = eval(expr)
        return str(result)

    def handle_message(self, message: Message):
        return super().handle_message(message)

    def handle_task(self, task: Task):
        print(task.to_json())
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


# Run the server
if __name__ == "__main__":
    agent = MathAgent()
    port = int(os.getenv("MATH_AGENT_PORT", "25002"))
    run_server(agent, port=port)
