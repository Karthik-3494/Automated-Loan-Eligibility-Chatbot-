import re
from pathlib import Path

import logger
from docling_ocr import docling_ocr_extractor
from kyc_logic import KYCCheck
from policy_logic import retrieve_policies
from ollama_synthesis import synthesize_report
from request_id_generator import new_request_id
from validation_logic import validators

FIELD_PATTERNS = {
    "Name": r"(?:^|[\r\n])\s*(?:full\s+)?name\s*[:\-]\s*([^\r\n]+)",
    "DOB": r"(?:dob|date\s+of\s+birth)\s*[:\-]\s*(\d{4}-\d{2}-\d{2})",
    "ID_number": r"(?:id|document|licen[cs]e)\s*(?:number|no\.?|#)\s*[:\-]?\s*([A-Z0-9-]+)",
    "ID_expiry": r"(?:id\s+)?(?:expiry|expires|valid\s+until|date\s+of\s+expiry)\s*[:\-]\s*(\d{4}-\d{2}-\d{2})",
}


def _append_log(state, message):
    return [*state.get("log_messages", []), message]


def _parse_fields(text):
    fields = {}
    for field, pattern in FIELD_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            fields[field] = match.group(1).strip()
    return fields


def receive_node(state):
    path = str(Path(state["document_path"]).resolve())
    return {
        "request_id": state.get("request_id") or new_request_id(),
        "document_path": path,
        "doc_type": Path(path).suffix.lstrip(".").upper(),
        "log_messages": _append_log(state, "Received document data"),
    }


def ocr_node(state):
    text, confidence = docling_ocr_extractor(state["document_path"])
    fields = _parse_fields(text or "")
    return {
        "extracted_text": text or "",
        "extracted_fields": fields,
        **fields,
        "ocr_confidence": confidence,
        "log_messages": _append_log(
            state,
            "Extracted data and confidence using Docling OCR" if text else "Docling OCR failed",
        ),
    }


def validation_node(state):
    errors = validators(state["request_id"]).run_all_checks(state)
    status = "pass" if not errors else "needs_review"
    messages = _append_log(state, "Validation result: " + status)
    if errors:
        messages.append("Validation issues: " + ", ".join(errors))
    return {
        "validation_errors": errors,
        "validation_status": status,
        "log_messages": messages,
    }


def kyc_node(state):
    checked = KYCCheck(state["request_id"]).run(dict(state))
    messages = _append_log(state, "KYC result: " + checked["kyc_status"])
    if checked["kyc_errors"]:
        messages.append("KYC issues: " + ", ".join(checked["kyc_errors"]))
    return {
        "kyc_status": checked["kyc_status"],
        "kyc_errors": checked["kyc_errors"],
        "log_messages": messages,
    }


def _policy_query(state):
    errors = state.get("validation_errors", [])
    parts = []
    missing = [field for field in ["Name", "DOB", "ID_number", "ID_expiry"] if not state.get(field)]
    if missing:
        parts.extend(["required fields", *missing])
    elif state.get("validation_status") == "pass":
        parts.extend(["required fields", "name", "dob", "id number"])

    if "ocr_confidence" in errors:
        parts.extend(["ocr confidence", "low confidence", "manual review"])
    if "Document has expired" in errors:
        parts.extend(["expired document", "expired identity"])
    if any("mismatch" in error.casefold() for error in state.get("kyc_errors", [])):
        parts.extend(["identity mismatch", "name mismatch", "dob mismatch"])
    elif state.get("kyc_status") != "match":
        parts.extend(["inconclusive verification", *state.get("kyc_errors", [])])

    if not parts:
        parts.extend(error.replace("_", " ") for error in errors)
    return " ".join(parts)


def policy_node(state):
    query = _policy_query(state)
    evidence = retrieve_policies(query)
    status = "found" if evidence else "insufficient_evidence"
    message = "Policy evidence retrieved" if evidence else "No relevant policy evidence found"
    if evidence:
        message += ": " + ", ".join(item["source_id"] for item in evidence)
    return {
        "policy_query": query,
        "policy_status": status,
        "evidence": evidence,
        "log_messages": _append_log(state, message),
    }


def synthesis_node(state):
    status = (
        "verified_in_simulation"
        if state.get("validation_status") == "pass"
        and state.get("kyc_status") == "match"
        and state.get("policy_status") == "found"
        else "needs_review"
    )
    try:
        summary = synthesize_report({**state, "deterministic_status": status})
        synthesis_status = "completed"
        synthesis_error = ""
        synthesis_message = "Qwen synthesis completed"
    except Exception as error:
        status = "failed"
        summary = "Qwen synthesis failed. Check that Ollama and the selected model are available."
        synthesis_status = "failed"
        synthesis_error = str(error)
        synthesis_message = "Qwen synthesis failed: " + str(error)

    messages = [*state.get("log_messages", []), synthesis_message, "Final status: " + status]
    logger.log("\n".join(messages), state["request_id"])
    return {
        "final_status": status,
        "final_report": summary,
        "synthesis_status": synthesis_status,
        "synthesis_error": synthesis_error,
        "log_messages": messages,
    }


