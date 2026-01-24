"""Extraction prompt templates for LLM borrower data extraction.

This module provides prompt templates and safe text handling for
extracting structured borrower information from loan documents.

Key functions:
- build_extraction_prompt: Safely inject document text into prompt
- EXTRACTION_SYSTEM_PROMPT: System instructions for the extraction LLM
- EXTRACTION_USER_PROMPT_TEMPLATE: User prompt template with {document_text}
"""

EXTRACTION_SYSTEM_PROMPT = """You are a loan document data extraction specialist. Extract borrower information from loan documents with high accuracy.

Your task:
1. Identify all borrowers mentioned in the document
2. Extract their personal information (name, SSN, address, phone, email)
3. Extract income history with amounts, periods, and sources
4. Extract account and loan numbers

Rules:
- Extract data exactly as it appears - do not infer or guess
- If a field is unclear or missing, omit it (return null)
- SSN format: XXX-XX-XXXX
- Income amounts: numeric only, no currency symbols
- Multiple borrowers should be separate records

Quality indicators to note:
- Mark data from handwritten sections with lower confidence
- Note if scanned text appears unclear
"""

EXTRACTION_USER_PROMPT_TEMPLATE = """Extract all borrower information from this loan document:

---
{document_text}
---

Return a JSON object with the extracted borrowers."""


def build_extraction_prompt(document_text: str) -> str:
    """Build the user prompt for extraction with safe text injection.

    Handles special characters (curly braces) safely to prevent
    string formatting issues (EXTRACT-18 requirement).

    Args:
        document_text: Raw document text from Docling processing

    Returns:
        Formatted prompt ready for LLM

    Example:
        >>> prompt = build_extraction_prompt("Borrower: John {Smith}")
        >>> "{Smith}" not in prompt  # Braces are escaped
        True
    """
    # Escape curly braces to prevent string formatting issues
    safe_text = document_text.replace("{", "{{").replace("}", "}}")
    return EXTRACTION_USER_PROMPT_TEMPLATE.format(document_text=safe_text)
