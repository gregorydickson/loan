"""Few-shot examples for account number extraction using LangExtract.

This module provides few-shot examples that teach LangExtract how to extract
account and loan numbers from loan documents. All extraction_text values MUST be
verbatim substrings of the sample text - LangExtract validates alignment.

Account extraction covers:
- Bank account numbers (checking, savings)
- Loan numbers (mortgage, auto, personal)
- Credit card numbers (last 4 digits typically)
- Investment account numbers
"""

import langextract as lx

# Sample account section - Multiple account types
SAMPLE_ACCOUNT_TEXT_1 = """ASSET AND LIABILITY VERIFICATION

BORROWER ASSETS

Bank of America
Checking Account #: 4521876543
Current Balance: $12,450.00

Chase Bank
Savings Account #: 7891234560
Current Balance: $45,780.00

Fidelity Investments
Brokerage Account: FID-2024-789012
Current Value: $125,000.00

LIABILITIES

Existing Mortgage
Wells Fargo Loan #: WF-MTG-2020-456789
Original Amount: $350,000
Current Balance: $298,500

Auto Loan
Capital One Loan Number: AUTO-2023-112233
Monthly Payment: $485.00
Remaining Balance: $18,200.00

Credit Cards
Visa ending in 4532
Current Balance: $2,100.00
"""

# Sample account section - Business and personal accounts
SAMPLE_ACCOUNT_TEXT_2 = """ACCOUNT VERIFICATION FORM

APPLICANT: John Smith
DATE: January 15, 2025

PERSONAL ACCOUNTS

Primary Checking
Bank: First National Bank
Account: 9988776655
Balance: $8,750.00

Emergency Savings
Bank: Ally Bank
Account Number: 1122334455
Balance: $25,000.00

BUSINESS ACCOUNTS (Self-Employed Applicant)

Business Operating Account
Bank: US Bank
Account #: BUS-7766554433
Balance: $42,800.00

EXISTING LOANS

Current Mortgage
Lender: Quicken Loans
Loan ID: QL-2019-887766
Monthly Payment: $1,850.00

Personal Line of Credit
Lender: PNC Bank
LOC Number: PNC-LOC-445566
Credit Limit: $25,000
Current Draw: $8,500.00
"""

ACCOUNT_EXAMPLES = [
    # Example 1: Consumer accounts and liabilities
    lx.data.ExampleData(
        text=SAMPLE_ACCOUNT_TEXT_1,
        extractions=[
            # Bank accounts
            lx.data.Extraction(
                extraction_class="account",
                extraction_text="4521876543",
                attributes={
                    "account_type": "checking",
                    "institution": "Bank of America",
                },
            ),
            lx.data.Extraction(
                extraction_class="account",
                extraction_text="7891234560",
                attributes={
                    "account_type": "savings",
                    "institution": "Chase Bank",
                },
            ),
            lx.data.Extraction(
                extraction_class="account",
                extraction_text="FID-2024-789012",
                attributes={
                    "account_type": "brokerage",
                    "institution": "Fidelity Investments",
                },
            ),
            # Loan numbers
            lx.data.Extraction(
                extraction_class="loan",
                extraction_text="WF-MTG-2020-456789",
                attributes={
                    "loan_type": "mortgage",
                    "institution": "Wells Fargo",
                },
            ),
            lx.data.Extraction(
                extraction_class="loan",
                extraction_text="AUTO-2023-112233",
                attributes={
                    "loan_type": "auto",
                    "institution": "Capital One",
                },
            ),
            # Credit card (partial number)
            lx.data.Extraction(
                extraction_class="account",
                extraction_text="4532",
                attributes={
                    "account_type": "credit_card",
                    "institution": "Visa",
                },
            ),
        ],
    ),
    # Example 2: Personal and business accounts
    lx.data.ExampleData(
        text=SAMPLE_ACCOUNT_TEXT_2,
        extractions=[
            # Personal accounts
            lx.data.Extraction(
                extraction_class="account",
                extraction_text="9988776655",
                attributes={
                    "account_type": "checking",
                    "institution": "First National Bank",
                },
            ),
            lx.data.Extraction(
                extraction_class="account",
                extraction_text="1122334455",
                attributes={
                    "account_type": "savings",
                    "institution": "Ally Bank",
                },
            ),
            # Business account
            lx.data.Extraction(
                extraction_class="account",
                extraction_text="BUS-7766554433",
                attributes={
                    "account_type": "business_checking",
                    "institution": "US Bank",
                },
            ),
            # Loan numbers
            lx.data.Extraction(
                extraction_class="loan",
                extraction_text="QL-2019-887766",
                attributes={
                    "loan_type": "mortgage",
                    "institution": "Quicken Loans",
                },
            ),
            lx.data.Extraction(
                extraction_class="loan",
                extraction_text="PNC-LOC-445566",
                attributes={
                    "loan_type": "line_of_credit",
                    "institution": "PNC Bank",
                },
            ),
        ],
    ),
]
