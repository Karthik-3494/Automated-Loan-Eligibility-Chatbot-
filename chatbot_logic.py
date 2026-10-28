import re
from loan_logic import PRODUCTS


def classify(text):
    t = text.casefold()
    if any(
        x in t
        for x in (
            "how much can i borrow",
            "maximum borrowing",
            "max borrowing",
            "compare loans",
            "all options",
            "borrowing power",
            "loan options",
            "which loan",
            "what loan",
            "recommend a loan",
        )
    ):
        return "capacity"
    for name in PRODUCTS:
        if name != "Check Max Borrowing Power" and name.casefold() in t:
            return "specific"
    aliases = {
        "personal": ["personal", "unsecured"],
        "home": ["home", "mortgage", "property"],
        "auto": ["auto", "car", "vehicle"],
    }
    for product, words in aliases.items():
        if any(w in t for w in words):
            return "specific"
    return "discovery"


def extract_fields(text):
    patterns = {
        "age": r"\b(?:age\s*)?(\d{2})\s*(?:years? old)?\b",
        "monthly_income": r"(?:income|earn|take.home|salary)\D{0,12}(\d[\d,]*)",
        "monthly_obligations": r"(?:obligations?|existing emi|current emi|debt)\D{0,12}(\d[\d,]*)",
        "credit_score": r"(?:score|cibil)\D{0,12}(\d{3})",
        "requested_amount": r"(?:borrow|loan|amount)\D{0,12}(\d[\d,]*)",
    }
    out = {}
    for k, p in patterns.items():
        m = re.search(p, text, re.I)
        if m:
            out[k] = int(m.group(1).replace(",", ""))
    return out


def fast_path(text):
    t = text.casefold().strip()
    if t in {"hi", "hello", "hey", "good morning"}:
        return "Hello! Are you looking for a Personal, Home, or Auto Loan, or do you want to check your borrowing power?"
    if "document" in t or "kyc" in t:
        return "At the application stage, a lender may request identity, address, and income documents. OCR only checks text readability here; it does not verify identity."
    if "help" in t:
        return "Choose a loan type or ask how much you may borrow. I will screen age, residency and income first, then review debts, stated score and estimated EMI."
    return None


def parse_eligibility_profile(text):
    """Extract an applicant profile from natural prose or comma-separated values."""
    profile = {}
    lowered = text.casefold()

    age_match = re.search(
        r"\bage\s*(?:is|:|=)?\s*(\d{1,3})\b|\bi(?:'m| am)\s+(\d{1,3})\b|\b(\d{1,3})\s+years?\s+old\b",
        text,
        re.I,
    )
    if age_match:
        profile["age"] = int(next(value for value in age_match.groups() if value))

    if any(
        term in lowered
        for term in ("not in india", "outside india", "non-resident", "not a resident")
    ):
        profile["residency"] = "Other"
    elif any(
        term in lowered
        for term in (
            "india resident",
            "resident of india",
            "live in india",
            "living in india",
            "indian resident",
        )
    ):
        profile["residency"] = "India"
    elif re.search(r"\b(yes|no)\b", lowered):
        profile["residency"] = "India" if re.search(r"\byes\b", lowered) else "Other"

    if (
        "self-employed" in lowered
        or "self employed" in lowered
        or "business" in lowered
    ):
        profile["employment_type"] = "Self-employed / Business"
    elif "salaried" in lowered or "salary" in lowered:
        profile["employment_type"] = "Salaried"
    elif "unemployed" in lowered or re.search(
        r"\bemployment\s*[:=]?\s*other\b", lowered
    ):
        profile["employment_type"] = "Other"

    duration_match = re.search(
        r"(?:employment|business|job|work|salaried|self-employed|self employed)[^\d]{0,24}(\d+)\s*(months?|mos?|years?|yrs?)\b",
        lowered,
    )
    if duration_match:
        duration = int(duration_match.group(1))
        profile["employment_months"] = (
            duration * 12
            if duration_match.group(2).startswith(("year", "yr"))
            else duration
        )

    income_match = re.search(
        r"(?:monthly\s+)?(?:take[ -]?home\s+income|net\s+income|income|salary)\s*(?:is|:|=)?\s*₹?\s*(\d[\d,]*)",
        text,
        re.I,
    )
    if income_match:
        profile["monthly_income"] = int(income_match.group(1).replace(",", ""))

    obligations_match = re.search(
        r"(?:existing\s+)?(?:monthly\s+)?(?:emis?|obligations?|debt payments?|loan payments?)\s*(?:are|is|:|=)?\s*₹?\s*(\d[\d,]*)",
        text,
        re.I,
    )
    if obligations_match:
        profile["monthly_obligations"] = int(
            obligations_match.group(1).replace(",", "")
        )
    elif re.search(
        r"\b(no|zero|none)\b.{0,25}\b(emi|emis|debt|loan|credit card)\b", lowered
    ):
        profile["monthly_obligations"] = 0

    score_match = re.search(
        r"(?:credit\s+)?(?:score|cibil)\s*(?:is|:|=)?\s*(\d{3})\b", text, re.I
    )
    if score_match:
        profile["credit_score"] = int(score_match.group(1))

    tenure_match = re.search(
        r"(?:tenure\s*(?:is|of|:|=)?\s*(\d{1,2})\s*(?:years?|yrs?)?|\b(\d{1,2})\s*[- ]?(?:year|yr)\s+tenure)",
        text,
        re.I,
    )
    if tenure_match:
        years = next(value for value in tenure_match.groups() if value)
        profile["tenure_months"] = int(years) * 12

    # Positional replies such as "43, yes, salaried, 30months, 400000, 0, 740, 10".
    parts = [part.strip() for part in re.split(r"[,;\n]+", text) if part.strip()]
    numeric_parts = []
    for part in parts:
        duration_part = re.fullmatch(r"(\d+)\s*(months?|mos?)", part, re.I)
        if duration_part and "employment_months" not in profile:
            profile["employment_months"] = int(duration_part.group(1))
            continue
        year_part = re.fullmatch(r"(\d+)\s*(years?|yrs?)", part, re.I)
        if year_part and "tenure_months" not in profile:
            profile["tenure_months"] = int(year_part.group(1)) * 12
            continue
        if re.fullmatch(r"₹?\s*[\d,]+\s*", part):
            numeric_parts.append(int(re.sub(r"[₹,\s]", "", part)))
        elif (
            re.fullmatch(r"\d{1,3}\s*years?\s*old", part, re.I) and "age" not in profile
        ):
            profile["age"] = int(re.search(r"\d+", part).group())

    # If the reply is unlabeled but ordered as requested, fill only fields not parsed above.
    positional_fields = [
        "age",
        "monthly_income",
        "monthly_obligations",
        "credit_score",
        "tenure_months",
    ]
    for field, value in zip(
        (key for key in positional_fields if key not in profile), numeric_parts
    ):
        if field == "tenure_months":
            profile[field] = value * 12 if value <= 30 else value
        else:
            profile[field] = value

    required = (
        "age",
        "residency",
        "employment_type",
        "employment_months",
        "monthly_income",
        "monthly_obligations",
        "credit_score",
        "tenure_months",
    )
    labels = {
        "residency": "Indian residency",
        "employment_months": "time in current job/business",
        "monthly_income": "monthly take-home income",
        "monthly_obligations": "monthly loan/card payments (0 if none)",
        "credit_score": "credit score",
        "tenure_months": "preferred tenure",
    }
    missing = [
        labels.get(field, field.replace("_", " "))
        for field in required
        if field not in profile
    ]
    return profile, missing
