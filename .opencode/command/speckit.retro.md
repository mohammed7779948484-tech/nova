---
description: Run a PDCA retrospective after implementation to capture learnings and improve the next development cycle.
handoffs:
  - label: Start New Feature
    agent: speckit.specify
    prompt: Begin next feature specification with learnings from retrospective
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Pre-Execution Checks

**Check for extension hooks (before retrospective)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_retro` key
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
  - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Pre-Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **Mandatory hook** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Pre-Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}

    Wait for the result of the hook command before proceeding to the Outline.
    ```
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently

## Outline

1. **Setup**: Run `.specify/scripts/bash/check-prerequisites.sh --json` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Load context for retrospective**:
   - **REQUIRED**: Read tasks.md — count total planned tasks vs completed [X] tasks
   - **REQUIRED**: Read spec.md — compare original requirements against implementation
   - **IF EXISTS**: Read checklists/ — count checklist completion rates
   - **IF EXISTS**: Read plan.md — compare planned vs actual approach
   - **REQUIRED**: Read `.agent/skills/pdca/references/act-prompts.md` for retrospective guide

3. **Collect Metrics**:
   - **Task Completion**: Total planned vs completed (percentage)
   - **Test Coverage**: How many test tasks were written and passed
   - **Checklist Status**: Completion rate across all checklists
   - **TDD Compliance**: Were Called Shots used? Was Red-Green-Refactor followed?
   - **Specification Accuracy**: Did implementation match original spec? Any deviations?

4. **Process Review** (PDCA Act Phase):
   
   Answer the following based on the full implementation session:
   
   **Critical Moments** (2-3 events that most impacted success or failure):
   - What was the moment? What happened? What was the outcome?
   
   **Start / Stop / Keep**:
   - **START**: What should we begin doing in the next cycle that we didn't do this time?
   - **STOP**: What should we stop doing that hindered progress or quality?
   - **KEEP**: What worked well and should be repeated?
   
   **ONE Thing**: If you could only change ONE thing about the process for the next cycle, what would it be and why?

5. **Generate retro.md**: Write the retrospective to `{FEATURE_DIR}/retro.md` using this structure:

   ```markdown
   # Retrospective: [Feature Name]
   
   **Date**: [current date]
   **Feature**: [feature directory name]
   **PDCA Cycle**: [Plan → Do → Check → Act]
   
   ## Metrics
   
   | Metric | Planned | Actual | Status |
   |--------|---------|--------|--------|
   | Tasks | X | Y | Z% |
   | Tests | X | Y | Z% |
   | Checklists | X | Y | Z% |
   
   ## Critical Moments
   
   1. [Moment description and impact]
   2. [Moment description and impact]
   3. [Moment description and impact]
   
   ## Start / Stop / Keep
   
   - **START**: [action item]
   - **STOP**: [action item]
   - **KEEP**: [action item]
   
   ## ONE Thing to Change
   
   [If you could only change one thing for next cycle, what and why?]
   
   ## Specification Accuracy
   
   - Deviations from spec: [list any]
   - Unplanned additions: [list any]
   - Spec improvements for next time: [suggestions]
   
   ## PDCA Compliance
   
   - Called Shot used: [yes/partially/no]
   - TDD Red-Green-Refactor: [yes/partially/no]
   - Anti-patterns detected: [none/list]
   - Check Gate passed: [yes/partially/no]
   
   ## Action Items for Next Cycle
   
   1. [Action item from retrospective]
   2. [Action item from retrospective]
   3. [Action item from retrospective]
   ```

6. **Update AGENTS.md**: Between the `<!-- SPECKIT START -->` and `<!-- SPECKIT END -->` markers, add key learnings from the retrospective that should inform the next feature development cycle.

7. **Check for extension hooks**: After generating retro.md, check if `.specify/extensions.yml` exists in the project root.
   - If it exists, read it and look for entries under the `hooks.after_retro` key
   - If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally
   - Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
   - For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
     - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
     - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
   - For each executable hook, output the following based on its `optional` flag:
     - **Optional hook** (`optional: true`):
       ```
       ## Extension Hooks

       **Optional Hook**: {extension}
       Command: `/{command}`
       Description: {description}

       Prompt: {prompt}
       To execute: `/{command}`
       ```
     - **Mandatory hook** (`optional: false`):
       ```
       ## Extension Hooks

       **Automatic Hook**: {extension}
       Executing: `/{command}`
       EXECUTE_COMMAND: {command}
       ```
   - If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently
