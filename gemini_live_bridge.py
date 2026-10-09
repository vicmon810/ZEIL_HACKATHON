"""Local Gemini Live microphone bridge. Keep GEMINI_API_KEY server-side."""
import asyncio
import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
import websockets

load_dotenv()
MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")
DECL = {
    "name": "navigate_page",
    "description": "Switch the recruitment dashboard to the user's requested section. Always call for navigation requests.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "page": {
                "type": "STRING",
                "enum": ["overview", "anomalies", "investigation"],
                "description": "Destination page"
            }
        },
        "required": ["page"]
    },
}

SCROLL_DECL = {
    "name": "scroll_page",
    "description": (
        "Scroll the currently visible recruitment dashboard vertically. "
        "Use for scroll down, scroll up, go to top, or go to bottom commands."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "direction": {
                "type": "STRING",
                "enum": ["up", "down", "top", "bottom"],
            },
            "amount": {
                "type": "INTEGER",
                "description": "Distance in pixels for up/down. Default 500, max 1200.",
            },
        },
        "required": ["direction"],
    },
}

DATASET_DECL = {
    "name": "load_csv_dataset",
    "description": (
        "Load one of three pre-approved local demo recruitment CSV datasets. "
        "Use only when the user asks to load, import, select, or switch CSV data. "
        "Never construct arbitrary local file paths."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "dataset": {
                "type": "STRING",
                "enum": ["bottleneck", "normal", "small_sample"],
                "description": "bottleneck=screening bottleneck; normal=healthy funnel; small_sample=tiny dataset",
            }
        },
        "required": ["dataset"],
    },
}


INVESTIGATE_DECL = {
    "name": "start_investigation",
    "description": (
        "Start or run the recruitment investigation with the existing Gemini "
        "analytics agent. Use when asked to start, run, or investigate "
        "recruitment data. Do not call for simple navigation requests."
    ),
    "parameters": {"type": "OBJECT", "properties": {}},
}

async def handler(socket):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        await socket.send(json.dumps({"type": "error", "message": "GEMINI_API_KEY missing"}))
        return
    client = genai.Client(api_key=key)
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=(
            "You control a recruitment analytics dashboard. For instructions to show, "
            "open, go to, or navigate to overview, anomalies/bottlenecks, or AI investigation, "
            "call navigate_page immediately. Interpret conversational wording. "
            "When asked to scroll up or down, or go to the top or bottom of the current page, "
            "call scroll_page. For a little scrolling, use 250 pixels; ordinary scroll 500; "
            "a lot 900. Never use scroll_page for navigation to a different page. "
            "For requests to load, upload, open, or switch the demo CSV, call load_csv_dataset: "
            "bottleneck for screening bottleneck, normal for healthy funnel, "
            "small_sample for small sample. Do not invent file paths or upload files. "
            "When the user asks to start or run the recruitment investigation, call "
            "start_investigation. Do not confuse opening the investigation page "
            "with running a new investigation. Do not invent other destinations. Be brief."
        ),
        tools=[{"function_declarations": [DECL, SCROLL_DECL, DATASET_DECL, INVESTIGATE_DECL]}],
    )
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            await socket.send(json.dumps({"type": "ready", "model": MODEL}))
            async def upload_audio():
                async for message in socket:
                    if isinstance(message, bytes):
                        await session.send_realtime_input(
                            audio=types.Blob(data=message, mime_type="audio/pcm;rate=16000")
                        )
                    elif message == "END_AUDIO":
                        await session.send_realtime_input(audio_stream_end=True)

            async def receive_tools():
                while True:
                    async for response in session.receive():
                        if response.tool_call:
                            responses = []
                            for call in response.tool_call.function_calls:
                                page = (call.args or {}).get("page")
                                if call.name == "navigate_page" and page in (
                                    "overview", "anomalies", "investigation"
                                ):
                                    await socket.send(json.dumps({"type": "navigate", "page": page}))
                                    result = {"status": "navigating", "page": page}
                                elif call.name == "load_csv_dataset":
                                    dataset = (call.args or {}).get("dataset")
                                    if dataset in ("bottleneck", "normal", "small_sample"):
                                        await socket.send(json.dumps({
                                            "type": "dataset", "dataset": dataset,
                                        }))
                                        result = {"status": "dataset_requested", "dataset": dataset}
                                    else:
                                        result = {"error": "Unknown dataset. Choose bottleneck, normal, or small_sample."}
                                elif call.name == "start_investigation":
                                    await socket.send(json.dumps({"type": "investigate"}))
                                    result = {"status": "investigation_requested"}
                                elif call.name == "scroll_page":
                                    args = call.args or {}
                                    direction = args.get("direction")
                                    if direction in ("up", "down", "top", "bottom"):
                                        try:
                                            amount = int(args.get("amount", 500))
                                        except (ValueError, TypeError):
                                            amount = 500
                                        amount = max(100, min(amount, 1200))
                                        await socket.send(json.dumps({
                                            "type": "scroll",
                                            "direction": direction,
                                            "amount": amount,
                                        }))
                                        result = {"status": "scrolling", "direction": direction, "amount": amount}
                                    else:
                                        result = {"error": "invalid direction"}
                                else:
                                    result = {"error": "not supported"}
                                responses.append(types.FunctionResponse(
                                    id=call.id, name=call.name, response=result
                                ))
                            await session.send_tool_response(function_responses=responses)
            tasks = [asyncio.create_task(upload_audio()), asyncio.create_task(receive_tools())]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            for task in done:
                if not task.cancelled():
                    error = task.exception()
                    if error:
                        raise error
    except Exception as exc:
        try:
            await socket.send(json.dumps({"type": "error", "message": str(exc)[:300]}))
        except Exception:
            pass
    finally:
        client.close()

async def main():
    async with websockets.serve(handler, "127.0.0.1", 8766, max_size=2**21):
        print(f"Gemini Live bridge listening at ws://127.0.0.1:8766 ({MODEL})", flush=True)
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
