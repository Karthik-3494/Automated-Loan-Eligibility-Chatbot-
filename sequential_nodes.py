from datetime import date
from pathlib import Path
import re
import logger, validation_logic, kyc_logic, policy_logic, loan_logic, db_helper
from ollama_synthesis import synthesize_report
from docling_ocr import docling_ocr_extractor


def _log(state, msg):
    state.setdefault("log_messages", []).append(msg)
    logger.log(msg, state.get("request_id"))


def receive_node(state):
    _log(state, "Received loan eligibility request")
    state["validation_errors"] = validation_logic.validate(state)
    return state


def knockout_node(state):
    reasons = []
    if state.get("age", 0) < 21 or state.get("age", 0) > 60:
        reasons.append("Applicants must be 21–60 under the current criteria.")
    if state.get("residency") != "India":
        reasons.append("This service currently supports Indian residents only.")
    if state.get("monthly_income", 0) < 25000:
        reasons.append(
            "Monthly net income must be at least ₹25,000 under the current criteria."
        )
    state["knockout_reasons"] = reasons
    state["knockout_status"] = "fail" if reasons else "pass"
    _log(state, "Hard knockout: " + state["knockout_status"])
    return state


def financial_node(state):
    income = state.get("monthly_income", 0)
    state["existing_obligation_ratio"] = (
        state.get("monthly_obligations", 0) / income if income else None
    )
    state["credit_source"] = "user_stated"
    _log(
        state,
        "Financial profile and user-stated score recorded; no bureau pull performed",
    )
    return state


def kyc_node(state):
    outcome = kyc_logic.run(state)
    state["kyc_status"] = outcome["status"]
    state["kyc_errors"] = outcome["errors"]
    _log(state, "Applicant profile checks: " + state["kyc_status"])
    return state


def eligibility_node(state):
    state["offers"] = (
        []
        if state["knockout_status"] == "fail" or state["validation_errors"]
        else loan_logic.calculate(state)
    )
    eligible = [o for o in state["offers"] if o["eligible"]]
    state["primary_offer"] = (
        eligible[0] if eligible else (state["offers"][0] if state["offers"] else {})
    )
    requested = state.get("loan_type")
    if state.get("intent") == "specific":
        state["alternatives"] = []
    else:
        state["alternatives"] = eligible[1:3]
    if (
        state.get("intent") == "specific"
        and not eligible
        and requested in {"Personal Loan", "Auto Loan"}
    ):
        state["alternatives"] = [
            o
            for o in loan_logic.calculate({**state, "loan_type": "Home Loan"})
            if o["eligible"]
        ][:1]
    state["final_status"] = "needs_review" if not eligible else "indicative_match"
    _log(state, "Eligibility engine completed with deterministic eligibility rules")
    return state


def policy_node(state):
    state["policy_query"] = (
        "loan eligibility "
        + state.get("loan_type", "")
        + " credit income obligations documents alternatives"
    )
    state["evidence"] = policy_logic.retrieve_policies(state["policy_query"])
    state["policy_status"] = "found" if state["evidence"] else "insufficient_evidence"
    _log(state, "Policy evidence retrieved")
    return state


def report_node(state):
    state["final_report"] = {
        "status": state["final_status"],
        "primary_offer": state["primary_offer"],
        "alternatives": state["alternatives"],
        "reasons": state.get("knockout_reasons", [])
        + state.get("validation_errors", []),
        "evidence": [x["source_id"] for x in state["evidence"]],
    }
    state["final_report"]["summary"], state["synthesis_engine"] = synthesize_report(
        state["final_report"]
    )
    _log(state, "Result report generated with " + state["synthesis_engine"])
    db_helper.save_case(state)
    return state


def run_sequential(state):
    for node in (
        receive_node,
        knockout_node,
        financial_node,
        kyc_node,
        eligibility_node,
        policy_node,
        report_node,
    ):
        state = node(state)
    return state


def ocr_document(path):
    text, confidence, error = docling_ocr_extractor(path)
    fields = {}
    for key, pattern in {
        "monthly_income": r"(?:monthly income|net salary|net income)\s*[:₹ ]+([\d,]+)",
        "name": r"(?:name)\s*[:\-]\s*([^\r\n]+)",
    }.items():
        m = re.search(pattern, text, re.I)
        if m:
            fields[key] = (
                int(m.group(1).replace(",", ""))
                if key == "monthly_income"
                else m.group(1).strip()
            )
    return {"text": text, "confidence": confidence, "error": error, "fields": fields}
