# Sprint Contract — Force Explicit Planning Before Building

## When to Use

Invoke this skill when starting a new task iteration or when previous attempts are failing without clear progress.

## What It Does

Before generating code, the agent must fill out a **Sprint Contract** — a structured commitment that answers:

1. **Mechanism Type** — What kind of structure/mechanism am I building?
2. **Key Physical Insight** — What is the single most important physical principle?
3. **Critical Parameters** — What specific values am I setting and WHY (derived from physics, not guesswork)?
4. **How I Will Verify It Works** — What specific outcome proves success?
5. **What I Think Will Go Wrong First** — Where do I expect failure?

## Why It Matters

From Anthropic's harness engineering research: "If a task you can't say clearly what 'done' looks like, it's probably not suitable to hand directly to an agent."

The Sprint Contract forces the agent to:
- Move from "try stuff and hope" → explicit physical reasoning
- Commit to specific parameters before building (not random tweaking)
- Anticipate failure modes instead of being surprised

## Sprint Contract Template

```
## Sprint Contract

### 1. Mechanism Type
(e.g., "bridge with tension cables", "4-wheel vehicle with active steering")

### 2. Key Physical Insight
The single most important physical principle that makes this design work.

### 3. Critical Parameters I Am Setting
| Parameter | Value | Why This Value |
|-----------|-------|----------------|
| wheel_radius | 1.5m | Derived from obstacle heights |
| motor_torque | 1800 N·m | Calculated from grade angle |

### 4. How I Will Verify It Works
- Vehicle reaches x=30m without joints breaking
- Structure mass < 2000kg
- No airborne rotation > 180°

### 5. What I Think Will Go Wrong First
- Mid-span joint will break due to shear → need reinforced joints
```

## How to Apply

When working on a task, include the Sprint Contract in your reasoning before writing code. This is especially valuable when:

- Starting a new task category (not sure what design pattern works)
- Previous attempts failed without clear diagnosis
- The task involves multiple competing constraints

## Relationship to Other Skills

- Use with `task-audit` when debugging cross-module consistency issues
- Use with `feedback-refactor` when feedback is too sparse to fill out the contract
- Use with `forensic-failure-analysis` when diagnosis is unclear
