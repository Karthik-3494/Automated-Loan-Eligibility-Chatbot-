from pathlib import Path


def validate(state):
    errors = []
    for key in ("loan_type", "residency", "employment_type"):
        if not str(state.get(key, "")).strip():
            errors.append(f'Missing {key.replace("_"," ")}')
    checks = [
        ("age", 18, 100),
        ("monthly_income", 0, 1e9),
        ("monthly_obligations", 0, 1e9),
        ("credit_score", 300, 900),
        ("requested_amount", 0 if state.get("intent") == "capacity" else 1, 1e9),
        ("tenure_months", 1, 480),
    ]
    for key, low, high in checks:
        try:
            val = float(state.get(key))
        except (ValueError, TypeError):
            errors.append(f'Invalid {key.replace("_"," ")}')
            continue
        if val < low or val > high:
            errors.append(f'{key.replace("_"," ")} outside valid range')
    return list(dict.fromkeys(errors))
