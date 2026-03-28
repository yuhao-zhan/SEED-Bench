---
name: audit_variable_classification
description: Variable classification for task audit and _CE evaluation mode rules
type: reference
---

# Task Audit: Variable Classification

## Three Types

1. **Constraint Variable** — hard design limit agent must respect (max mass, max force/torque, beam size, max wheels). **Must be exposed** even if agent can't "see" it (e.g., joint_max_force is invisible but is a CONSTRAINT, not Invisible).

2. **Visible Variable** — observable geometry in the scene (gap width, cliff height, platform position). **Must be exposed** if mentioned in prompt.

3. **Invisible Variable** — environmental physical constant agent cannot observe by looking (gravity, wind force magnitude, earthquake frequency/amplitude, wind_oscillation_frequency, wind_shear_factor, damping coefficients). **Must NEVER expose specific values.**

## Priority Rule
**Constraint beats Invisible**: If a variable is BOTH a design limit AND something the agent can't directly observe → treat as Constraint and expose.

## UNIFORM_SUFFIX Rule
All variables modified in any stage (Stage-1 through Stage-4) — regardless of type — must appear in UNIFORM_SUFFIX. Only the variable name as a generic warning is allowed; never specific values or directions of change, e.g., "- **Joint force resilience**: The maximum linear force structural joints can withstand before failing."

## _CE Mode
"_CE" = Change Exposure. An evaluation mode where _CE stages intentionally expose variable changes to solver. **Do NOT flag _CE as a violation.**
