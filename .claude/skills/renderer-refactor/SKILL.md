---
name: renderer-refactor
description: Refactor renderer.py for precision and academic aesthetics. Use when visual rendering needs standardization across tasks.
disable-model-invocation: true
---

# Renderer Refactor - Academic Visual Standardization

Your task is to refactor, standardize, and audit the `renderer.py` module for precision, professional aesthetics, and comprehensive viewport coverage.

## STRICT RULE: ISOLATED MODIFICATION

You are STRICTLY PROHIBITED from modifying any file other than `renderer.py`. You have STRICTLY READ-ONLY access to all other modules.

## Audit Steps

### Step 1: Physical Fidelity Audit
- Ensure renderer.py provides an absolutely precise simulation of all physical properties, boundaries, and test-passing criteria defined in environment.py, evaluator.py, etc.
- Meticulously review all physics variables. Identify and correct any logic in the renderer that contradicts or deviates from the baseline or mutated task mechanics.

### Step 2: Visuality & Format Standardization (Academic Focus)

Enforce a strict, uniform standard across all tasks:

**Specific Academic Color Palette:**
- **Background:** `#000000` (Pure Black)
- **Environmental Baseline (Terrain, walls, target zones):** `#E6C229` (Goldenrod Yellow)
- **Agent-Created Structure (Tools/Joints/Beams):** `#4CAF50` (Material Green)

**Panoramic Camera Viewport:** Meticulously adjust the camera's viewport bounds, scale, and offset to capture the complete range of the entire structure. Resolve issues like partial cutoffs.

**Mandatory Aspect Ratio:** Enforce a consistent `16:9` aspect ratio for all rendered output.

### Step 3: Sequential Validation & Visualization

1. Run the reference solution in `agent.py` to execute and save the updated GIF (usually via `test_agent.py`).
2. If `test_stage_solutions.py` exists, execute it to run reference solutions across all four mutated stages and save newly rendered GIFs.

## Final Deliverable

Report any findings requiring corrections in other modules as violation cases. Only modify renderer.py.

## Input
The task directory path in the format: `tasks/<Category>` for category-wide refactoring or `tasks/<Category>/<TaskID>` for single-task, e.g., `tasks/Category6_ExoticPhysics`.
