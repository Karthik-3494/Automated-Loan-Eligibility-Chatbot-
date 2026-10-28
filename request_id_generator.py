from pathlib import Path


def correct_path_address(path) -> str | None:
    return str(path).replace("\\", "/") if path else None


def find_last_request_id(logs_folder=None) -> str | None:
    folder = Path(logs_folder) if logs_folder else Path("logs")
    if not folder.exists():
        return None
    ids = [int(path.stem) for path in folder.glob("*.log") if path.stem.isdigit()]
    return str(max(ids)) if ids else None


def new_request_id(logs_folder=None) -> str:
    latest = find_last_request_id(logs_folder)
    return str(int(latest) + 1) if latest is not None else "0"
