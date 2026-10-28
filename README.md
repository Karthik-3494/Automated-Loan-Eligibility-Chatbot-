# Loan Eligibility Assistant

A Streamlit conversational loan eligibility assistant. It adapts a sequential workflow with request IDs, per-request logs, typed state, OCR, validation, applicant profile checks, policy retrieval, and structured reporting. The chat uses intent recognition, entity extraction, a rule-based fast path, and SQLite case persistence.

## Run

```powershell
cd C:\Users\karth\OneDrive\Desktop\coding\loan_hackathon
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Document review uses Docling: `pip install -r requirements-ocr.txt`. If OCR returns no readable text for an image, the assistant can fall back to local Qwen vision through Ollama. Install the optional client with `pip install -r requirements-local-ai.txt`, update Ollama to a Qwen3-VL-compatible version, and run `ollama pull qwen3-vl:2b`. Set `LOANGUIDE_VISION_MODEL` to choose another local vision model. The fallback identifies likely document categories but does not authenticate files. Upload redacted documents only; files are processed locally and are not submitted to a lender.

Optional local report narration requires `pip install -r requirements-local-ai.txt`, Ollama, and the configured local model. Eligibility results remain determined by the rule engine.

## Workflow

Loan intent → age, residency, and income screening → financial profile → applicant-provided credit score → eligibility calculation → result and product alternatives → optional document review and next-step guidance.

## Project files

- `app.py`: Streamlit chatbot and conversational flow
- `agent_state.py`: workflow state
- `sequential_agent.py`, `sequential_nodes.py`: ordered eligibility processing
- `request_id_generator.py`, `logger.py`: request IDs and per-request logs
- `validation_logic.py`, `kyc_logic.py`, `policy_logic.py`: validation, profile checks, and policy retrieval
- `docling_ocr.py`: document text extraction
- `loan_logic.py`: repayment and eligibility calculations
- `chatbot_logic.py`: intent and entity handling
- `db_helper.py`: SQLite persistence
- `ollama_synthesis.py`: optional local report narration

The configured eligibility criteria and rates are estimates for initial guidance. They do not constitute an approval or loan offer. Lenders may require additional checks and documents and make the final decision. The assistant does not contact a credit bureau or identity verification service.

