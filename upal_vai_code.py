from dotenv import load_dotenv
import boto3
from botocore.client import Config
from livekit import agents, api
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    openai,
    deepgram,
    noise_cancellation,
    silero,
    google,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
# new imports
from typing import Any, Dict
from livekit.agents import function_tool, RunContext
import requests
import yaml  
import argparse
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env.justicenet'))

PROMPT_CONFIG = os.path.join(os.path.dirname(__file__), '../prompts/prompt_justicenet.yaml')


# Load configurations from the YAML file
with open(PROMPT_CONFIG, "r") as f:
    config = yaml.safe_load(f)
    system_prompt = config.get("system_prompt")
    greeting_instruction = config.get("greeting_instruction")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=system_prompt,
            # tools=[
            #     send_contact_info_goHighLevel,
            # ],
        )


async def entrypoint(ctx: agents.JobContext):

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="en-US"),
        llm=openai.LLM(model="gpt-4o-mini", temperature=0.3),
        tts=google.TTS(
            gender="female",
            voice_name="en-US-Chirp3-HD-Achernar"
        ),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
            
        ),
    )

    # --- Create bucket using room name ---
    bucket_name = ctx.room.name.lower().replace(" ", "-")
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.environ["E2_ACCESS_KEY"],
        aws_secret_access_key=os.environ["E2_SECRET_KEY"],
        region_name=os.environ["E2_REGION"],
        endpoint_url=os.environ["E2_ENDPOINT"],
        config=Config(signature_version="s3v4"),
    )

    # Create the bucket if it doesn't exist
    try:
        existing_buckets = s3.list_buckets()
        if bucket_name not in [b["Name"] for b in existing_buckets.get("Buckets", [])]:
            s3.create_bucket(Bucket=bucket_name)
            print(f"Bucket '{bucket_name}' created.")
        else:
            print(f" Bucket '{bucket_name}' already exists.")
    except Exception as e:
        print(f"Failed to create bucket '{bucket_name}': {e}")
        return

    # Set up recording
    req = api.RoomCompositeEgressRequest(
        room_name=ctx.room.name,
        audio_only=True,
        file_outputs=[
            api.EncodedFileOutput(
                file_type=api.EncodedFileType.MP4,
                filepath=f"{ctx.room.name}.mp4",
                s3=api.S3Upload(
                    bucket=bucket_name,
                    region=os.environ["E2_REGION"],
                    access_key=os.environ["E2_ACCESS_KEY"],
                    secret=os.environ["E2_SECRET_KEY"],
                    endpoint=os.environ["E2_ENDPOINT"],
                ),
            )
        ],
    )

    lkapi = api.LiveKitAPI()
    res = await lkapi.egress.start_room_composite_egress(req)

    if res.egress_id:
        print(f"Egress started with ID: {res.egress_id}")
    else:
        print("Failed to start egress")

    await ctx.connect()

    await session.generate_reply(
        instructions=greeting_instruction,
    )

    await lkapi.egress.stop_egress(
        api.StopEgressRequest(egress_id=res.egress_id)
    )

    await lkapi.aclose()

# if __name__ == "__main__":
#     agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))



# Add this before the entrypoint function
def parse_args():
    parser = argparse.ArgumentParser(description='LiveKit Agent')
    parser.add_argument('--port', type=int, default=8081, help='Port for debug interface')
    parser.add_argument('--ws-port', type=int, help='WebSocket port')
    return parser.parse_args()

# Modify the main section
if __name__ == "__main__":
    port = int(os.environ.get('AGENT_DEBUG_PORT', 8081))
    
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=entrypoint,
        port=port
    ))