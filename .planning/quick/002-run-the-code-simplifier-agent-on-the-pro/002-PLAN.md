---
phase: quick
plan: 002
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/lib/formatting.ts
  - frontend/src/components/borrowers/borrower-table.tsx
  - frontend/src/components/borrowers/borrower-card.tsx
  - backend/src/extraction/validation.py
autonomous: true
---

<objective>
Implement the top quick-win simplifications identified in quick task 001 code analysis.

Purpose: Apply the highest-impact, lowest-effort recommendations from the code-simplifier analysis to reduce duplication and improve maintainability.

Output: Refactored code implementing 2 quick-win items (confidence badge extraction + validation consolidation).
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
Quick task 001 summary (completed 2026-01-25):
@.planning/quick/001-use-the-code-simplifier-agent-to-review-/001-SUMMARY.md

Key findings from that analysis:
- 8 high-impact simplification opportunities identified
- Top quick wins:
  1. Extract Confidence Badge Logic (#9) - 12 LOC, High impact, Low effort
  2. Consolidate Validation Pattern (#2) - 40 LOC, High impact, Low effort

This plan implements items #9 and #2 from the prioritized recommendations.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extract Confidence Badge Utility to Shared Location</name>
  <files>
    frontend/src/lib/formatting.ts (new)
    frontend/src/components/borrowers/borrower-table.tsx
    frontend/src/components/borrowers/borrower-card.tsx
  </files>
  <action>
Create a new utility file `frontend/src/lib/formatting.ts` containing:

1. Move `getConfidenceBadgeVariant` function from `borrower-table.tsx:23-29`
2. Export it for reuse
3. Add JSDoc documentation explaining the thresholds:
   - >= 0.8: "default" (success/green)
   - >= 0.5: "secondary" (warning/yellow)
   - < 0.5: "destructive" (error/red)

Then update both consuming files:
- `borrower-table.tsx`: Remove local function, import from `@/lib/formatting`
- `borrower-card.tsx:14-20`: Remove local function, import from `@/lib/formatting`

Expected result: Single source of truth for confidence display logic.
  </action>
  <verify>
Run `npm run build` in frontend directory to confirm no import errors.
Verify function is exported: `grep -r "getConfidenceBadgeVariant" frontend/src/`
  </verify>
  <done>Confidence badge logic consolidated into shared utility, both components updated to use it</done>
</task>

<task type="auto">
  <name>Task 2: Consolidate Validation Pattern with Generic Helper</name>
  <files>backend/src/extraction/validation.py</files>
  <action>
Refactor `backend/src/extraction/validation.py:78-227` to reduce duplication.

Current state: Four similar validation methods with repeated return patterns:
- `validate_ssn`
- `validate_phone`
- `validate_zip`
- `validate_year`

Create a generic `_validate_with_pattern` helper:

```python
def _validate_with_pattern(
    value: str | None,
    field_name: str,
    pattern: re.Pattern[str],
    error_message: str,
    formatter: Callable[[str], str] | None = None
) -> ValidationResult:
    """Generic pattern-based validation with optional formatting."""
    if not value:
        return ValidationResult(is_valid=False, field=field_name, error="Value is required")

    cleaned = value.strip()
    if not pattern.match(cleaned):
        return ValidationResult(is_valid=False, field=field_name, error=error_message)

    formatted = formatter(cleaned) if formatter else cleaned
    return ValidationResult(is_valid=True, field=field_name, value=formatted)
```

Then refactor each validator to use it:

```python
SSN_PATTERN = re.compile(r'^\d{9}$|^\d{3}-\d{2}-\d{4}$')

def validate_ssn(value: str | None) -> ValidationResult:
    def format_ssn(v: str) -> str:
        digits = re.sub(r'[^\d]', '', v)
        return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"

    return _validate_with_pattern(
        value, "ssn", SSN_PATTERN,
        "SSN must be 9 digits (XXX-XX-XXXX)",
        format_ssn
    )
```

Repeat for phone, zip, year with their respective patterns and formatters.

Expected reduction: ~40 LOC by eliminating repeated validation boilerplate.
  </action>
  <verify>
Run existing validation tests: `cd backend && pytest tests/unit/extraction/test_validation.py -v`
All existing tests must pass - this is a refactor, not a behavior change.
  </verify>
  <done>Validation methods refactored to use generic helper, all tests pass, ~40 LOC reduction achieved</done>
</task>

<task type="auto">
  <name>Task 3: Run Tests and Verify No Regressions</name>
  <files>None (verification only)</files>
  <action>
Run full test suite to ensure refactoring introduced no regressions:

1. Frontend build:
   ```
   cd frontend && npm run build && npm run lint
   ```

2. Backend tests:
   ```
   cd backend && pytest tests/ -v --tb=short
   ```

3. Type checking:
   ```
   cd backend && mypy src/
   ```

If any tests fail, investigate and fix before completing.
  </action>
  <verify>
- Frontend: `npm run build` exits 0
- Backend: All 490 tests pass
- mypy: 0 errors
  </verify>
  <done>All tests pass, type checking passes, refactoring complete without regressions</done>
</task>

</tasks>

<verification>
- `getConfidenceBadgeVariant` exists in `frontend/src/lib/formatting.ts`
- `borrower-table.tsx` and `borrower-card.tsx` import from shared location
- `_validate_with_pattern` helper exists in `validation.py`
- All 4 validators use the helper
- Full test suite passes (490 tests)
- mypy reports 0 errors
</verification>

<success_criteria>
- Confidence badge logic consolidated (12 LOC reduction)
- Validation pattern consolidated (40 LOC reduction)
- All tests pass with no regressions
- Code follows existing project conventions
</success_criteria>

<output>
Present results directly to user:
- Files modified
- LOC reduction achieved
- Test results confirmation
</output>
