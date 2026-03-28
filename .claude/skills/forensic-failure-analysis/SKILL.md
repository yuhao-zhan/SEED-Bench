---
name: forensic-failure-analysis
description: Analyze execution logs to determine root causes of LLM failure. Use when an LLM agent failed and you need to understand why through forensic analysis of execution logs.
---

# Forensic Failure Analysis

You are an expert Embodied AI evaluator, physical simulation analyst, and code reviewer. Analyze execution logs to determine root causes of failure.

## Warning: Data Scale

The JSON contains a very long execution record across many iterations, including code modifications, scores, physical metrics, and feedback loops. Pay careful attention to nuances of every iteration.

## Core Analysis Requirements

Analyze the execution log and provide a detailed report addressing these 5 dimensions:

### 1. System-Level Errors & Environment Faults
- Is the task setup missing critical physical constraints, boundary conditions, or necessary environmental information?
- Are there signs that the agent was forced to "guess" parameters?
- Did the agent misuse or invent APIs?

### 2. LLM Physical Reasoning Capacity
- Is the agent demonstrating genuine multi-step physical reasoning?
- Or is it merely engaging in blind "parameter tweaking"?
- Did the agent correctly identify the root physical cause of failures?

### 3. Feedback Sparsity & Quality
- Is the feedback too sparse (e.g., only final score)?
- Does the feedback lack "process-aware" physical metrics?
- Did the lack of detailed feedback contribute to failure?

### 4. Unanticipated Failure Mechanisms
- Did the agent get trapped in a local minimum?
- Were there conflicts between physical properties the agent set?
- Did a design break the physics engine?

### 5. Trajectory of True Improvement
- Was there any true evolution in policy or solution architecture?
- Plot the trajectory of best_score and physical metrics over time.
- Did the agent actually learn from previous iterations?

## Output Format

Structure your response using clear headings for the 5 points. Cite specific iteration numbers, code snippets, and metric changes to back up claims.

## Input

Provide the evaluation results JSON file paths. The expected path template is:

```
evaluation_results/<Category>/<Task>/<Model>/<Method>/all_Initial_to_Stage-<N>.json
```

For example, for a Qwen3-8B baseline run across 4 stages:
```
evaluation_results/Category1_Statics_Equilibrium/S_04/Qwen3-8B/baseline/all_Initial_to_Stage-1.json
evaluation_results/Category1_Statics_Equilibrium/S_04/Qwen3-8B/baseline/all_Initial_to_Stage-2.json
evaluation_results/Category1_Statics_Equilibrium/S_04/Qwen3-8B/baseline/all_Initial_to_Stage-3.json
evaluation_results/Category1_Statics_Equilibrium/S_04/Qwen3-8B/baseline/all_Initial_to_Stage-4.json
```

Replace `<Category>`, `<Task>`, `<Model>`, `<Method>`, and `<N>` with the actual values for the task being analyzed.
