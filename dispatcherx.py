import os
import json
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from google.adk.agent import Agent, AgentContext, AgentResponse
from google.adk.type.card import Card, CardHeader, CardSection, CardSectionItem

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class AgentInfo(BaseModel):
    """Model to store information about registered agents"""
    name: str
    description: str
    capabilities: List[str]
    card: Card


class DispatcherAgent(Agent):
    """
    Dispatcher Agent that routes requests to appropriate registered agents
    """

    def __init__(self):
        super().__init__()
        # Dictionary to store registered agents
        self.registered_agents: Dict[str, AgentInfo] = {}

    def register_agent(self, agent_name: str, description: str, capabilities: List[str], card: Card) -> bool:
        """
        Register a new agent with the dispatcher

        Args:
            agent_name: Name of the agent
            description: Description of what the agent does
            capabilities: List of capabilities the agent provides
            card: Agent's card information

        Returns:
            bool: True if registration was successful
        """
        if agent_name in self.registered_agents:
            print(
                f"Agent {agent_name} is already registered. Updating information.")

        self.registered_agents[agent_name] = AgentInfo(
            name=agent_name,
            description=description,
            capabilities=capabilities,
            card=card
        )

        print(
            f"Agent {agent_name} registered successfully with capabilities: {capabilities}")
        return True

    def find_suitable_agents(self, user_request: str) -> List[str]:
        """
        Use LLM to determine which registered agents can handle the user request

        Args:
            user_request: The user's request in natural language

        Returns:
            List of agent names that can handle the request
        """
        if not self.registered_agents:
            return []

        # Prepare agent information for the prompt
        agent_info = []
        for name, info in self.registered_agents.items():
            agent_info.append({
                "name": name,
                "description": info.description,
                "capabilities": info.capabilities
            })

        # Create a prompt for the LLM
        prompt = f"""
        You are a dispatcher that routes user requests to the appropriate agent.
        
        Available agents:
        {json.dumps(agent_info, indent=2)}
        
        User request: "{user_request}"
        
        Based on the user request and the available agents, determine which agent(s) can handle this request.
        If no agent can handle this request, return an empty list.
        If multiple agents can handle this request, return all suitable agents.
        
        Return your response as a JSON array of agent names, e.g., ["agent1", "agent2"].
        """

        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        # Parse the response
        try:
            content = response.choices[0].message.content
            result = json.loads(content)
            return result.get("agents", [])
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return []

    def handle(self, context: AgentContext) -> AgentResponse:
        """
        Handle incoming requests by routing to appropriate agent

        Args:
            context: The agent context containing the user's request

        Returns:
            AgentResponse: The response to send back to the user
        """
        # Get the user's request
        user_request = context.request.text

        # Find suitable agents
        suitable_agents = self.find_suitable_agents(user_request)

        # No suitable agents found
        if not suitable_agents:
            return AgentResponse(text="No agent to do this task is found.")

        # One suitable agent found
        if len(suitable_agents) == 1:
            agent_name = suitable_agents[0]
            agent_info = self.registered_agents[agent_name]
            return AgentResponse(
                text=f"Your request will be handled by {agent_name}.",
                card=agent_info.card
            )

        # Multiple suitable agents found
        agent_options = "\n".join([f"- {name}: {self.registered_agents[name].description}"
                                  for name in suitable_agents])

        return AgentResponse(
            text=f"Multiple agents can handle your request. Please choose one:\n\n{agent_options}"
        )


# Create the dispatcher agent
dispatcher = DispatcherAgent()

# Define the request body model for agent registration


class AgentRegistrationRequest(BaseModel):
    name: str
    description: str
    capabilities: List[str]
    card: Dict[str, Any]


# Create a FastAPI app
app = FastAPI(title="A2A Dispatcher API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)


@app.post("/register")
async def register(data: AgentRegistrationRequest):
    """
    Endpoint for agents to register with the dispatcher
    """
    try:
        # Extract agent information from request
        agent_name = data.name
        description = data.description
        capabilities = data.capabilities
        card_data = data.card

        # Convert card data to Card object
        header = CardHeader(
            title=card_data.get('header', {}).get('title', agent_name),
            subtitle=card_data.get('header', {}).get('subtitle', description)
        )

        sections = []
        for section_data in card_data.get('sections', []):
            items = [
                CardSectionItem(title=item.get('title', ''))
                for item in section_data.get('items', [])
            ]
            sections.append(CardSection(
                header=section_data.get('header', ''),
                items=items
            ))

        card = Card(header=header, sections=sections)

        # Register the agent
        success = dispatcher.register_agent(
            agent_name=agent_name,
            description=description,
            capabilities=capabilities,
            card=card
        )

        if success:
            return {"status": "success", "message": f"Agent {agent_name} registered successfully"}
        else:
            raise HTTPException(
                status_code=400, detail="Failed to register agent")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Start the agent and FastAPI app with Uvicorn
if __name__ == "__main__":
    port = int(os.getenv("PORT", "25001"))
    api_port = port + 1

    # Start the agent in a separate thread
    import threading
    agent_thread = threading.Thread(
        target=dispatcher.start, kwargs={"port": port})
    agent_thread.daemon = True
    agent_thread.start()

    # Start the FastAPI app with Uvicorn
    print(f"Dispatcher agent is running on port {port}")
    f"Registration endpoint available at http://localhost:{port}/register")
    app.run(host='0.0.0.0', port=port+1)
