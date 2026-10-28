import re

POLICIES = [
    {
        "source_id": "POL-001",
        "topic": "required_fields",
        "text": "Name, DOB, ID number and ID expiry must be present for document processing.",
        "keywords": ["required fields", "missing field", "name", "dob", "id number", "id expiry"],
    },
    {
        "source_id": "POL-002",
        "topic": "ocr_confidence",
        "text": "OCR confidence below 0.60 requires manual review before proceeding.",
        "keywords": ["ocr confidence", "low confidence", "manual review"],
    },
    {
        "source_id": "POL-003",
        "topic": "expired_document",
        "text": "An expired identity document must be referred for review.",
        "keywords": ["expired document", "document expired", "expired identity"],
    },
    {
        "source_id": "POL-004",
        "topic": "identity_mismatch",
        "text": "A mismatch in identity fields requires review. Do not treat it as a confirmed match.",
        "keywords": ["identity mismatch", "name mismatch", "dob mismatch"],
    },
    {
        "source_id": "POL-005",
        "topic": "inconclusive_kyc",
        "text": "If identity verification is inconclusive, mark the case for review rather than claiming successful verification.",
        "keywords": ["inconclusive verification", "unknown verification", "no matching mock record"],
    },
]

def retrieve_policies(query: str, limit: int = 3) -> list[dict]:
    query = re.sub(r"\s+", " ", query.casefold()).strip()
    if not query or limit <= 0:
        return []

    matches = []
    for policy in POLICIES:
        score = sum(keyword in query for keyword in policy["keywords"])
        if score:
            matches.append((score, policy))

    matches.sort(key=lambda item: (-item[0], item[1]["source_id"]))
    return [
        {
            "source_id": policy["source_id"],
            "topic": policy["topic"],
            "snippet": policy["text"],
            "retrieval_method": "keyword",
        }
        for _, policy in matches[:limit]
    ]