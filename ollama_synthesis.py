import json

try:
    import ollama
except ImportError:
    ollama = None

MODEL_NAME = "qwen2.5:1.5b"


def synthesize_report(state):
    if ollama is None:
        raise RuntimeError("Install the Ollama Python package with pip install ollama")

    facts = {
        "status": state["deterministic_status"],
        "validation_status": state.get("validation_status"),
        "validation_issues": state.get("validation_errors", []),
        "kyc_status": state.get("kyc_status"),
        "kyc_issues": state.get("kyc_errors", []),
        "policy_status": state.get("policy_status"),
        "policy_sources": [item["source_id"] for item in state.get("evidence", [])],
    }
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You write the final summary for a synthetic document workflow. "
                    "Describe this case's outcome, not what a policy requires. "
                    "State validation and mock KYC results. Use only the supplied facts. "
                    "Do not change the given status or claim real identity verification. "
                    "Return a JSON object with one string field named summary."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Write one or two short sentences. Focus on the case result and mention "
                    "that it is a simulation. The status and check results are authoritative.\n"
                    + json.dumps(facts, ensure_ascii=False)
                ),
            },
        ],
        format="json",
        options={"temperature": 0, "num_ctx": 2048, "num_predict": 120},
    )
    content = response.message.content
    result = json.loads(content)
    summary = result.get("summary") if isinstance(result, dict) else None
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("Qwen returned no summary")
    return summary.strip()
