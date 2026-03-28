---
name: difficulty-escalation
description: Overhaul mutated environments with severe difficulty increases. Use when current mutated tasks are too easy and need fundamental redesign to test reasoning limits.
---

# Difficulty Escalation for Mutated Tasks

Your task is to completely overhaul the current mutated environments to introduce severe, essential difficulty increases. The current tasks may be too naive, allowing LLMs to succeed by simply tweaking the original reference solution.

## Core Objective
Create fundamentally complex, physics-based challenges that rigorously test the agent's reasoning limits.

## Step 1: Essential Difficulty Escalation (Structural Innovation)

**Prohibited:** Do NOT simply scale existing parameters (e.g., merely increasing weight, distance, gravity, or quantity).

**Required - Innovation within Constraints:**

- **Stage-1 & Stage-2 (Single Variable Limit):** While these stages should generally change ONLY one physical variable, innovate by introducing a variable that creates a critical threshold or a non-linear challenge.
  - *Example:* Instead of just "wider gap," introduce a "zero-friction surface" on the bridge deck, "fragile anchor points" with very low joint strength, or "constant lateral wind force."

- **Stage-3 & Stage-4 (Multi-Variable Complexity):** Combine multiple physical changes to create conflicting constraints. The agent should have to balance competing requirements. Difficulty must be increasing across stages.

- **Fundamental Challenges:** Construct scenarios requiring multi-step physical reasoning, handling of unforeseen structural barriers, or overcoming complex environmental mechanisms.

## Step 2: Information Hiding & Embodied Discovery

**Implicit Mechanics & Uniform Suffix (DYNAMIC GENERATION REQUIRED):**

Do NOT spoon-feed all fine-grained environmental conditions. The agent must encounter the difficulty through trial.

Create and use a **uniform `task_description_suffix`** across all stages. The suffix must list the **UNION** of all physical variables that have been modified across Stage-1, Stage-2, Stage-3, and Stage-4 in stages.py.

**Format Template:**
```
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - [Variable 1]: [Brief, general description of its potential physical effect]
 - [Variable 2]: [Brief, general description of its potential physical effect]
 - [Variable N...]: [...]

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning.
```

**Interaction-Driven:** Design the environment so the agent is forced to discover specific phenomena only through active interaction.

**Theoretical Solvability:** While specific mechanics are hidden, the basic rules MUST be logically sufficient for a human expert to deduce the solution.

## Step 3: Implementation, Validation & Visualization

1. **Environment Overhaul:** Update `stages.py` (and `environment.py` if necessary) to implement high-difficulty mutations. Ensure `task_description_suffix` uses the UNIFORM_SUFFIX.

2. **Reference Solution Update (CONDITIONAL):** If `agent.py` contains stage-specific reference solutions, update them to solve the new high-difficulty mutations. If it only contains initial reference solution, do NOT write new ones.

3. **Rigorous Validation:** Test stage-specific reference solutions - they must consistently pass the new high-difficulty environment tests.

4. **Visualization:** If reference solutions were updated, save GIFs demonstrating successful execution.

## Step 4: Baseline Failure Check (MANDATORY)

Verify that the **initial reference solution**:
- CAN still pass the initial environment
- ABSOLUTELY FAILS on all 4 mutated environments

If the initial reference solution accidentally succeeds, the difficulty increase is invalid.

## Strict Rules
- DO NOT modify the existing `build_agent` and `agent_action` functions dedicated to the initial environment.
- The initial reference solution MUST fail on all mutated environments.
- If stage-specific solutions exist, DO NOT stop debugging them until tests pass.

## Input
The task directory path in the format: `tasks/<Category>/<TaskID>`, e.g., `tasks/Category5_Cybernetics_Control/C_01`.
