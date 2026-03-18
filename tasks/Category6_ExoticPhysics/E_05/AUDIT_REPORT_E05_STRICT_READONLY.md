# E-05 (The Magnet) — Strict Read-Only Audit Report

**Scope:** `tasks/Category6_ExoticPhysics/E_05` (all modules).  
**Rules:** Read-only; no code changes. Exhaustive, line-by-line parameter trace and violation enumeration.

---

## Step 1: Cross-Module Consistency Audit

### 1.1 Physical Parameters in `environment.py` — Full List and Trace

| # | Parameter | Location (environment.py) | Type / Default | Trace to Other Modules |
|---|-----------|---------------------------|----------------|-------------------------|
| 1 | `BODY_START_X` | Line 59, class constant `8.0` | Constant | **prompt.py** L27: "x=8.0m". **evaluator.py** L25: `body_start_x` from `terrain_bounds.get("body_start", {}).get("x", 8.0)`; bounds come from `get_terrain_bounds()` which uses `self._body_start_x` (L88: from `terrain_config.get("body_start_x", self.BODY_START_X)`). Default run: 8.0. **Consistent.** |
| 2 | `BODY_START_Y` | Line 60, class constant `5.0` | Constant | **prompt.py** L27: "y=5.0m". **evaluator.py** L26: `body_start_y` from bounds, default 5.0. **Consistent.** |
| 3 | `TARGET_X_MIN` | Line 62, class constant `28.0` | Constant | **prompt.py** L28, L42: "[28.0, 32.0]". **evaluator.py** L22: from `tz.get("x_min", 28.0)`; `tz` from `get_terrain_bounds()` which returns `self.TARGET_X_MIN` (L187). **renderer.py** L93: `tz.get("x_min", 28.0)`. **agent.py** L3: `TARGET_X_MIN = 28.0`. **Consistent.** |
| 4 | `TARGET_X_MAX` | Line 63, class constant `32.0` | Constant | Same pattern: prompt, evaluator, renderer, agent all 32.0. **Consistent.** |
| 5 | `TARGET_Y_MIN` | Line 64, class constant `6.0` | Constant | prompt L28, L42 "6.0"; evaluator L24; renderer L95; agent L7. **Consistent.** |
| 6 | `TARGET_Y_MAX` | Line 65, class constant `9.0` | Constant | prompt, evaluator, renderer, agent 9.0. **Consistent.** |
| 7 | `MAX_STEPS` | Line 67, class constant `10000` | Constant | **prompt.py** L43: "10,000 simulation steps". Evaluator receives `max_steps` as argument (L31, L60, L113); caller must supply 10000. **Consistent.** |
| 8 | `MAGNET_R_MIN` | Line 70, constant `0.5` | Internal | Used only in `step()` (L145) to clamp distance; not exposed. No prompt or evaluator reference. **Consistent (internal only).** |
| 9 | `gravity` | L77, `physics_config.get("gravity", (0, -10))` | Physics | Not in prompt (invisible). Stages 2–4 mutate. **Consistent.** |
| 10 | `linear_damping` | L78, default `0.28` | Physics | Not in prompt. Stage-3 mutates to 2.0. **Consistent.** |
| 11 | `angular_damping` | L79, default `0.15` | Physics | Not in prompt. Not mutated in any stage. **Consistent.** |
| 12 | `magnets` | L84, `terrain_config.get("magnets", default_magnets())` | Terrain | Invisible; not in prompt. All stages set `magnets` in terrain_config (Stage-1 different layout; 2–4 default). **Consistent.** |
| 13 | `max_thrust` | L85, `terrain_config.get("max_thrust", 165.0)` | Terrain | **prompt.py** L30, L46: "165.0". Stages 3–4 set `max_thrust: 500.0`. **stages.py** updates prompt via `update_task_description_for_visible_changes` / `update_success_criteria_for_visible_changes`. **Consistent.** |
| 14 | `body_start_x` / `body_start_y` | L87–88, from `terrain_config` | Terrain | Defaults 8.0, 5.0. Not mutated in any stage. **Consistent.** |
| 15 | Ground: `ground_length` 45, `ground_height` 1, friction 0.4 | L99–106 | Internal | Not in prompt; not a success/failure threshold. **Consistent.** |
| 16 | Body fixture: w 0.8, h 0.4, density 30, friction 0.3, restitution 0.1 | L114–122 | Internal | Not in prompt. **Consistent.** |

**Note:** Target zone bounds are class attributes in `environment.py` (L186–191), not read from `terrain_config`, so they are never mutated by stage configs. No cross-module mismatch.

### 1.2 Pit Zone (Evaluator-Only Rule)

- **evaluator.py** L55: `in_pit = (16 <= x <= 24) and y < 5.5`; L56–58: instant fail if in pit and not success.
- **prompt.py** L29: "the region 16 m <= x <= 24 m with y < 5.5 m before reaching the target, the run fails immediately."
- **environment.py:** No pit geometry; pit is an evaluation rule only. **Consistent.**

### 1.3 Evaluator Logic vs Environment

- Success: body in `[target_x_min, target_x_max]` x `[target_y_min, target_y_max]` (L49–52).
- Failed: (1) in pit and not success, or (2) `step_count >= max_steps - 1` and not success (L55–61).
- `done`: `failed or (step_count >= max_steps - 1)` (L113).
- Progress score (L67–70): `max_dist = target_x_min - start_x` (20.0 for default 28, 8); `progress = dist_traveled / max_dist`; score = progress * 80 until success/fail. **Consistent with environment and prompt.**

### 1.4 Renderer vs Environment

- **renderer.py** L91–98: Target zone from `sandbox.get_terrain_bounds()["target_zone"]` with defaults 28, 32, 6, 9. **Consistent.**

### 1.5 Feedback vs Evaluator

- **feedback.py** uses only `metrics` from evaluator (progress_x, dist_to_target, body_x/y, velocity, speed, failure_reason). No hardcoded thresholds that conflict with evaluator. **Consistent.**

**Step 1 conclusion:** No cross-module consistency violations found.

---

## Step 2: Information Consistency & Visibility Audit

### 2.1 Constraint Completeness (VISIBLE — All Required Limits in Prompt)

Audit rule: Every structural limit needed to solve the task must appear explicitly in the initial prompt.

| Structural limit / threshold | In environment / evaluator | In prompt.py | Result |
|-----------------------------|----------------------------|--------------|--------|
| Body start (8, 5) | environment L59–60, 88–89; evaluator L25–26 | L27: "x=8.0m, y=5.0m" | Present |
| Target zone x [28, 32], y [6, 9] | environment L62–65; evaluator L21–24 | L28, L42 | Present |
| Forbidden region (pit) 16 ≤ x ≤ 24, y < 5.5 | evaluator L55 | L29 | Present |
| Maximum thrust 165.0 | environment L85 | L30, L46 | Present |
| Simulation step limit 10,000 | environment L67; prompt says "within 10,000 steps" | L43 | Present |
| MAGNET_R_MIN 0.5 | environment only, internal | — | Not required for agent (numerical stability). OK. |
| Gravity, damping, magnet layout/strength | environment | — | Intended INVISIBLE. OK. |

**Step 2.1 conclusion:** No violations. All required structural limits are in the prompt.

---

### 2.2 Mutation Synchronization (Updating VISIBLE Changes)

Rule: If `stages.py` modifies any VISIBLE variable (mentioned in the prompt), the prompt must be updated to `[new_value] (originally [old_value] in the source environment)`.

**Visible mutations in stages:**

- **Stage-1:** `terrain_config`: `magnets` only. Magnets are not in the prompt (invisible). No prompt update required. **OK.**
- **Stage-2:** `physics_config`: `gravity` only. Gravity is invisible. No prompt update required. **OK.**
- **Stage-3:** `terrain_config`: `magnets`, `max_thrust`: 500.0. **max_thrust is VISIBLE.** `update_task_description_for_visible_changes` and `update_success_criteria_for_visible_changes` implement the update. **Stage-4:** Same: `max_thrust`: 500.0. Same update logic. **OK.**

**Regex dry-run (execution verification):**

1. **Task description update** (`stages.py` L53–59)  
   - Pattern: `r"(- \*\*Maximum Thrust\*\*: The thrust vector magnitude is capped at )(\d+\.?\d*)( \(engine limit\)\.)"`  
   - Prompt text (prompt.py L30): `"- **Maximum Thrust**: The thrust vector magnitude is capped at 165.0 (engine limit)."`  
   - Match: group(1) = prefix up to "at ", group(2) = "165.0", group(3) = " (engine limit)."  
   - Replacement: `f"{m.group(1)}{target_max_thrust:.1f} (originally {base_max_thrust:.1f} in the source environment){m.group(3)}"`  
   - For Stage-3/4: target 500.0, base 165.0 → output: `"...capped at 500.0 (originally 165.0 in the source environment) (engine limit)."`  
   - Format requirement satisfied: `[new_value] (originally [old_value] in the source environment)`. **No violation.**

2. **Success criteria update** (`stages.py` L71–77)  
   - Pattern: `r"(- \*\*Maximum Thrust\*\*: Thrust magnitude must not exceed )(\d+\.?\d*)(\.)"`  
   - Prompt text (prompt.py L46): `"- **Maximum Thrust**: Thrust magnitude must not exceed 165.0."`  
   - Match: group(1) = prefix, group(2) = "165.0", group(3) = "."  
   - Replacement yields: `"...must not exceed 500.0 (originally 165.0 in the source environment)."`  
   - Format satisfied. **No violation.**

**Base config when running mutated stage:** Evaluation passes `target_terrain = env_j["terrain_config"]`, `base_terrain = env_i["terrain_config"]`. For Stage-4 vs base (Stage-1 or source), base may have no `max_thrust` → `base_max_thrust = _DEFAULT_MAX_THRUST = 165.0` (L51, L70). Correct. **No violation.**

**Step 2.2 conclusion:** No violations. Only visible mutation is max_thrust; regexes match and output the required format.

---

### 2.3 Hidden Physics Protection (INVISIBLE — No Leak of Values or Direction)

Rule: Exact values or direction of change of invisible constants (gravity, damping, magnet strengths/layout, etc.) must NOT appear in the prompt. General warning by name is allowed only in UNIFORM_SUFFIX.

**prompt.py line-by-line:**

- L24–25: "invisible magnetic force field", "invisible repulsive and attractive points" — no magnitudes or positions. **OK.**
- L26: "starting at x=8.0m, y=5.0m" — visible start. **OK.**
- L27–29: Force fields, gates, target zone, forbidden region — no gravity/damping/magnet values. **OK.**
- L30: Max thrust 165.0 — visible limit. **OK.**
- L31–42: Goal and objective — no invisible constants. **OK.**
- L43–46: Success criteria and design constraints — only target zone, steps, thrust. **OK.**

**Regex outputs (updated prompt for Stage-3/4):** Only change is max_thrust 165.0 → 500.0 (originally 165.0…). No gravity, damping, or magnet values. **OK.**

**stages.py mutation_description (L90, L101, L113, L127):** Per design, these are for logs/orchestration and must not be shown to the agent. Not part of prompt. No audit violation for leakage in prompt.

**Step 2.3 conclusion:** No violations. No invisible constant value or direction of change appears in the prompt or in the regex-generated prompt text.

---

### 2.4 UNIFORM_SUFFIX Audit (Union Rule and Tone)

Rule: UNIFORM_SUFFIX must list the **union** of all physical variables modified in Stage-1–4, and only give a general warning (what might change), never exact mutations or direction.

**Variables modified per stage:**

| Stage | terrain_config | physics_config |
|-------|----------------|----------------|
| Stage-1 | magnets (different layout) | — |
| Stage-2 | magnets (default) | gravity (0, 5.0) |
| Stage-3 | magnets (default), **max_thrust** 500 | gravity (0, -15), **linear_damping** 2.0 |
| Stage-4 | magnets (default), **max_thrust** 500 | gravity (0, -25) |

**Union of modified variables:** Electromagnetic fields (magnets), Gravity, Motion damping (linear_damping), Maximum thrust.

**UNIFORM_SUFFIX (stages.py L29–38):**

- "**Electromagnetic Fields**: The spatial layout and strength of repulsive walls or attractive nodes may differ from the source environment." — Covers magnets. **OK.**
- "**Gravity**: The magnitude and direction of the gravitational field may differ from the source environment." — Covers gravity. **OK.**
- "**Motion Damping**: Environmental friction and air resistance may differ from the source environment." — Covers linear_damping (Stage-3). **OK.**
- "**Maximum Thrust**: The engine's power limit may differ from the source environment." — Covers max_thrust (Stage-3, 4). **OK.**

**Union completeness:** Every modified variable (magnets, gravity, linear_damping, max_thrust) is mentioned. No modified variable is omitted. **OK.**

**Tone:** Wording is "may differ"; no exact values (e.g. "500" or "-25") and no direction (e.g. "increased" or "inverted"). **OK.**

**Step 2.4 conclusion:** No violations. UNIFORM_SUFFIX is the union of modified variables and stays general.

---

## Step 3: Expected Failure States and Logic

- **Body missing:** evaluator L40–46 returns done=True, score=0, failure_reason="Body not found". **Consistent.**
- **Pit entry before target:** L55–58: failed=True, failure_reason="Fell into pit zone; body entered forbidden region". **Consistent with prompt L29.**
- **Timeout without target:** L59–61: failed when `step_count >= max_steps - 1` and not success; reason "Stuck in local minimum: did not reach target zone before time ran out". **Consistent with prompt (10,000 steps, target zone).**
- **Success:** L50–52, 63–64: body in target zone → success=True, score=100. **Consistent.**

No violations found in failure/success logic.

---

## Summary Table

| Category | Result |
|----------|--------|
| Step 1: Cross-Module Consistency | **No violations found.** |
| Step 2.1: Constraint Completeness (visible limits in prompt) | **No violations found.** |
| Step 2.2: Mutation Synchronization (regex + format) | **No violations found.** |
| Step 2.3: Hidden Physics (no leak of invisible values/direction) | **No violations found.** |
| Step 2.4: UNIFORM_SUFFIX (union + tone) | **No violations found.** |
| Step 3: Expected failure states | **No violations found.** |

---

## Exhaustive Parameter Trace Summary

Every physical parameter in `environment.py` was traced:

- **BODY_START_X/Y, TARGET_*_MIN/MAX, MAX_STEPS:** Consistent across environment, prompt, evaluator, renderer, agent.
- **MAGNET_R_MIN:** Internal only; no prompt requirement.
- **gravity, linear_damping, angular_damping:** Invisible; not in prompt; stages mutate gravity and linear_damping; UNIFORM_SUFFIX covers them generally.
- **magnets:** Invisible; not in prompt; all stages set it; UNIFORM_SUFFIX mentions electromagnetic fields.
- **max_thrust:** Visible in prompt (165.0); Stage-3/4 set 500.0; prompt update and success_criteria update with "(originally 165.0 in the source environment)" implemented and regex-verified.
- **body_start_x/y** (from terrain): Defaults 8, 5; not mutated; prompt matches.
- Ground and body fixture constants: Not success/failure thresholds; not required in prompt.

Pit zone (16, 24, 5.5) exists only in evaluator and prompt; environment does not define it; alignment is correct.

---

**End of Audit. No modifications were made to any file.**
