from dataclasses import dataclass


@dataclass
class Product:
    name: str
    annual_rate: float
    max_amount: float
    max_dti: float
    secured: bool = False


PRODUCTS = {
    "Personal Loan": Product("Personal Loan", 0.145, 2500000, 0.40),
    "Home Loan": Product("Home Loan", 0.0875, 15000000, 0.55, True),
    "Auto Loan": Product("Auto Loan", 0.105, 4000000, 0.50, True),
    "Check Max Borrowing Power": None,
}


def emi(principal, annual_rate, months):
    if principal <= 0 or months <= 0:
        return 0
    r = annual_rate / 12
    f = (1 + r) ** months
    return principal * r * f / (f - 1)


def max_amount(income, obligations, score, product, tenure):
    if income <= 0:
        return 0
    cap = max(0, income * product.max_dti - obligations)
    monthly_rate = product.annual_rate / 12
    factor = (1 + monthly_rate) ** tenure
    amount = cap * (factor - 1) / (monthly_rate * factor) if cap and tenure > 0 else 0
    score_factor = (
        1 if score >= 750 else (0.8 if score >= 680 else 0.55 if score >= 620 else 0)
    )
    return max(0, min(product.max_amount, amount)) * score_factor


def calculate(state):
    intent = state.get("intent", "specific")
    requested = state.get("loan_type", "Personal Loan")
    income = float(state.get("monthly_income", 0))
    obligations = float(state.get("monthly_obligations", 0))
    score = int(state.get("credit_score", 0))
    tenure = int(state.get("tenure_months", 60))
    products = (
        [PRODUCTS[requested]]
        if requested != "Check Max Borrowing Power"
        else [PRODUCTS["Home Loan"], PRODUCTS["Auto Loan"], PRODUCTS["Personal Loan"]]
    )
    offers = []
    for p in products:
        amount = max_amount(income, obligations, score, p, tenure)
        principal = (
            amount
            if state.get("intent") == "capacity"
            else min(float(state.get("requested_amount", amount)), amount)
        )
        payment = emi(principal, p.annual_rate, tenure)
        eligible = (
            amount >= 50000
            and score >= 620
            and payment + obligations <= income * p.max_dti
        )
        offers.append(
            {
                "product": p.name,
                "rate_apr": p.annual_rate,
                "max_amount": round(amount, -2),
                "requested_amount": float(state.get("requested_amount", 0)),
                "estimated_emi": round(payment),
                "tenure_months": tenure,
                "eligible": eligible,
                "secured": p.secured,
                "reason": (
                    None
                    if eligible
                    else (
                        "Score/repayment capacity does not meet the current product threshold"
                        if amount
                        else "No borrowing capacity under the current product criteria"
                    )
                ),
            }
        )
    offers.sort(key=lambda o: (not o["eligible"], o["rate_apr"], -o["max_amount"]))
    return offers
