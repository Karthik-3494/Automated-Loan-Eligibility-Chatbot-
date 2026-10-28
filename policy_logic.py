POLICIES = [
    {
        "source_id": "ELIG-001",
        "topic": "hard_knockout",
        "text": "Eligibility screening requires age 21–60, Indian residency and monthly net income of at least ₹25,000.",
        "keywords": ["age", "residency", "income", "knockout"],
    },
    {
        "source_id": "ELIG-002",
        "topic": "debt_capacity",
        "text": "Indicative monthly debt service should remain within the product debt-to-income limit.",
        "keywords": ["emi", "obligation", "debt", "income", "capacity"],
    },
    {
        "source_id": "ELIG-003",
        "topic": "credit",
        "text": "A stated score is a user-provided estimate, not a bureau fetch; lower scores require review.",
        "keywords": ["credit", "score", "bureau", "review"],
    },
    {
        "source_id": "ELIG-004",
        "topic": "documents",
        "text": "Identity and income documents may be requested at application; OCR readability is not verification.",
        "keywords": ["document", "kyc", "identity", "verification"],
    },
    {
        "source_id": "ELIG-005",
        "topic": "alternatives",
        "text": "When an unsecured request does not fit, discuss a secured product only if its own checks pass.",
        "keywords": ["alternative", "secured", "personal", "home", "auto"],
    },
]


def retrieve_policies(query, limit=3):
    q = query.casefold()
    ranked = []
    for p in POLICIES:
        score = sum(k in q for k in p["keywords"])
        if score:
            ranked.append((score, p))
    ranked.sort(key=lambda x: (-x[0], x[1]["source_id"]))
    return [
        {
            "source_id": p["source_id"],
            "topic": p["topic"],
            "snippet": p["text"],
            "retrieval_method": "keyword",
        }
        for _, p in ranked[:limit]
    ]
