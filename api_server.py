# api_server.py
import asyncio
import json
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import dweepbot modules
from dweepbot import AutonomousAgent, AgentConfig, create_registry_with_default_tools
from dweepbot.utils.deepseek_client import DeepSeekClient
from dweepbot.state.agent_state import AgentState
from dweepbot.utils.cost_tracker import CostTracker

# --- Data Models ---
class AgentTask(BaseModel):
    task: str
    max_cost: float = 5.0
    max_iterations: int = 50
    enable_web_search: bool = False
    enable_code_execution: bool = True

class AgentControl(BaseModel):
    action: str  # "start", "stop", "pause", "resume"
    agent_id: Optional[str] = None

class ToolConfig(BaseModel):
    enable_web_search: bool = True
    enable_code_execution: bool = True
    enable_shell_execution: bool = False

# --- State Management ---
class CommandCenterState:
    def __init__(self):
        self.active_agents: Dict[str, AutonomousAgent] = {}
        self.agent_states: Dict[str, AgentState] = {}
        self.cost_trackers: Dict[str, CostTracker] = {}
        self.websocket_connections: Dict[str, List[WebSocket]] = {}
        
    def add_agent(self, agent_id: str, agent: AutonomousAgent, state: AgentState, cost_tracker: CostTracker):
        self.active_agents[agent_id] = agent
        self.agent_states[agent_id] = state
        self.cost_trackers[agent_id] = cost_tracker
        self.websocket_connections[agent_id] = []
        
    def remove_agent(self, agent_id: str):
        if agent_id in self.active_agents:
            del self.active_agents[agent_id]
            del self.agent_states[agent_id]
            del self.cost_trackers[agent_id]
            if agent_id in self.websocket_connections:
                del self.websocket_connections[agent_id]

state = CommandCenterState()

# --- FastAPI App ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🦈 Shark Command Center API starting...")
    yield
    # Shutdown
    print("🦈 Shark Command Center API shutting down...")
    for agent_id in list(state.active_agents.keys()):
        await state.active_agents[agent_id].stop()
        state.remove_agent(agent_id)

app = FastAPI(lifespan=lifespan)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WebSocket for Real-Time Streams ---
@app.websocket("/ws/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    
    # Add connection to pool
    if agent_id not in state.websocket_connections:
        state.websocket_connections[agent_id] = []
    state.websocket_connections[agent_id].append(websocket)
    
    try:
        # Send initial state
        if agent_id in state.agent_states:
            initial_state = {
                "type": "state_sync",
                "agent_id": agent_id,
                "state": state.agent_states[agent_id].dict(),
                "cost": state.cost_trackers[agent_id].get_current_cost(),
                "tokens": state.cost_trackers[agent_id].get_token_counts()
            }
            await websocket.send_json(initial_state)
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Handle incoming commands from dashboard
            command = json.loads(data)
            await handle_websocket_command(agent_id, command, websocket)
            
    except WebSocketDisconnect:
        # Remove connection
        if agent_id in state.websocket_connections:
            state.websocket_connections[agent_id].remove(websocket)

async def broadcast_to_agent(agent_id: str, message: dict):
    """Broadcast message to all WebSocket connections for an agent"""
    if agent_id in state.websocket_connections:
        for connection in state.websocket_connections[agent_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Failed to send to WebSocket: {e}")

# --- REST Endpoints ---
@app.post("/api/agents/create")
async def create_agent(task: AgentTask):
    """Create and start a new agent"""
    agent_id = f"agent_{len(state.active_agents) + 1}"
    
    # Create configuration
    config = AgentConfig(
        deepseek_api_key="your-deepseek-api-key",  # Get from environment
        max_cost_usd=task.max_cost,
        max_iterations=task.max_iterations,
        enable_web_search=task.enable_web_search,
        enable_code_execution=task.enable_code_execution,
        workspace_path=f"./workspace/{agent_id}"
    )
    
    try:
        # Initialize components
        async with DeepSeekClient(api_key=config.deepseek_api_key) as llm:
            from dweepbot.tools import create_registry_with_default_tools
            from dweepbot.state.agent_state import AgentState
            from dweepbot.utils.cost_tracker import CostTracker
            
            # Create tool context
            from dweepbot.tools.base import ToolExecutionContext
            context = ToolExecutionContext(workspace_path=config.workspace_path)
            tools = create_registry_with_default_tools(context)
            
            # Create state and cost tracker
            agent_state = AgentState()
            cost_tracker = CostTracker()
            
            # Create agent
            agent = AutonomousAgent(config, llm, tools, state=agent_state, cost_tracker=cost_tracker)
            
            # Store in state
            state.add_agent(agent_id, agent, agent_state, cost_tracker)
            
            # Start agent in background
            asyncio.create_task(run_agent_stream(agent_id, agent, task.task))
            
            return {
                "success": True,
                "agent_id": agent_id,
                "message": f"Agent {agent_id} created and started"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")

async def run_agent_stream(agent_id: str, agent: AutonomousAgent, task: str):
    """Run agent and stream updates to WebSocket"""
    try:
        async for update in agent.run(task):
            # Stream update to dashboard
            message = {
                "type": "agent_update",
                "agent_id": agent_id,
                "update_type": update.type,
                "message": update.message,
                "data": update.data if hasattr(update, 'data') else {},
                "timestamp": update.timestamp.isoformat() if hasattr(update, 'timestamp') else None
            }
            
            # Add cost data if available
            if agent_id in state.cost_trackers:
                cost_tracker = state.cost_trackers[agent_id]
                message["cost"] = cost_tracker.get_current_cost()
                message["tokens"] = cost_tracker.get_token_counts()
                message["token_history"] = cost_tracker.get_token_history()[-20:]  # Last 20 points
            
            # Add tool execution data
            if hasattr(update, 'tool_call') and update.tool_call:
                message["tool"] = {
                    "name": update.tool_call.name,
                    "status": update.tool_call.status,
                    "execution_time": update.tool_call.execution_time_seconds
                }
            
            await broadcast_to_agent(agent_id, message)
            
            # Also update state
            if agent_id in state.agent_states:
                state.agent_states[agent_id] = agent.state
        
        # Agent completed
        completion_message = {
            "type": "agent_completed",
            "agent_id": agent_id,
            "success": True,
            "final_cost": state.cost_trackers[agent_id].get_current_cost() if agent_id in state.cost_trackers else 0
        }
        await broadcast_to_agent(agent_id, completion_message)
        
    except Exception as e:
        error_message = {
            "type": "agent_error",
            "agent_id": agent_id,
            "error": str(e)
        }
        await broadcast_to_agent(agent_id, error_message)
    finally:
        # Cleanup
        if agent_id in state.active_agents:
            state.remove_agent(agent_id)

@app.post("/api/agents/{agent_id}/control")
async def control_agent(agent_id: str, control: AgentControl):
    """Control an existing agent"""
    if agent_id not in state.active_agents:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    agent = state.active_agents[agent_id]
    
    if control.action == "stop":
        await agent.stop()
        state.remove_agent(agent_id)
        return {"success": True, "message": f"Agent {agent_id} stopped"}
    
    elif control.action == "pause":
        await agent.pause()
        return {"success": True, "message": f"Agent {agent_id} paused"}
    
    elif control.action == "resume":
        await agent.resume()
        return {"success": True, "message": f"Agent {agent_id} resumed"}
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {control.action}")

@app.get("/api/agents/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """Get current agent status"""
    if agent_id not in state.active_agents:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    agent_state = state.agent_states.get(agent_id, {})
    cost_tracker = state.cost_trackers.get(agent_id)
    
    return {
        "agent_id": agent_id,
        "status": agent_state.status if hasattr(agent_state, 'status') else "unknown",
        "current_task": agent_state.current_task if hasattr(agent_state, 'current_task') else None,
        "iteration": agent_state.iteration if hasattr(agent_state, 'iteration') else 0,
        "cost": cost_tracker.get_current_cost() if cost_tracker else 0,
        "tokens": cost_tracker.get_token_counts() if cost_tracker else {"input": 0, "output": 0},
        "tools_used": agent_state.tools_used if hasattr(agent_state, 'tools_used') else []
    }

@app.get("/api/system/info")
async def get_system_info():
    """Get system-wide information"""
    total_cost = sum(
        tracker.get_current_cost() 
        for tracker in state.cost_trackers.values()
    )
    
    total_tokens = {
        "input": sum(tracker.get_token_counts().get("input", 0) for tracker in state.cost_trackers.values()),
        "output": sum(tracker.get_token_counts().get("output", 0) for tracker in state.cost_trackers.values())
    }
    
    return {
        "active_agents": len(state.active_agents),
        "total_cost": total_cost,
        "total_tokens": total_tokens,
        "agents": list(state.active_agents.keys()),
        "uptime": "0s"  # You can implement actual uptime tracking
    }

@app.post("/api/tools/execute")
async def execute_tool(tool_request: dict):
    """Direct tool execution (for manual override)"""
    # This allows your dashboard's manual override to directly execute tools
    agent_id = tool_request.get("agent_id", "default")
    
    if agent_id not in state.active_agents:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    agent = state.active_agents[agent_id]
    tool_name = tool_request.get("tool_name")
    params = tool_request.get("parameters", {})
    
    try:
        # Execute tool through agent
        result = await agent.execute_tool(tool_name, **params)
        
        # Log the execution
        log_message = {
            "type": "manual_tool_execution",
            "agent_id": agent_id,
            "tool": tool_name,
            "result": result.success,
            "output": result.output[:500] if result.output else ""  # Truncate
        }
        await broadcast_to_agent(agent_id, log_message)
        
        return {
            "success": result.success,
            "output": result.output,
            "execution_time": result.execution_time_seconds
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")

async def handle_websocket_command(agent_id: str, command: dict, websocket: WebSocket):
    """Handle commands from WebSocket dashboard"""
    cmd_type = command.get("type")
    
    if cmd_type == "emergency_stop":
        if agent_id in state.active_agents:
            await state.active_agents[agent_id].stop()
            state.remove_agent(agent_id)
            await websocket.send_json({
                "type": "emergency_stop_confirmed",
                "agent_id": agent_id
            })
    
    elif cmd_type == "spawn_agent":
        # Parse spawn command from your dashboard
        agent_type = command.get("agent_type", "coder")
        task = command.get("task", f"Execute {agent_type} task")
        
        # Create new agent
        agent_task = AgentTask(
            task=task,
            enable_code_execution=True,
            enable_web_search=agent_type == "researcher"
        )
        
        # Call the create endpoint
        response = await create_agent(agent_task)
        await websocket.send_json({
            "type": "agent_spawned",
            "agent_id": response["agent_id"],
            "agent_type": agent_type
        })
    
    elif cmd_type == "override_control":
        # Manual override control
        control_action = command.get("action")
        if control_action == "inject_thought":
            # Inject a thought/instruction into agent's thinking
            thought = command.get("thought", "")
            if agent_id in state.active_agents:
                # This would require extending the agent with thought injection capability
                await state.active_agents[agent_id].inject_thought(thought)
                await websocket.send_json({
                    "type": "thought_injected",
                    "thought": thought[:100]  # Truncate
                })

if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
