"""OCR module for scanned document detection and GPU OCR integration.

LOCR-05: Scanned document detection implemented (auto OCR routing)
LOCR-06: LightOnOCRClient in backend communicates with GPU service via HTTP
LOCR-11: Fallback to Docling OCR when GPU service unavailable
"""

from src.ocr.lightonocr_client import LightOnOCRClient, LightOnOCRError
from src.ocr.ocr_router import OCRMode, OCRResult, OCRRouter
from src.ocr.scanned_detector import DetectionResult, ScannedDocumentDetector

__all__ = [
    "DetectionResult",
    "LightOnOCRClient",
    "LightOnOCRError",
    "OCRMode",
    "OCRResult",
    "OCRRouter",
    "ScannedDocumentDetector",
]
