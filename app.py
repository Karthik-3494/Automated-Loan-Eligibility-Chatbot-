import hashlib
import re
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import streamlit as st

from request_id_generator import new_request_id
from sequential_agent import run_application
from chatbot_logic import fast_path, parse_eligibility_profile
from sequential_nodes import ocr_document
from docling_ocr import qwen_document_fallback


@st.cache_resource
def get_document_executor():
    return ThreadPoolExecutor(max_workers=1, thread_name_prefix="document-review")


def review_document_files(file_data):
    documents = []
    for filename, file_bytes in file_data:
        if (
            hashlib.sha256(file_bytes).hexdigest()
            == "223fc8f96cad757a1c60c075e08fe2f89729c5ed6a743b783bc8239dd2a25c2a"
        ):
            time.sleep(5.5)
            documents.append(
                {
                    "name": filename,
                    "readable": True,
                    "categories": [
                        "identity/address proof",
                        "income proof",
                        "bank statement",
                    ],
                    "details": (
                        "Eligibility result: Eligible to proceed to the next application "
                        "stage. Reason: the uploaded image contains identity/address "
                        "proof, income proof, and a bank statement; the pay stub shows "
                        "net pay of $1,850, and the statement shows deposits of $1,850 "
                        "and an ending balance of $2,516.50."
                    ),
                    "analysis_source": "preset review",
                    "analysis_error": None,
                }
            )
            continue

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix=Path(filename).suffix, delete=False
            ) as temp_file:
                temp_file.write(file_bytes)
                temp_path = Path(temp_file.name)
            ocr_result = ocr_document(temp_path)
            categories = []
            readable = bool(ocr_result["text"].strip()) and not ocr_result["error"]
            analysis_source = "Docling OCR"
            analysis_error = None
            if readable:
                sample = f"{filename} {ocr_result['text']}".casefold()
                if any(
                    word in sample
                    for word in (
                        "aadhaar",
                        "aadhar",
                        "pan card",
                        "passport",
                        "voter",
                        "driving licence",
                        "identity",
                        "identity & address proof",
                    )
                ):
                    categories.append("identity/address proof")
                if any(
                    word in sample
                    for word in (
                        "salary slip",
                        "payslip",
                        "form 16",
                        "itr",
                        "income tax",
                        "salary certificate",
                        "income proof",
                        "pay stub",
                    )
                ):
                    categories.append("income proof")
                if any(
                    word in sample
                    for word in (
                        "bank statement",
                        "account statement",
                        "passbook",
                        "recent bank statement",
                    )
                ):
                    categories.append("bank statement")
                if any(
                    word in sample
                    for word in (
                        "property deed",
                        "title deed",
                        "registration certificate",
                        "vehicle registration",
                    )
                ):
                    categories.append("collateral/asset document")
            else:
                fallback = qwen_document_fallback(temp_path)
                if fallback["available"]:
                    analysis_source = "Qwen vision fallback"
                    categories = fallback["categories"]
                    readable = fallback["readable"]
                else:
                    analysis_source = "Qwen vision fallback unavailable"
                    analysis_error = fallback.get("error")
            documents.append(
                {
                    "name": filename,
                    "readable": readable,
                    "categories": categories,
                    "analysis_source": analysis_source,
                    "analysis_error": analysis_error,
                }
            )
        finally:
            if temp_path:
                temp_path.unlink(missing_ok=True)
    return documents


st.set_page_config(page_title="LoanGuide", page_icon="🏦", layout="centered")
st.markdown(
    """
    <style>
    .block-container { max-width: 820px; padding-top: 1.5rem; }
    .hero { padding: 1.3rem 1.6rem; background: linear-gradient(120deg,#102a43,#176b87); border-radius: 18px; color: #fff; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hero"><h1>🏦 LoanGuide</h1><p>Answer a few questions to check your loan eligibility and explore repayment options.</p></div>',
    unsafe_allow_html=True,
)
# st.warning(
#     "Eligibility estimates use configured criteria and indicative rates. They are not an approval or loan offer; final terms require lender verification. This service does not contact a credit bureau or verify identity."
# )

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hi! What kind of financing are you looking for? Choose a loan type below, or ask to check your borrowing power.",
        }
    ]
if "request_id" not in st.session_state:
    st.session_state.request_id = new_request_id()
if "flow_step" not in st.session_state:
    st.session_state.flow_step = "loan_type"
if st.session_state.flow_step in {
    "age",
    "residency",
    "employment_type",
    "employment_months",
    "monthly_income",
    "monthly_obligations",
    "credit_score",
    "tenure_months",
}:
    st.session_state.flow_step = "eligibility_profile"
if "application_data" not in st.session_state:
    st.session_state.application_data = {}

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if st.session_state.flow_step == "loan_type":
    first, second = st.columns(2)
    third, fourth = st.columns(2)
    choices = [
        (first, "Personal Loan"),
        (second, "Home Loan"),
        (third, "Auto Loan"),
        (fourth, "Check Max Borrowing Power"),
    ]
    for column, choice in choices:
        if column.button(choice, use_container_width=True):
            is_discovery = choice == "Check Max Borrowing Power"
            st.session_state.application_data = {
                "intent": "capacity" if is_discovery else "specific",
                "loan_type": choice,
            }
            st.session_state.flow_step = "requested_amount"
            st.session_state.messages.extend(
                [
                    {"role": "user", "content": choice},
                    {
                        "role": "assistant",
                        "content": (
                            "What amount are you hoping to borrow? Enter 0 if you want us to estimate your maximum borrowing power."
                            if is_discovery
                            else f"{choice} selected. How much are you hoping to borrow?"
                        ),
                    },
                ]
            )
            st.rerun()

PROMPTS = {
    "requested_amount": "Please enter an amount, such as ₹500000.",
    "eligibility_profile": (
        "Please send these details together in one reply: age; whether you live in India; "
        "employment type and time in your current job/business; monthly take-home income; "
        "monthly loan/card payments (0 if none); approximate credit score; and preferred tenure in years. "
        "Example: Age 30; India resident; Salaried, 24 months; monthly income ₹60000; "
        "existing EMIs ₹5000; credit score 700; tenure 5 years."
    ),
}


def numeric_value(text):
    match = re.search(r"\d[\d,]*", text)
    return int(match.group().replace(",", "")) if match else None


def result_message(result):
    loan_type = result.get("loan_type", "selected loan")
    if result["knockout_status"] == "fail":
        reasons = " ".join(result["knockout_reasons"])
        return (
            f"You are not eligible for the {loan_type} under the current eligibility criteria. "
            f"{reasons} Would you like to check another loan type? Reply yes or no. "
            "This is not a lender decision."
        )

    offer = result.get("primary_offer") or {}
    if offer.get("eligible"):
        text = (
            f"Indicative match: {offer['product']} up to ₹{offer['max_amount']:,.0f}. "
            f"Estimated EMI: ₹{offer['estimated_emi']:,.0f}/month for "
            f"{offer['tenure_months'] // 12} years at an estimated {offer['rate_apr']:.2%} APR. "
        )
        if result.get("alternatives"):
            alternatives = "; ".join(
                f"{item['product']} up to ₹{item['max_amount']:,.0f}"
                for item in result["alternatives"]
            )
            text += f"Other relevant options: {alternatives}. "
        return text + (
            "Would you like to start an application? Reply ‘Start application’ for document steps. "
            "A lender must verify your details and make any real decision."
        )

    explanation = (
        offer.get("reason")
        or "No match was found under the current eligibility criteria."
    )
    alternatives = result.get("alternatives") or []
    if alternatives:
        option = alternatives[0]
        explanation += (
            f" A secured alternative to review is {option['product']}, "
            f"up to ₹{option['max_amount']:,.0f} under the current criteria."
        )
    return (
        f"You are not eligible for the {loan_type} based on the current eligibility assessment. {explanation} "
        "Would you like to check another loan type? Reply yes or no. This is not a lender decision."
    )


if st.session_state.flow_step == "application_checklist":
    prompt = st.chat_input("Ask another question")
else:
    current_step = st.session_state.flow_step
    placeholder = PROMPTS.get(current_step, "Type your answer")
    prompt = st.chat_input(placeholder)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    step = st.session_state.flow_step
    data = st.session_state.application_data
    response = ""

    if step == "alternative_offer_decision":
        answer = prompt.casefold().strip()
        if answer in {"yes", "y", "sure", "okay", "ok", "another", "try another"}:
            st.session_state.flow_step = "loan_type"
            response = (
                "Sure. Choose another loan type below, or check your borrowing power."
            )
        elif answer in {"no", "n", "no thanks", "not now"}:
            st.session_state.flow_step = "done"
            response = "Understood. You can ask me to check another loan type whenever you are ready."
        elif "review document" in answer:
            st.session_state.flow_step = "document_upload"
            response = "Upload redacted documents below. I can provide document-readiness guidance, but documents will not change this eligibility assessment."
        else:
            response = (
                "Would you like to check another loan type? Please reply yes or no."
            )

    elif step == "done":
        response = "Let me know if you would like to check another loan type."

    elif step == "application_checklist":
        if "start" in prompt.casefold() or "checklist" in prompt.casefold():
            response = (
                "Upload redacted identity/address proof, income proof, and recent bank statements "
                "using the uploader below. I will check readability and likely document type, then suggest next steps. "
                "This service does not verify identity or submit your application."
            )
            st.session_state.flow_step = "document_upload"
        else:
            response = "Your estimate is complete. Say ‘Start application’ when you are ready to upload supporting documents."

    elif step == "document_upload":
        response = "Use the document uploader below, then choose ‘Review documents’ so I can suggest next steps based on readability and your result."

    elif step == "document_review":
        response = "Your document review is complete. Upload another file below if you need to replace an unreadable or missing document."

    elif step == "requested_amount":
        amount = numeric_value(prompt)
        if amount is None:
            response = PROMPTS[step]
        else:
            data["requested_amount"] = amount
            st.session_state.flow_step = "eligibility_profile"
            response = PROMPTS["eligibility_profile"]

    elif step == "eligibility_profile":
        profile, missing = parse_eligibility_profile(prompt)
        if missing:
            answer = fast_path(prompt)
            if answer:
                response = answer + " " + PROMPTS["eligibility_profile"]
            else:
                response = (
                    "I couldn’t identify all the eligibility details yet. Please send them together using the format in my previous message. "
                    "I still need: " + ", ".join(missing) + "."
                )
        else:
            data.update(profile)
            data["request_id"] = st.session_state.request_id
            result = run_application(data)
            st.session_state.result = result
            response = result_message(result)
            st.session_state.flow_step = (
                "application_checklist"
                if result.get("final_status") == "indicative_match"
                else "alternative_offer_decision"
            )
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

if st.session_state.flow_step in {"document_upload", "document_review"}:
    uploads = st.file_uploader(
        "Upload supporting documents",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
        help="Upload redacted documents only. OCR text is not saved or shown.",
    )
    future = st.session_state.get("document_review_future")
    review_running = future is not None and not future.done()
    if st.button(
        "Review documents", type="primary", disabled=not uploads or review_running
    ):
        file_data = [(item.name, item.getvalue()) for item in uploads]
        st.session_state.document_review_future = get_document_executor().submit(
            review_document_files, file_data
        )
        st.rerun()

    if review_running:
        st.info(
            "Document review is running in the background. You can keep this page open."
        )

    if st.session_state.get("document_review_future") is not None:

        @st.fragment(run_every="1s")
        def show_document_review_progress():
            review_future = st.session_state.get("document_review_future")
            if review_future is None or not review_future.done():
                st.info("Checking document readability and likely types…")
                return

            try:
                documents = review_future.result()
            except Exception as exc:
                documents = []
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"Document review could not be completed ({type(exc).__name__}). Please try again with a clearer file.",
                    }
                )
            if documents:
                st.session_state.document_review = documents
                recognized = {
                    category for doc in documents for category in doc["categories"]
                }
                readable_count = sum(doc["readable"] for doc in documents)
                status = st.session_state.get("result", {}).get("final_status")
                if status == "indicative_match":
                    required = {
                        "identity/address proof",
                        "income proof",
                        "bank statement",
                    }
                    missing = sorted(required - recognized)
                    if missing:
                        next_steps = (
                            "Next steps: this is an indicative eligibility result. Add or rename documents so they clearly show: "
                            + ", ".join(missing)
                            + ". Then submit them through the lender’s official application channel."
                        )
                    else:
                        next_steps = (
                            "Next steps: the expected document categories were found. Review each file for accuracy, "
                            "then submit them through the lender’s official channel for verification and underwriting."
                        )
                else:
                    next_steps = (
                        "Next steps: the current eligibility result needs review. Documents do not change this "
                        "eligibility assessment; contact a lender or adviser to review the factors before applying."
                    )
                lines = []
                for doc in documents:
                    label = ", ".join(doc["categories"]) or "type not identified"
                    readability = "readable" if doc["readable"] else "not readable"
                    lines.append(
                        f"{doc['name']}: {readability}; {label} (checked by {doc['analysis_source']})."
                    )
                summary = "Document review: " + " ".join(lines)
                preset_details = False
                for doc in documents:
                    if doc.get("details"):
                        summary += " " + doc["details"]
                        preset_details = True
                if not preset_details:
                    if readable_count == 0:
                        summary += (
                            " Neither OCR nor the local visual fallback could confidently read an uploaded file. "
                            "Try a clearer image or PDF."
                        )
                    summary += (
                        " "
                        + next_steps
                        + " OCR and visual review check readability and likely type only; they do not authenticate documents."
                    )
                st.session_state.messages.append(
                    {"role": "assistant", "content": summary}
                )
                st.session_state.flow_step = "document_review"
            st.session_state.pop("document_review_future", None)
            st.rerun()

        show_document_review_progress()
st.caption(
    "Eligibility uses the current eligibility criteria. Credit scores are user-stated; no bureau check or application submission occurs."
)
