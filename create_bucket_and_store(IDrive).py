from dotenv import load_dotenv
import asyncio
from datetime import datetime
import json
import boto3
from botocore.client import Config
import logging
import os

from livekit import agents, api
from livekit.agents import AgentSession, Agent, RoomInputOptions, metrics, MetricsCollectedEvent
from livekit.plugins import (
    openai,
    cartesia,
    deepgram,
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv()
logger = logging.getLogger()


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You are a helpful voice AI assistant.")


async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=cartesia.TTS(model="sonic-2", voice="f786b574-daa5-4673-aa0c-cbe3e8534c02"),
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
            print(f"✅ Bucket '{bucket_name}' created.")
        else:
            print(f"ℹ️ Bucket '{bucket_name}' already exists.")
    except Exception as e:
        print(f"❌ Failed to create bucket '{bucket_name}': {e}")
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
        print(f"✅ Egress started with ID: {res.egress_id}")
    else:
        print("❌ Failed to start egress")

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    await ctx.connect()

    await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )

    await asyncio.sleep(5)

    await lkapi.egress.stop_egress(
        api.StopEgressRequest(egress_id=res.egress_id)
    )

    await lkapi.aclose()
    ctx.add_shutdown_callback(log_usage)


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))