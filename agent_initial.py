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
            # LiveKit Cloud enhanced noise cancellation
            # - If self-hosting, omit this parameter
            # - For telephony applications, use `BVCTelephony` for best results
            noise_cancellation=noise_cancellation.BVC(), 
        ),
    )
     # Set up recording
    req = api.RoomCompositeEgressRequest(
        room_name=ctx.room.name,
        audio_only=True,
        file_outputs=[api.EncodedFileOutput(
            file_type=api.EncodedFileType.MP4,
            filepath=f"{ctx.room.name}.mp4",
            s3=api.S3Upload(
                bucket=os.environ["E2_BUCKET"],
                region=os.environ["E2_REGION"],
                access_key=os.environ["E2_ACCESS_KEY"],
                secret=os.environ["E2_SECRET_KEY"],
                endpoint=os.environ["E2_ENDPOINT"],
            ),
        )],
    )

    lkapi = api.LiveKitAPI()
    res = await lkapi.egress.start_room_composite_egress(req)
    # Check if egress started successfully
    if res.egress_id:
        print(f"Egress started with ID: {res.egress_id}")
    else:
        print("not egress")
   
    # # ranscript Config
    # async def write_transcript():
    #     current_date = datetime.now().strftime("%Y%m%d_%H%M%S")

    #     filename = f"/tmp/transcript_{ctx.room.name}_{current_date}.json"
    #     s3_key = f"transcripts/{ctx.room.name}/transcript_{current_date}.json"

        
    #     with open(filename, 'w') as f:
    #         json.dump(session.history.to_dict(), f, indent=2)
            
    #     print(f"Transcript for {ctx.room.name} saved to {filename}")

    #     s3 = boto3.client(
    #         "s3",
    #         aws_access_key_id="VyIg0cmo7HAMwnYvCrnp",
    #         aws_secret_access_key="EnjpLkFa1TL00Ylevj6H7SgPCmc1Rwi6Lc8kC73H",
    #         region_name="LA",
    #         endpoint_url="https://u5r0.la1.idrivee2-97.com",
    #         config=Config(signature_version="s3v4"),
    #     )

    #     try:
    #         s3.upload_file(filename, "transcripts", s3_key)
    #         print(f"Transcript uploaded to {s3_key}")
    #     except Exception as e:
    #         print(f"Failed to upload transcript: {e}")

    #for session cost
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

    # Optional timeout stop (e.g., after 30 seconds)
    await asyncio.sleep(5)

  # Proper way to stop
    await lkapi.egress.stop_egress(
        api.StopEgressRequest(egress_id=res.egress_id)
    )

    await lkapi.aclose()
    ctx.add_shutdown_callback(log_usage)



if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))