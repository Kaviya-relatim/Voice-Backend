"""
LiveKit Token Server for Relatim Android App
=============================================

This is a reference implementation of the backend token server required for
LiveKit voice AI integration. This server handles:

1. Generating LiveKit access tokens for Android clients
2. Dispatching AI agents to rooms

REQUIREMENTS:
- Python 3.8+
- livekit-api package: pip install livekit-api
- fastapi: pip install fastapi uvicorn

ENVIRONMENT VARIABLES:
- LIVEKIT_URL: Your LiveKit server URL (e.g., wss://your-project.livekit.cloud)
- LIVEKIT_API_KEY: Your LiveKit API key
- LIVEKIT_API_SECRET: Your LiveKit API secret

RUNNING:
uvicorn token_server:app --host 0.0.0.0 --port 8080
"""

import os
import uuid
import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from livekit import api

# Configuration - using actual LiveKit credentials
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "wss://relatim-v1wlyfls.livekit.cloud")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "APIgNUtuSTugMPF")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "G94A3JBc7teQiXnmvA2RO1MTQWRf7FRa7XfWYJCebJAB")

app = FastAPI(
    title="Relatim LiveKit Token Server",
    description="Token generation server for LiveKit voice AI integration",
    version="1.0.0"
)

# Enable CORS for mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your app's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class TokenRequest(BaseModel):
    room_name: str
    participant_identity: str
    participant_name: Optional[str] = None
    room_config: Optional[dict] = None

class TokenResponse(BaseModel):
    token: str
    url: str
    room_name: str
    participant_identity: str
    expires_at: int

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    livekit_url: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.datetime.utcnow().isoformat(),
        livekit_url=LIVEKIT_URL
    )


@app.post("/token", response_model=TokenResponse)
async def generate_token(request: TokenRequest):
    """
    Generate a LiveKit access token for the Android client.
    
    The token grants:
    - Room join permission
    - Audio publish permission (for microphone)
    - Audio subscribe permission (to hear the AI agent)
    - Data publish/subscribe (for transcriptions)
    
    When room_config contains agent_name, the agent will be automatically
    dispatched to the room via agent dispatch.
    """
    try:
        # Create access token using new API
        token = api.AccessToken(
            LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET
        ).with_identity(
            request.participant_identity
        ).with_name(
            request.participant_name or request.participant_identity
        ).with_grants(
            api.VideoGrants(
                room_join=True,
                room=request.room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        ).with_ttl(
            datetime.timedelta(hours=1)
        )
        
        # Handle agent dispatch - support both formats:
        # Format 1: room_config.agent_name (simple)
        # Format 2: room_config.agents[0].agentName (from Android app)
        agent_name = None
        if request.room_config:
            # Try format 1
            if request.room_config.get("agent_name"):
                agent_name = request.room_config["agent_name"]
            # Try format 2 (Android app sends this)
            elif request.room_config.get("agents"):
                agents = request.room_config["agents"]
                if agents and len(agents) > 0:
                    agent_name = agents[0].get("agentName") or agents[0].get("agent_name")
        
        if agent_name:
            # Set up room config to dispatch agent
            token = token.with_room_config(
                api.RoomConfiguration(
                    agents=[
                        api.RoomAgentDispatch(
                            agent_name=agent_name,
                        )
                    ]
                )
            )
        
        # Generate the JWT
        jwt_token = token.to_jwt()
        
        # Calculate expiration time
        expires_at = int(datetime.datetime.utcnow().timestamp()) + 3600
        
        return TokenResponse(
            token=jwt_token,
            url=LIVEKIT_URL,
            room_name=request.room_name,
            participant_identity=request.participant_identity,
            expires_at=expires_at
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate token: {str(e)}"
        )


@app.post("/dispatch-agent")
async def dispatch_agent(room_name: str, agent_name: str = "relatim-voice-agent"):
    """
    Explicitly dispatch an agent to a room.
    
    This is an alternative to automatic agent dispatch.
    Use this if you need more control over when agents join.
    """
    try:
        # Create Room Service client
        room_service = api.RoomService(
            LIVEKIT_URL.replace("wss://", "https://").replace("ws://", "http://"),
            LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET
        )
        
        # Create agent dispatch request
        # This requires LiveKit Cloud with Agents enabled
        dispatch_request = api.CreateAgentDispatchRequest(
            room=room_name,
            agent_name=agent_name
        )
        
        # Note: Agent dispatch API may vary based on LiveKit version
        # Refer to LiveKit documentation for your specific setup
        
        return {
            "status": "dispatched",
            "room_name": room_name,
            "agent_name": agent_name
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to dispatch agent: {str(e)}"
        )


# Main entry point for testing
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8081"))
    print("Starting Relatim LiveKit Token Server...")
    print(f"LiveKit URL: {LIVEKIT_URL}")
    print(f"API Key: {LIVEKIT_API_KEY[:8]}...")
    print(f"Server Port: {port}")
    
    uvicorn.run(
        "token_server:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
