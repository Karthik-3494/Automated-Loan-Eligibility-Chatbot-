from agent_state import AgentState

mock_record = {
    "DL-SAMPLE-001": {
        "Name": "Asha Example",
        "DOB": "1994-06-12",
    }
}


class KYCCheck:
    def __init__(self, request_id):
        self.request_id = request_id

    def run(self, state: AgentState):
        errors = []
        if state.get("validation_errors"):
            state["kyc_status"] = "needs_review"
            state["kyc_errors"] = ["validation did not pass"]
            return state

        record = mock_record.get(state["ID_number"])
        if record is None:
            errors.append("no matching mock record")
        else:
            if record["Name"].strip().casefold() != state["Name"].strip().casefold():
                errors.append("Name mismatch")
            if record["DOB"] != state["DOB"]:
                errors.append("DOB mismatch")

        state["kyc_errors"] = errors
        state["kyc_status"] = "needs_review" if errors else "match"
        return state
