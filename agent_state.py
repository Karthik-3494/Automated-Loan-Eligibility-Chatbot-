from typing import TypedDict, Any


class AgentState(TypedDict, total=False):
    request_id: str
    messages: list[dict]
    intent: str
    loan_type: str
    residency: str
    age: int
    employment_type: str
    employment_months: int
    monthly_income: float
    monthly_obligations: float
    credit_score: int
    requested_amount: float
    tenure_months: int
    document_path: str
    extracted_text: str
    extracted_fields: dict
    validation_errors: list[str]
    validation_status: str
    knockout_status: str
    knockout_reasons: list[str]
    kyc_status: str
    kyc_errors: list[str]
    policy_query: str
    policy_status: str
    evidence: list[dict]
    offers: list[dict]
    primary_offer: dict
    alternatives: list[dict]
    final_status: str
    final_report: dict
    log_messages: list[str]
    synthesis_engine: str
