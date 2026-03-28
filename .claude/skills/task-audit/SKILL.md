---
name: task-audit
description: Strict read-only audit of task modules for consistency and violations. Use when auditing a task directory for cross-module consistency issues, constraint completeness, or UNIFORM_SUFFIX problems.
disable-model-invocation: true
---

# Task Audit - Read-Only Consistency Checker

Conduct a strict, read-only audit of the task. Your goal is to analyze the existing code for logic, consistency, and expected failure states, reporting any violations.

## STRICT RULE 1: READ-ONLY MODE

Do NOT modify, rewrite, or attempt to fix any scripts or code during this task. You are acting strictly as an auditor. Your final output must ONLY consist of your analysis and a comprehensive list of violation cases.

## STRICT RULE 2: ANTI-LAZINESS & EXHAUSTIVE COMPLETENESS

Do NOT stop after finding 1 or 2 errors. Provide an EXHAUSTIVE, line-by-line enumeration of EVERY SINGLE violation within the task directory.

## Audit Steps

### Step 1: Cross-Module Consistency Audit
Review all modules within the task directory (environment.py, evaluator.py, feedback.py, prompt.py, stages.py, renderer.py).

**Expected Outcome:** All modules must be logically consistent. The physical mechanics and parameters defined in the underlying environment MUST perfectly align with the evaluation logic and prompt descriptions.

**Action:** Document EVERY SINGLE discrepancy, logical conflict, or misaligned physics across these files.

### Step 2: Information Consistency & Variable Audit

#### 1. Constraint Completeness (The "Constraint Variable" Rule)
- **Definition:** A "Constraint Variable" is ANY variable that defines an absolute maximum, minimum, or failure threshold required to logically solve the task.
- **Audit Rule:** ALL necessary structural limits and boundaries must be explicitly stated in the initial prompt with their exact numerical values. This applies even if the limit is physically invisible.
- **Action:** Scan environment.py for ANY hardcoded constraint numbers. Verify they are correctly exposed in prompt.py.

#### 2. Mutation Synchronization (Updating "Constraint" & "Visible" Variables)
- **Definition:** A "Visible Variable" refers to observable physical properties explicitly mentioned in the prompt.
- **Audit Rule:** If stages.py modifies ANY "Constraint Variable" OR "Visible Variable" mentioned in the prompt, the prompt string MUST be dynamically updated to reflect the new value with format: `[new_value] (originally [old_value] in the source environment)`.
- **Action:** Dry-run EVERY SINGLE regex logic block in stages.py to ensure it outputs the exact required format.

#### 3. Hidden Physics Protection (The "Invisible Variable" Rule)
- **Definition:** "Invisible Variables" are underlying environmental constants that are NOT limits or constraints (e.g., gravitational acceleration, global friction coefficients).
- **Audit Rule:** The exact numerical values or directions of change of Invisible Variables MUST NOT be mentioned in the prompt. Only the name as a general warning in UNIFORM_SUFFIX is allowed.
- **Action:** Document EVERY instance where an INVISIBLE environmental constant's specific value is leaked.

### Step 3: The `UNIFORM_SUFFIX` Audit (The "Union" Rule)
- **Audit Rule:** The `UNIFORM_SUFFIX` MUST dynamically list the **UNION** of all physical variables that have been modified across Stage-1 through Stage-4.
- **Format Restriction:** The suffix must ONLY provide a general warning about *what* might have changed, NEVER pinpointing exact mutations or values.
- **Action:** Document EVERY instance where UNIFORM_SUFFIX fails to include a modified variable OR violates the tone.

## Final Deliverable

Provide an exhaustively detailed list of all violations categorized by step. If a category has no violations, explicitly state "No violations found for [Category]". Do not summarize.

## Input
The task directory path in the format: `tasks/<Category>/<TaskID>`, e.g., `tasks/Category1_Statics_Equilibrium/S_01`.
