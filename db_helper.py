from pathlib import Path
from contextlib import contextmanager
import sqlite3

DB = Path(__file__).resolve().parent / "data" / "loan_cases.db"


@contextmanager
def connect():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def init_db():
    with connect() as c:
        c.execute(
            "CREATE TABLE IF NOT EXISTS cases (request_id TEXT PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP, loan_type TEXT, status TEXT, payload_json TEXT)"
        )


def save_case(state):
    import json

    init_db()
    with connect() as c:
        c.execute(
            "INSERT OR REPLACE INTO cases(request_id,loan_type,status,payload_json) VALUES(?,?,?,?)",
            (
                state["request_id"],
                state.get("loan_type"),
                state.get("final_status"),
                json.dumps(state, ensure_ascii=False, default=str),
            ),
        )


def recent_cases(limit=20):
    init_db()
    with connect() as c:
        return [
            dict(r)
            for r in c.execute(
                "SELECT request_id,created_at,loan_type,status FROM cases ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        ]
