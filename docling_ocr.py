import base64
import io
import json
import math
import os
from pathlib import Path


def docling_ocr_extractor(path):
    try:
        from docling.document_converter import DocumentConverter

        result = DocumentConverter().convert(str(path))
        text = result.document.export_to_text()
        score = getattr(getattr(result, "confidence", None), "mean_score", None)
        score = (
            float(score) if score is not None and math.isfinite(float(score)) else None
        )
        return text, score, None
    except Exception as exc:
        return "", None, f"{type(exc).__name__}: {exc}"


def qwen_document_fallback(path):
    """Use local Qwen vision to identify a document when OCR returns no text."""
    path = Path(path)
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        return {
            "available": False,
            "categories": [],
            "error": "Vision fallback supports image files only.",
        }

    try:
        import ollama
        from PIL import Image

        with Image.open(path) as image:
            image = image.convert("RGB")
            image.thumbnail((2048, 2048))
            image_buffer = io.BytesIO()
            image.save(image_buffer, format="JPEG", quality=88)
        encoded_image = base64.b64encode(image_buffer.getvalue()).decode("ascii")

        response = ollama.chat(
            model=os.getenv("LOANGUIDE_VISION_MODEL", "qwen3-vl:2b"),
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Identify the visible document types. Return only comma-separated labels "
                        "from this list: identity/address proof, income proof, bank statement, "
                        "collateral/asset document. Do not transcribe names, account numbers, "
                        "addresses, or other personal information. Do not claim that a document "
                        "is authentic, valid, verified, or sufficient for a loan."
                    ),
                    "images": [encoded_image],
                }
            ],
            options={"temperature": 0, "num_predict": 100, "num_ctx": 8192},
        )
        answer = response.message.content.casefold()
        categories = []
        if "identity" in answer and "address" in answer:
            categories.append("identity/address proof")
        if "income proof" in answer or "pay stub" in answer or "payslip" in answer:
            categories.append("income proof")
        if "bank statement" in answer:
            categories.append("bank statement")
        if "collateral" in answer or "asset document" in answer:
            categories.append("collateral/asset document")
        return {
            "available": True,
            "categories": categories,
            "readable": bool(categories),
            "note": answer[:240],
            "error": None,
        }
    except Exception as exc:
        return {
            "available": False,
            "categories": [],
            "readable": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
