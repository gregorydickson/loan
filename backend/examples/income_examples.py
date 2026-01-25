"""Few-shot examples for income extraction using LangExtract.

This module provides few-shot examples that teach LangExtract how to extract
income records from loan documents. All extraction_text values MUST be
verbatim substrings of the sample text - LangExtract validates alignment.

Income extraction covers:
- Employment income (W-2, salary)
- Self-employment income (1099, business)
- Other income (rental, investment, retirement)
"""

import langextract as lx

# Sample income section - Multiple income sources and formats
SAMPLE_INCOME_TEXT_1 = """INCOME DOCUMENTATION - VERIFICATION SUMMARY

BORROWER: Jane Williams
SSN: XXX-XX-1234

EMPLOYMENT INCOME

Current Employer: Global Financial Services
Position: Financial Analyst
Start Date: March 2020

Verified Income:
Base Salary 2025: $95,000 per year
Base Salary 2024: $88,000 per year
Bonus 2024: $12,000

Previous Employer: Regional Bank Corp
Position: Junior Analyst
Employment Period: 2018-2020
Final Salary: $65,000 annually

SELF-EMPLOYMENT INCOME

Business: Williams Tax Prep (Side Business)
Schedule C Net Income 2024: $18,500
Schedule C Net Income 2023: $15,200

OTHER INCOME

Rental Property Income: $1,800 per month
Investment Dividends 2024: $3,400
"""

# Sample income section - Complex compensation structure
SAMPLE_INCOME_TEXT_2 = """WAGE AND INCOME VERIFICATION

Employee: Robert Martinez
Employer: Tech Innovations Inc
Department: Engineering

COMPENSATION BREAKDOWN

Annual Base: $145,000 (2025)
Stock Options Vested: $28,000 (2025)
Performance Bonus: $22,500 (2025)

Prior Year Earnings:
Total W-2 Income 2024: $168,000
Total W-2 Income 2023: $155,500

RETIREMENT CONTRIBUTIONS
401(k) Match: $8,700 (2025)
"""

INCOME_EXAMPLES = [
    # Example 1: Multiple income types and sources
    lx.data.ExampleData(
        text=SAMPLE_INCOME_TEXT_1,
        extractions=[
            # Employment income - current year
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$95,000 per year",
                attributes={
                    "amount": "95000",
                    "period": "annual",
                    "year": "2025",
                    "source_type": "employment",
                    "employer": "Global Financial Services",
                },
            ),
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$88,000 per year",
                attributes={
                    "amount": "88000",
                    "period": "annual",
                    "year": "2024",
                    "source_type": "employment",
                    "employer": "Global Financial Services",
                },
            ),
            # Bonus income
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$12,000",
                attributes={
                    "amount": "12000",
                    "period": "annual",
                    "year": "2024",
                    "source_type": "bonus",
                    "employer": "Global Financial Services",
                },
            ),
            # Previous employer
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$65,000 annually",
                attributes={
                    "amount": "65000",
                    "period": "annual",
                    "year": "2020",
                    "source_type": "employment",
                    "employer": "Regional Bank Corp",
                },
            ),
            # Self-employment income
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$18,500",
                attributes={
                    "amount": "18500",
                    "period": "annual",
                    "year": "2024",
                    "source_type": "self-employment",
                    "employer": "Williams Tax Prep",
                },
            ),
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$15,200",
                attributes={
                    "amount": "15200",
                    "period": "annual",
                    "year": "2023",
                    "source_type": "self-employment",
                    "employer": "Williams Tax Prep",
                },
            ),
            # Other income
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$1,800 per month",
                attributes={
                    "amount": "1800",
                    "period": "monthly",
                    "year": "2025",
                    "source_type": "rental",
                    "employer": None,
                },
            ),
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$3,400",
                attributes={
                    "amount": "3400",
                    "period": "annual",
                    "year": "2024",
                    "source_type": "investment",
                    "employer": None,
                },
            ),
        ],
    ),
    # Example 2: Complex compensation with bonuses and stock
    lx.data.ExampleData(
        text=SAMPLE_INCOME_TEXT_2,
        extractions=[
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$145,000 (2025)",
                attributes={
                    "amount": "145000",
                    "period": "annual",
                    "year": "2025",
                    "source_type": "employment",
                    "employer": "Tech Innovations Inc",
                },
            ),
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$28,000 (2025)",
                attributes={
                    "amount": "28000",
                    "period": "annual",
                    "year": "2025",
                    "source_type": "stock_options",
                    "employer": "Tech Innovations Inc",
                },
            ),
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$22,500 (2025)",
                attributes={
                    "amount": "22500",
                    "period": "annual",
                    "year": "2025",
                    "source_type": "bonus",
                    "employer": "Tech Innovations Inc",
                },
            ),
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$168,000",
                attributes={
                    "amount": "168000",
                    "period": "annual",
                    "year": "2024",
                    "source_type": "employment",
                    "employer": "Tech Innovations Inc",
                },
            ),
            lx.data.Extraction(
                extraction_class="income",
                extraction_text="$155,500",
                attributes={
                    "amount": "155500",
                    "period": "annual",
                    "year": "2023",
                    "source_type": "employment",
                    "employer": "Tech Innovations Inc",
                },
            ),
        ],
    ),
]
