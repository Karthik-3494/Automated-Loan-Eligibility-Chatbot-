from pathlib import Path


def find_last_request_id(logs_folder=None):
    folder = Path(logs_folder or Path(__file__).resolve().parent / "logs")
    if not folder.exists():
        return None
    ids = []
    for path in folder.glob("*.jsonl"):
        try:
            ids.append(int(path.stem.split("-", 1)[0]))
        except ValueError:
            pass
    return str(max(ids)) if ids else None


def new_request_id(logs_folder=None):
    latest = find_last_request_id(logs_folder)
    return str(int(latest) + 1) if latest is not None else "0"
