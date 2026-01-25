"""OCR module for scanned document detection and GPU OCR integration.

LOCR-05: Scanned document detection implemented (auto OCR routing)
LOCR-06: LightOnOCRClient in backend communicates with GPU service via HTTP
"""

from src.ocr.lightonocr_client import LightOnOCRClient, LightOnOCRError
from src.ocr.scanned_detector import DetectionResult, ScannedDocumentDetector

__all__ = [
    "DetectionResult",
    "LightOnOCRClient",
    "LightOnOCRError",
    "ScannedDocumentDetector",
]
