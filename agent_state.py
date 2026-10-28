from typing import TypedDict


class AgentState(TypedDict, total=False):
    request_id: str
    doc_type: str
    document_path: str
    extracted_text: str
    Name: str
    DOB: str
    ID_number: str
    ID_expiry: str
    extracted_fields: dict
    ocr_confidence: float | None
    validation_errors: list[str]
    validation_status: str
    kyc_status: str
    kyc_errors: list[str]
    policy_query: str
    policy_status: str
    evidence: list[dict]
    final_status: str
    final_report: str
    synthesis_status: str
    synthesis_error: str
    log_messages: list[str]
