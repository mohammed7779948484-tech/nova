# Check Phase: Implementation Verification & Quality Audit

**Purpose:** Verify all objectives met and process discipline maintained
**When to use:** After completing all planned implementation steps
**Prerequisites:** All planned work completed, tests passing
**Expected output:** Verification checklist, process audit results, outstanding items list
**Typical duration:** 2-5 minutes
**Next step:** Retrospection (4) for continuous improvement

---

> **Tool check:** Before running this check, is there an agent tool to see all uncommitted changes?

```
**Completeness Check**

Review our original goal outcome and plan against our execution.

**Verification:**
- [ ] All tests passing
- [ ] Manual smoke test completed successfully 
- [ ] Documentation updated
- [ ] No regressions introduced
- [ ] No TODO implementations remaining created by this test driving

**Process Audit:**
- [ ] Testing approach was followed consistently
- [ ] TDD discipline maintained (if chosen)
- [ ] Test coverage is adequate and appropriate
- [ ] No untested implementation was committed
- [ ] Simple test scenarios were effective


**Structural Review:**
- [ ] What structural improvements did this implementation reveal? (discovered during Do only — no speculative cleanup)
- [ ] If identified: implement as separate `refactor:` commits with all tests still passing
- [ ] If none: confirm scope is structurally clean

**Status:** [Complete/Needs work]
**Outstanding items:** [any remaining tasks]
**Ready to close:** [Yes/No with reasoning]

```

> **Tool check:** Is there an agent tool to surface code quality improvements in what changed? One to catch security concerns?

Add Results to Ticket.


---

