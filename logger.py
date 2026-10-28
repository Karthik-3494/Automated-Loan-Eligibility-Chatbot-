from pathlib import Path
from datetime import datetime, timezone
import json

ROOT = Path(__file__).resolve().parent


def log(message, request_id=None):
    folder = ROOT / "logs"
    folder.mkdir(exist_ok=True)
    path = folder / (f"{request_id}.jsonl" if request_id else "general.jsonl")
    with path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "time": datetime.now(timezone.utc).isoformat(),
                    "request_id": request_id,
                    "message": message,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
