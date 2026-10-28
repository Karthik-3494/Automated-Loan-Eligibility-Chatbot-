import math
from docling.document_converter import DocumentConverter


def docling_ocr_extractor(path):
    try:
        result = DocumentConverter().convert(path)
        text = result.document.export_to_text()
        score = result.confidence.mean_score
        confidence = float(score) if math.isfinite(float(score)) else None
        return text, confidence
    except Exception:
        return None, None
