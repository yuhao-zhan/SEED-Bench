---
name: api-audit
description: Audit API architecture for a task to prevent reference solutions from "cheating". Use when reviewing if agent.py uses prohibited environment manipulations.
disable-model-invocation: true
---

# API Audit - Read-Only Architecture Checker

Your task is to audit the API architecture for a specific task. This ensures rigorous environmental interaction and prevents reference solutions from "cheating" by directly manipulating internal physics states.

## STRICT RULE: READ-ONLY AUDIT

You must ONLY check, analyze, and report your findings. Do NOT modify, rewrite, or save any scripts during this phase!

## Audit Steps

### Step 1: Comprehensive API Documentation & Prompt Alignment
- Verify that the API collection in `primitives_api.json` provides highly concrete and faithful documentation for this task.
- Ensure that every single API employed in `agent.py` is explicitly recorded in `primitives_api.json`.

### Step 2: Reference Solution Audit (Eradicating Prohibited APIs)

#### ALLOWED Actions:
- **Read-Only Access:** Accessing internal variables to read states is permitted (e.g., `_world`, `_bodies`, `_terrain_bodies`).
- **Tool Manipulation:** Modifying the physical properties of *dynamically created tools* is permitted (e.g., changing `v.linearVelocity`, `v.angle`, `v.ApplyTorque`, `v.angularVelocity` of tools spawned by the agent).

#### PROHIBITED Actions:
- **Environment Manipulation:** Directly modifying physics properties derived from the underlying environmental baseline is STRICTLY PROHIBITED (e.g., directly altering `f.friction` of the environment itself).

## Final Deliverable

Provide a detailed report listing:
1. Any APIs in agent.py not documented in primitives_api.json
2. Any prohibited environment manipulations found
3. Any discrepancies between documented and actual API usage

## Input
The task directory path in the format: `tasks/<Category>/<TaskID>` or `tasks/<Category>` for category-wide audits, e.g., `tasks/Category2_Kinematics_Linkages/K_01`.
