import json
import os


def synthesize_report(report):
    """Optional local Ollama narration. The supplied deterministic result remains authoritative."""
    if os.getenv("LOANGUIDE_USE_OLLAMA", "0") != "1":
        return deterministic_summary(report), "deterministic_fallback"
    try:
        import ollama

        facts = {
            "status": report["status"],
            "product": (report.get("primary_offer") or {}).get("product"),
            "eligible": (report.get("primary_offer") or {}).get("eligible"),
            "max_amount": (report.get("primary_offer") or {}).get("max_amount"),
            "reasons": report.get("reasons", []),
        }
        response = ollama.chat(
            model=os.getenv("LOANGUIDE_MODEL", "qwen2.5:1.5b"),
            messages=[
                {
                    "role": "system",
                    "content": "Summarize this loan eligibility result in one or two short sentences. Use only supplied facts. Do not claim approval, pre-qualification, bureau verification, or real lender action. Return JSON with one string field named summary.",
                },
                {"role": "user", "content": json.dumps(facts, ensure_ascii=False)},
            ],
            format="json",
            options={"temperature": 0, "num_predict": 100},
        )
        parsed = json.loads(response.message.content)
        summary = parsed.get("summary") if isinstance(parsed, dict) else None
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("Missing summary")
        return summary.strip(), "ollama"
    except Exception:
        return deterministic_summary(report), "deterministic_fallback"


def deterministic_summary(report):
    offer = report.get("primary_offer") or {}
    if offer.get("eligible"):
        return f"The current eligibility criteria show an indicative match for {offer['product']} up to ₹{offer['max_amount']:,.0f}. A lender must verify details and make any real decision."
    return "No matching offer was found under the current eligibility criteria. Review the listed factors or consider a suitable alternative; this is not a lender decision."
