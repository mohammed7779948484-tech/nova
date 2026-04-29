# [PROJECT_NAME] Constitution
<!-- Example: Spec Constitution, TaskFlow Constitution, etc. -->

## Core Principles

### [PRINCIPLE_1_NAME]
<!-- Example: I. Library-First -->
[PRINCIPLE_1_DESCRIPTION]
<!-- Example: Every feature starts as a standalone library; Libraries must be self-contained, independently testable, documented; Clear purpose required - no organizational-only libraries -->

### [PRINCIPLE_2_NAME]
<!-- Example: II. CLI Interface -->
[PRINCIPLE_2_DESCRIPTION]
<!-- Example: Every library exposes functionality via CLI; Text in/out protocol: stdin/args → stdout, errors → stderr; Support JSON + human-readable formats -->

### [PRINCIPLE_3_NAME]
<!-- Example: III. Test-First (NON-NEGOTIABLE) -->
[PRINCIPLE_3_DESCRIPTION]
<!-- Example: TDD mandatory: Tests written → User approved → Tests fail → Then implement; Red-Green-Refactor cycle strictly enforced -->

### [PRINCIPLE_4_NAME]
<!-- Example: IV. Integration Testing -->
[PRINCIPLE_4_DESCRIPTION]
<!-- Example: Focus areas requiring integration tests: New library contract tests, Contract changes, Inter-service communication, Shared schemas -->

### [PRINCIPLE_5_NAME]
<!-- Example: V. Observability, VI. Versioning & Breaking Changes, VII. Simplicity -->
[PRINCIPLE_5_DESCRIPTION]
<!-- Example: Text I/O ensures debuggability; Structured logging required; Or: MAJOR.MINOR.BUILD format; Or: Start simple, YAGNI principles -->

## [SECTION_2_NAME]
<!-- Example: Additional Constraints, Security Requirements, Performance Standards, etc. -->

[SECTION_2_CONTENT]
<!-- Example: Technology stack requirements, compliance standards, deployment policies, etc. -->

## [SECTION_3_NAME]
<!-- Example: Development Workflow, Review Process, Quality Gates, etc. -->

[SECTION_3_CONTENT]
<!-- Example: Code review requirements, testing gates, deployment approval process, etc. -->

## VI. PDCA Quality Gates (NON-NEGOTIABLE)

Enforced via [PDCA Framework](.agent/skills/pdca/SKILL.md) — see full reference in `references/` directory.

**6.1 TDD Mandatory**
Every implementation task MUST have a corresponding test task that is written and verified to FAIL before implementation begins. Red-Green-Refactor cycle is strictly enforced. No exceptions.

**6.2 Called Shot Protocol**
Before writing ANY test, the agent MUST announce:
1. **Test name**: Descriptive name of the test
2. **Behavior under test**: What observable behavior this verifies
3. **Expected failure**: The exact assertion message or error expected when test runs red

If actual failure ≠ expected failure → **STOP** — the test is testing the wrong thing.

**6.3 Test Ordering (Mandatory Sequence)**
For every feature, tests MUST follow this order:
1. Degenerate/zero case first (empty state, null input, no items)
2. 1-2 exception cases (invalid input, error conditions)
3. Happy path incrementally (Fake It → Obvious Implementation → Triangulate)
4. Remaining exception cases
5. NEVER stop with only happy path coverage

**6.4 Completeness Check Gate**
After completing each User Story phase, run PDCA Check:
- All tests passing
- No TODO implementations remaining
- No untested code committed
- See: `.agent/skills/pdca/references/check-prompts.md`

**6.5 Retrospective**
After full implementation, run PDCA Act retrospective:
- Identify critical moments that impacted success/failure
- Start / Stop / Keep analysis
- ONE thing to change for next cycle
- See: `.agent/skills/pdca/references/act-prompts.md`

**6.6 Testing Anti-Patterns (Prohibited)**
The following are STRICTLY FORBIDDEN:
- ❌ Choosing mock behavior over system behavior
- ❌ Mocking without understanding (run real implementation first)
- ❌ Incomplete mocks (must reflect full API shape)
- ❌ Test-only methods in production code
- ❌ Tests written after code (if it never failed, it proves nothing)
- ❌ Integration tests as afterthought (add from the start)
- ❌ Vacuous greens (test that passes against a trivial stub)
- See: `.agent/skills/pdca/references/testing-anti-patterns.md`

## Governance
<!-- Example: Constitution supersedes all other practices; Amendments require documentation, approval, migration plan -->

[GOVERNANCE_RULES]
<!-- Example: All PRs/reviews must verify compliance; Complexity must be justified; Use [GUIDANCE_FILE] for runtime development guidance -->

**Version**: [CONSTITUTION_VERSION] | **Ratified**: [RATIFICATION_DATE] | **Last Amended**: [LAST_AMENDED_DATE]
<!-- Example: Version: 2.1.1 | Ratified: 2025-06-13 | Last Amended: 2025-07-16 -->
