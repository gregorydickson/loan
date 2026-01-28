---
phase: quick
plan: 001
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: true
---

<objective>
Run the code-simplifier agent to review the loan document extraction system codebase and identify simplification opportunities.

Purpose: Identify areas where code can be simplified, deduplicated, or made more maintainable across the backend (Python) and frontend (TypeScript) codebases.

Output: Code simplification analysis report with actionable recommendations.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
Project structure:
- Backend: /Users/gregorydickson/stackpoint/loan/backend/src/ (49 Python files)
  - API layer: src/api/ (5 files)
  - Extraction: src/extraction/ (14 files)
  - OCR: src/ocr/ (4 files)
  - Ingestion: src/ingestion/ (4 files)
  - Storage: src/storage/ (5 files)
  - Models: src/models/ (3 files)
- Frontend: /Users/gregorydickson/stackpoint/loan/frontend/src/ (~30 files)
  - Components: src/components/
  - Hooks: src/hooks/
  - Lib: src/lib/
  - App routes: src/app/
- Infrastructure: /Users/gregorydickson/stackpoint/loan/infrastructure/

Tech stack:
- Backend: FastAPI, SQLAlchemy (async), Pydantic, LangExtract, Docling
- Frontend: Next.js 14, TypeScript, shadcn/ui, Tailwind CSS
- Testing: pytest (490 tests, 87% coverage), mypy strict

Recent completion: v2.0 milestone with dual extraction pipelines (Docling + LangExtract)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Run code-simplifier agent on backend Python codebase</name>
  <files>backend/src/**/*.py</files>
  <action>
Run the code-simplifier agent to analyze the backend Python codebase.

Focus areas for the agent:
1. Extraction module (14 files) - largest subsystem, most complex logic
2. API layer - check for repeated error handling patterns
3. Storage layer - repository pattern implementation
4. OCR module - circuit breaker and retry logic

The agent should identify:
- Duplicate code patterns that can be extracted into shared utilities
- Overly complex functions that can be decomposed
- Inconsistent patterns across similar modules
- Opportunities for better abstraction
- Dead code or unused imports

Run command:
```
/code-simplifier
```

Provide the agent with the backend source directory: /Users/gregorydickson/stackpoint/loan/backend/src/

Request analysis organized by module with specific file references and line numbers where simplifications are recommended.
  </action>
  <verify>
Agent produces a structured report covering:
- Number of files analyzed
- Identified simplification opportunities
- Prioritized recommendations
  </verify>
  <done>Code simplification analysis for backend Python code is complete with actionable recommendations</done>
</task>

<task type="auto">
  <name>Task 2: Run code-simplifier agent on frontend TypeScript codebase</name>
  <files>frontend/src/**/*.ts, frontend/src/**/*.tsx</files>
  <action>
Run the code-simplifier agent to analyze the frontend TypeScript codebase.

Focus areas for the agent:
1. Components - check for repeated UI patterns
2. Hooks - custom hook implementations
3. API client layer - data fetching patterns
4. Type definitions - potential consolidation

The agent should identify:
- Repeated JSX patterns that can become shared components
- Similar data fetching logic across pages
- Type definitions that can be shared or simplified
- Prop drilling that could use context
- Component composition opportunities

Run command:
```
/code-simplifier
```

Provide the agent with the frontend source directory: /Users/gregorydickson/stackpoint/loan/frontend/src/

Request analysis organized by area (components, hooks, lib, app) with specific recommendations.
  </action>
  <verify>
Agent produces a structured report covering:
- Number of files analyzed
- Identified simplification opportunities
- Component-level recommendations
  </verify>
  <done>Code simplification analysis for frontend TypeScript code is complete with actionable recommendations</done>
</task>

<task type="auto">
  <name>Task 3: Consolidate findings into prioritized action list</name>
  <files>None (analysis only)</files>
  <action>
Synthesize findings from backend and frontend analyses into a single prioritized recommendation document.

Structure the output as:
1. **High Impact / Low Effort** - Quick wins that provide immediate value
2. **High Impact / High Effort** - Significant improvements requiring more work
3. **Low Impact / Low Effort** - Nice-to-haves for future consideration

For each recommendation include:
- Location (file paths)
- Current state (what exists)
- Proposed simplification
- Expected benefit (LOC reduction, maintainability improvement, etc.)

Present findings in a format suitable for creating follow-up tasks if the user wants to act on recommendations.
  </action>
  <verify>
Consolidated report includes:
- Prioritization matrix
- Specific actionable items
- Estimated impact for each recommendation
  </verify>
  <done>Prioritized simplification roadmap is available for user review</done>
</task>

</tasks>

<verification>
- Code-simplifier agent successfully analyzed both backend and frontend codebases
- Analysis covers all major modules/areas
- Recommendations are specific (file, location, proposed change)
- Prioritization helps user decide what to act on first
</verification>

<success_criteria>
- Backend analysis complete with module-by-module breakdown
- Frontend analysis complete with component/hook/lib breakdown
- Consolidated prioritized action list available
- User has clear next steps if they want to implement simplifications
</success_criteria>

<output>
Present the consolidated findings directly to the user. No SUMMARY.md file needed for quick tasks.
</output>
