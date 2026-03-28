---
name: mutated-reference-solution
description: Implement, test, and verify reference solutions for mutated tasks. Use when creating reference solutions for Stage-1 through Stage-4 mutated environments in a task directory.
---

# Mutated Reference Solution Generator

Your task is to implement, test, and verify the reference solutions for mutated tasks in a task directory.

## Core Objective
Create new, independent functions in agent.py to store the reference solution for each mutated task (e.g., `build_agent_stage_3` and `agent_action_stage_3`). The initial reference solution (`build_agent` and `agent_action`) should PASS the initial env but FAIL on all mutated tasks.

## Workflow

### Step 1: Physical Analysis & Feasibility Check
Read stages.py to identify the mutated physical elements and parameters. Conduct a fine-grained theoretical physical analysis to determine if the mutated task remains physically solvable.

#### If unsolvable:
Redesign the mutated environment to make it solvable by logically modifying the mutated elements in stages.py. Environment.py, feedback.py, evaluator.py, prompt.py, stages.py MUST be coherent and consistent!

#### If solvable:
Proceed directly to Step 2.

### Step 2: Implement Reference Solutions
Create new, independent functions in agent.py for each mutated task. Base your new implementations on the logic found in the initial environment's reference solution.

Organize functions cleanly - each mutated task's solution should be completely isolated.

### Step 3: Testing & Debugging
Run tests to check how the initial reference solution performs in each mutated environment. The ideal situation is:
- Initial reference solution PASSES the initial env
- Initial reference solution FAILS on all four mutated tasks

Test every newly created reference solution within its corresponding mutated environment. If a test fails, continuously debug until it passes. Do not move on to the next mutated task until the current one is fully resolved.

## Strict Rules
- DO NOT modify the existing `build_agent` and `agent_action` functions dedicated to the initial environment.
- DO NOT stop debugging a mutated task until its tests pass.

## Input
The task directory path in the format: `tasks/<Category>/<TaskID>`, e.g., `tasks/Category5_Cybernetics_Control/C_02`.
