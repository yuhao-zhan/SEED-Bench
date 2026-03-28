---
name: feedback-refactor
description: Transform feedback from summative to high-resolution forensic feedback. Use when feedback needs to be more diagnostic and process-aware.
disable-model-invocation: true
---

# Feedback Refactor - Forensic Feedback Optimization

Your task is to refactor and significantly enhance the `feedback.py` module. Transform feedback from "binary/summative" into "process-aware/diagnostic" feedback.

## Strict Constraints & Ground Rules

1. **Module Immutability:** You are ONLY allowed to modify `feedback.py`. The `environment.py`, `evaluator.py`, `prompt.py`, and `stages.py` files are the absolute GROUND TRUTH.

2. **No Information Hallucination:** Explicitly extract hidden physical states from the `metrics` dict returned by `evaluator.evaluate()`. Do NOT report metrics that do not exist in the code.

3. **The "No-Spoilers" Rule:**
   - BAD: "Your linkage is too heavy. Decrease density to 5.0 and add a cross-brace."
   - GOOD: "The structure failed due to self-weight exceeding the joint torque limit."

4. **Dynamic Thresholding:** The physics environments mutate across stages. Your feedback.py MUST NEVER hardcode environmental thresholds.
   - BAD: `if metrics['mass'] > 1200:`
   - GOOD: `max_mass = metrics.get('max_structure_mass', float('inf'))`

## Refactoring Requirements

### 1. `format_task_metrics(metrics)` -> The Baseline
Expose high-resolution physical metrics without giving suggestions.
- Expose peak forces, torques, boundary margin proximity
- Phase-Specific Segregation
- Only include metrics provided in the metrics dict

### 2. `get_improvement_suggestions(metrics, ...)` -> The System Feedback
Generate actionable diagnostic warnings without giving the answer.

- **Multi-Objective Trade-off Paradox:** Point out if agent perfects one metric but severely fails another.
- **Root-Cause Chain Identification:** Help agent understand *what broke first*.
- **Physics Engine Limits:** Warn about "numerical instability" if metrics show impossible spikes.

## Execution Steps

1. **Deep Read & Domain Identification:** Analyze ground truth files. Map out all physical constraints, mutated stages, and APIs.
2. **Rewrite `feedback.py`:** Make the complete, refactored Python code.
3. **Self-Summary:** Briefly state which physics domain you optimized for and how thresholds adapt.

## Verification

After implementing changes:
1. Execute mutated tests to confirm initial reference solution passes base but fails mutants.
2. Audit the failure logs to verify forensic data (timing, locations, forces) is present.

## Input
The task directory path in the format: `tasks/<Category>/<TaskID>`, e.g., `tasks/Category6_ExoticPhysics/E_01`.
