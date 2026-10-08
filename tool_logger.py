
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "tool_calls.jsonl"


def save_tool_log(tool_log: list[dict]) -> str | None:
    """Persist one investigation's tool calls as JSONL."""

    if not tool_log:
        return None

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    investigation_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    with LOG_FILE.open("a", encoding="utf-8") as file:
        for step, entry in enumerate(tool_log, start=1):
            record = {
                "timestamp": timestamp,
                "investigation_id": investigation_id,
                "step": step,
                "tool": entry["tool"],
                "arguments": entry["arguments"],
                "result": entry["result"],
            }

            file.write(
                json.dumps(record, ensure_ascii=False) + "\n"+"="*50
            )

    return investigation_id
