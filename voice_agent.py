"""
LiveKit Voice Agent for Relatim Android App
============================================

Real-time AI voice agent using:
- Deepgram for Speech-to-Text (STT)
- Groq for LLM (fast inference with Llama)
- ElevenLabs for Text-to-Speech (TTS)

REQUIREMENTS:
- Python 3.10+
- livekit-agents>=1.3
- livekit-plugins-deepgram
- livekit-plugins-silero
- livekit-plugins-elevenlabs
- livekit-plugins-openai (for Groq compatibility)

RUNNING:
python voice_agent.py dev  # Development mode
python voice_agent.py start  # Production mode
"""

import os
import logging
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import (
    AgentSession,
    Agent,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.plugins import deepgram, silero, cartesia, groq

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("relatim-voice-agent")


# System prompt for the Relatim assistant
SYSTEM_PROMPT = """You are Relatim Voice Assistant, an AI helper for a field service management application.
Your role is to help users navigate and manage their service jobs through voice commands.

You can help users with:
1. Navigating to different job views (scheduled, reported, in progress, completed, billed)
2. Finding specific jobs or customers
3. Updating job statuses
4. Getting summaries of their workload
5. General questions about using the app

Keep your responses concise and conversational since this is a voice interface.
When the user wants to navigate, respond with confirmation and the action you're taking.

Available navigation commands you can suggest:
- "Show scheduled jobs" or "Show upcoming jobs"
- "Show reported jobs"
- "Show in progress jobs"
- "Show completed jobs"
- "Show billed jobs"
- "Show all jobs" or "Go to dashboard"

Be helpful, efficient, and professional."""


def prewarm(proc: agents.JobProcess):
    """Prewarm the agent process with necessary models"""
    # Load VAD (Voice Activity Detection) model
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("Agent prewarmed with VAD model")


class RelatimAssistant(Agent):
    """Relatim Voice Assistant - helps users manage service jobs via voice"""
    
    def __init__(self):
        super().__init__(
            instructions=SYSTEM_PROMPT
        )


async def entrypoint(ctx: JobContext):
    """Main entry point for the voice agent"""
    logger.info(f"Agent starting for room: {ctx.room.name}")
    
    # Wait for participant to connect
    await ctx.connect()
    
    # Create the agent session with STT-LLM-TTS pipeline
    session = AgentSession(
        stt=deepgram.STT(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            model="nova-2",
            language="en",
        ),
        llm=groq.LLM(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
        ),
        tts=cartesia.TTS(
            api_key=os.getenv("CARTESIA_API_KEY"),
        ),
        vad=silero.VAD.load(),
    )
    
    # Start the session
    await session.start(
        room=ctx.room,
        agent=RelatimAssistant(),
    )
    
    # Generate initial greeting
    await session.generate_reply(
        instructions="Greet the user warmly and ask how you can help them manage their service jobs today."
    )
    
    logger.info("Agent started and ready for conversation")


if __name__ == "__main__":
    # Run the agent with WorkerOptions that supports agent_name
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name="relatim-voice-agent",
        )
    )
