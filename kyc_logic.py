# Profile-only checks; no external bureau or identity service is contacted.
def run(state):
    errors = []
    if state.get("credit_score") is None:
        errors.append("No stated credit score")
    if state.get("employment_type") == "Other" and state.get("monthly_income", 0) <= 0:
        errors.append("Income source needs review")
    return {
        "status": "needs_review" if errors else "profile_reviewed",
        "errors": errors,
    }
