"""Few-shot examples for borrower extraction using LangExtract.

This module provides few-shot examples that teach LangExtract how to extract
borrower information from loan documents. All extraction_text values MUST be
verbatim substrings of the sample text - LangExtract validates alignment.

See: 11-RESEARCH.md for LangExtract patterns and requirements.
"""

import langextract as lx

# Sample loan document excerpt 1 - Primary borrower with full information
SAMPLE_LOAN_TEXT_1 = """LOAN APPLICATION - BORROWER INFORMATION

Primary Borrower: Sarah Johnson
Social Security Number: 987-65-4321
Current Address: 456 Oak Avenue, Apartment 12B, Houston, TX 77001
Phone: (713) 555-9876
Email: sarah.johnson@email.com

EMPLOYMENT INFORMATION
Employer: TechCorp Industries
Position: Senior Engineer
Annual Salary: $125,000 (2025)
Annual Salary: $118,000 (2024)

CO-BORROWER INFORMATION

Co-Borrower: Michael Johnson
Social Security Number: 876-54-3210
Current Address: 456 Oak Avenue, Apartment 12B, Houston, TX 77001
Phone: (713) 555-8765

ACCOUNT INFORMATION
Primary Checking Account: 1234567890
Savings Account: 9876543210
Loan Number: LN-2025-001234
"""

# Sample loan document excerpt 2 - Self-employed borrower
SAMPLE_LOAN_TEXT_2 = """UNIFORM RESIDENTIAL LOAN APPLICATION

Borrower Name: David Chen
SSN: 456-78-9012
Mailing Address: 789 Maple Drive, San Francisco, CA 94102
Contact Phone: (415) 555-3456
Email Address: david.chen@consulting.net

INCOME VERIFICATION

Self-Employment Income
Business Name: Chen Consulting LLC
2025 Gross Income: $175,000
2024 Gross Income: $162,000
2023 Gross Income: $148,500

ASSET VERIFICATION
Business Checking: 5551234567
Business Line of Credit: LOC-2024-789456
"""

BORROWER_EXAMPLES = [
    # Example 1: Primary and co-borrower with employment income
    lx.data.ExampleData(
        text=SAMPLE_LOAN_TEXT_1,
        extractions=[
            # Primary borrower
            lx.data.Extraction(
                extraction_class="borrower",
                extraction_text="Sarah Johnson",
                attributes={
                    "ssn": "987-65-4321",
                    "street": "456 Oak Avenue, Apartment 12B",
                    "city": "Houston",
                    "state": "TX",
                    "zip_code": "77001",
                    "phone": "(713) 555-9876",
                    "email": "sarah.johnson@email.com",
                },
            ),
            # Co-borrower
            lx.data.Extraction(
                extraction_class="borrower",
                extraction_text="Michael Johnson",
                attributes={
                    "ssn": "876-54-3210",
                    "street": "456 Oak Avenue, Apartment 12B",
                    "city": "Houston",
                    "state": "TX",
                    "zip_code": "77001",
                    "phone": "(713) 555-8765",
                    "email": None,
                },
            ),
            # Income records for primary borrower
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$125,000 (2025)",
                attributes={
                    "amount": "125000",
                    "period": "annual",
                    "year": "2025",
                    "source_type": "employment",
                    "employer": "TechCorp Industries",
                },
            ),
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$118,000 (2024)",
                attributes={
                    "amount": "118000",
                    "period": "annual",
                    "year": "2024",
                    "source_type": "employment",
                    "employer": "TechCorp Industries",
                },
            ),
            # Account numbers
            lx.data.Extraction(
                extraction_class="account",
                extraction_text="1234567890",
                attributes={"account_type": "checking"},
            ),
            lx.data.Extraction(
                extraction_class="account",
                extraction_text="9876543210",
                attributes={"account_type": "savings"},
            ),
            # Loan number
            lx.data.Extraction(
                extraction_class="loan",
                extraction_text="LN-2025-001234",
                attributes={"loan_type": "mortgage"},
            ),
        ],
    ),
    # Example 2: Self-employed borrower
    lx.data.ExampleData(
        text=SAMPLE_LOAN_TEXT_2,
        extractions=[
            lx.data.Extraction(
                extraction_class="borrower",
                extraction_text="David Chen",
                attributes={
                    "ssn": "456-78-9012",
                    "street": "789 Maple Drive",
                    "city": "San Francisco",
                    "state": "CA",
                    "zip_code": "94102",
                    "phone": "(415) 555-3456",
                    "email": "david.chen@consulting.net",
                },
            ),
            # Self-employment income records
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$175,000",
                attributes={
                    "amount": "175000",
                    "period": "annual",
                    "year": "2025",
                    "source_type": "self-employment",
                    "employer": "Chen Consulting LLC",
                },
            ),
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$162,000",
                attributes={
                    "amount": "162000",
                    "period": "annual",
                    "year": "2024",
                    "source_type": "self-employment",
                    "employer": "Chen Consulting LLC",
                },
            ),
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$148,500",
                attributes={
                    "amount": "148500",
                    "period": "annual",
                    "year": "2023",
                    "source_type": "self-employment",
                    "employer": "Chen Consulting LLC",
                },
            ),
            # Account numbers
            lx.data.Extraction(
                extraction_class="account",
                extraction_text="5551234567",
                attributes={"account_type": "business_checking"},
            ),
            lx.data.Extraction(
                extraction_class="loan",
                extraction_text="LOC-2024-789456",
                attributes={"loan_type": "line_of_credit"},
            ),
        ],
    ),
]
