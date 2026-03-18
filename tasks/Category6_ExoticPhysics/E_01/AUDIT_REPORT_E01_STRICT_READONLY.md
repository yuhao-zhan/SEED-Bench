# E_01 Strict Read-Only Audit Report

**Task:** `tasks/Category6_ExoticPhysics/E_01` (Inverted Gravity)  
**Mode:** Read-only; no code modified.  
**Scope:** Exhaustive cross-module consistency, constraint completeness, mutation synchronization, hidden physics, and UNIFORM_SUFFIX.

---

## Step 1: Cross-Module Consistency Audit

### 1.1 Physical Parameters in `environment.py` (Exhaustive List)

| # | Parameter | Default / Source | Used By |
|---|-----------|------------------|---------|
| 1 | ARENA_X_MIN | 0.0 | evaluator, renderer, get_terrain_bounds |
| 2 | ARENA_X_MAX | 40.0 | evaluator, renderer, get_terrain_bounds |
| 3 | ARENA_Y_MIN | 0.0 | get_terrain_bounds |
| 4 | ARENA_Y_MAX | 20.0 or terrain_config["arena_y_max"] | evaluator, renderer, get_terrain_bounds, add_joint |
| 5 | BUILD_ZONE_X_MIN | 12.0 | get_terrain_bounds, evaluator, renderer |
| 6 | BUILD_ZONE_X_MAX | 28.0 | get_terrain_bounds, evaluator, renderer |
| 7 | BUILD_ZONE_Y_MIN | 6.0 | get_terrain_bounds, evaluator, renderer |
| 8 | BUILD_ZONE_Y_MAX | 18.0 or terrain_config["build_zone_y_max"] | get_terrain_bounds, evaluator, renderer |
| 9 | MAX_STRUCTURE_MASS | 200.0 or physics_config["max_structure_mass"] | evaluator (_check_design_constraints, metrics) |
| 10 | MAX_BEAM_COUNT | 12 or physics_config["max_beam_count"] | evaluator, get_terrain_bounds |
| 11 | OBSTACLE1_X_MIN/MAX, OBSTACLE1_Y_CENTER, HALF_W, HALF_H | 18, 22, 10, 2, 0.25 | _create_terrain, get_terrain_bounds, evaluator |
| 12 | OBSTACLE2_* | 14, 26, 13, 6, 0.25 | same |
| 13 | OBSTACLE3_* | 18.5, 19.5, 14, 0.5, 0.25 | same |
| 14 | FORBIDDEN_* (2 zones) | Rule-only; no physical body | get_terrain_bounds, evaluator (forbidden_zone_violation) |
| 15 | MIN_BEAM_SIZE, MAX_BEAM_SIZE | 0.1, 5.0 | add_beam, prompt |
| 16 | default_gravity_function | period 5s, g_y in [-10, 10] | __init__, step, get_gravity_at_time |
| 17 | _joint_force_limit | physics_config["joint_force_limit"] or inf | step (joint breaking) |
| 18 | _terrain_friction | terrain_config.get("friction", 0.6) | _create_terrain |
| 19 | _default_linear_damping | physics_config.get("linear_damping", 0.0) | __init__, add_beam, _create_demonstrator_bodies |
| 20 | _default_angular_damping | physics_config.get("angular_damping", 0.0) | same |
| 21 | _beam_density_scale | physics_config.get("beam_density_scale", 1.0) | add_beam |

### 1.2 Consistency Checks (Each Parameter Traced)

- **Arena bounds:** Evaluator reads `arena` from `terrain_bounds` (from `environment.get_terrain_bounds()`). Defaults in evaluator (0, 40, 0, 20) match `environment.py`. Mutated `ARENA_Y_MAX` is set on the sandbox instance and returned by `get_terrain_bounds()`; evaluator uses it. **Consistent.**
- **Build zone:** Same: from `terrain_bounds["build_zone"]`, defaults [12, 28], [6, 18]. **Consistent.**
- **MAX_STRUCTURE_MASS / MAX_BEAM_COUNT:** Evaluator uses `getattr(environment, "MAX_STRUCTURE_MASS", ...)` and `get_terrain_bounds()["max_beam_count"]` (from instance). **Consistent.**
- **Obstacles:** Evaluator builds `obstacle_zones` from `terrain_bounds["obstacles"]`; environment fills it from OBSTACLE1/2/3. **Consistent.**
- **Forbidden zones:** Evaluator uses `terrain_bounds["forbidden_zones"]`; environment fills from FORBIDDEN_* and FORBIDDEN2_*. **Consistent.**
- **Joint breaking:** Environment breaks joints when reaction force > `_joint_force_limit`; evaluator sets `structure_broken` when joint count drops. **Consistent.**
- **Success condition:** Evaluator: `success = (not failed) and (step_count >= max_steps - 1)`; failure = out_of_bounds OR structure_broken OR obstacle_overlap OR forbidden_zone_violation. Aligns with prompt. **Consistent.**
- **feedback.py:** Uses only metrics from evaluator; no hardcoded limits. **Consistent.**
- **renderer.py:** Uses `getattr(sandbox, "ARENA_Y_MAX", 20)` and sandbox build zone; respects mutated instance. **Consistent.**

### 1.3 Simulation Step Count

- **Prompt:** States "2,500 simulation steps" in task_description and success_criteria.
- **environment.py / evaluator.py:** Do not define 2,500; evaluator receives `max_steps` as argument and uses it for success and progress.
- **Conclusion:** The step count is a design constraint stated in the prompt; enforcement is in the runner (e.g. `get_max_steps_for_task`). Within E_01 directory, no inconsistency; consistency with runner is outside this directory.

### Step 1 Violations

**No violations found for Step 1 (Cross-Module Consistency).** All physical parameters are traced; evaluator, feedback, and renderer align with environment and prompt.

---

## Step 2: Information Consistency & Visibility Audit

### 2.1 Constraint Completeness (VISIBLE — All Structural Limits in Prompt)

Rule: Every variable that defines an absolute maximum, minimum, or failure threshold required to solve the task must be explicitly stated in the initial prompt.

| Environment / Evaluator Limit | In prompt.py? | Location |
|-------------------------------|---------------|----------|
| Arena x in [0, 40], y in [0, 20] | Yes | task_description: "x in [0, 40] m and y in [0, 20] m" |
| Build zone x=[12, 28], y=[6, 18] | Yes | task_description: "x=[12.0, 28.0], y=[6.0, 18.0]" |
| MAX_STRUCTURE_MASS 200 kg | Yes | success_criteria: "Total structure mass <= 200 kg" |
| MAX_BEAM_COUNT 12 | Yes | success_criteria: "Maximum 12 beams" |
| Obstacle zones 1–3 (exact bounds) | Yes | task_description: Zone 1–3 x/y ranges |
| MIN_BEAM_SIZE 0.1, MAX_BEAM_SIZE 5.0 | Yes | task_description and success_criteria: "0.1 m and 5.0 m" / "[0.1, 5.0] m" |
| Joint force limit (default: no limit) | Yes | task_description and success_criteria: "no force limit" |
| Simulation length | Yes | "2,500 simulation steps" (enforcement in runner) |
| Forbidden zones | Constraint stated, locations not given | "Use environmental feedback to infer their locations" (by design) |

**Omissions:** None. All structural limits needed to solve the task are in the prompt. Forbidden zone locations are intentionally invisible (infer from feedback).

### 2.1 Violations

**No violations found for Step 2.1 (Constraint Completeness).**

---

### 2.2 Mutation Synchronization (Visible Changes → Prompt Update)

Rule: If `stages.py` modifies any VISIBLE variable, the prompt must be updated with format `[new_value] (originally [old_value] in the source environment)`. Every regex must be dry-run to verify it captures and outputs correctly.

#### 2.2.1 Arena y_max (`update_task_description_for_visible_changes`)

- **Pattern:** `r"(- \*\*Arena\*\*: A bounded region with x in \[0, 40\] m and y in \[0, )(\d+\.?\d*)(\] m\.)"`
- **Prompt text:** "- **Arena**: A bounded region with x in [0, 40] m and y in [0, 20] m. "
- **Dry-run:** group(1) = "- **Arena**: A bounded region with x in [0, 40] m and y in [0, ", group(2) = "20", group(3) = "] m."
- **Replacement:** `\g<1>{target_arena_y_max:.1f}\g<3> (originally y in [0, {base_arena_y_max:.1f}] m in the source environment).`
- **Output (e.g. Stage-2):** "- **Arena**: A bounded region with x in [0, 40] m and y in [0, 16.8] m. (originally y in [0, 20.0] m in the source environment)."
- **Format:** New value = "y in [0, 16.8] m"; old = "y in [0, 20.0] m". **Correct.**

#### 2.2.2 Build Zone y_max

- **Pattern:** `r"(- \*\*Build Zone\*\*: Structure must be built within x=\[12\.0, 28\.0\], y=\[6\.0, )(\d+\.?\d*)(\]\.|\] \()"`
- **Prompt text:** "- **Build Zone**: Structure must be built within x=[12.0, 28.0], y=[6.0, 18.0]."
- **Dry-run:** group(2) = "18.0", group(3) = "]."
- **Replacement:** `\g<1>{target_bz_y_max:.1f}]. (originally y=[6.0, {base_bz_y_max:.1f}] in the source environment).`
- **Output (e.g. Stage-2):** "- **Build Zone**: Structure must be built within x=[12.0, 28.0], y=[6.0, 16.5]. (originally y=[6.0, 18.0] in the source environment)."
- **Format:** New = "y=[6.0, 16.5]", old = "y=[6.0, 18.0]". **Correct.** Pattern `(\]\.|\] \()` allows re-application on already-updated text (second run: "]. " after number; `\]\.` matches "].", so capture still works).

#### 2.2.3 Joint strength (`joint_force_limit`)

- **No-limit → finite:** Pattern `r"(- \*\*Joint strength\*\*: )Joints have no force limit \(they do not break from overload\)\."` → replacement with "Joints break when reaction force exceeds {target_joint_limit:.0f} N (originally no force limit in the source environment)." **Correct.**
- **Finite → finite:** Pattern `r"(- \*\*Joint strength\*\*: Joints break when reaction force exceeds )(\d+\.?\d*)( N \(originally .+? in the source environment\)\.)"` → replacement with new value and `(originally {base_joint_limit:.0f} N ...)` or "(originally no force limit ...)". **Correct** provided caller passes base_physics_config = source.

Mass budget and beam limit are only in **success_criteria**; they are updated in `update_success_criteria_for_visible_changes`:

- **Mass:** Pattern `r"(- \*\*Mass Budget\*\*: Total structure mass <= )(\d+\.?\d*)( kg\.)"` → "\\g<1>{target_mass:.0f} kg (originally {base_mass:.0f} kg in the source environment)." **Correct.**
- **Beam limit:** Pattern `r"(- \*\*Beam Limit\*\*: Maximum )(\d+)( beams\.)"` → "\\g<1>{int(target_beams)} beams (originally {int(base_beams)} beams in the source environment)." **Correct.**

**Caller contract:** The update functions are written so that `base_terrain_config` and `base_physics_config` represent the **source (unmutated) environment**. If an orchestrator passes a different stage’s config as base (e.g. in cross-mutation, base = env_i), then "(originally X in the source environment)" will refer to that stage’s X, not the true source. That is a **caller/orchestration** concern; within E_01 the implementation is correct when base = source.

### 2.2 Violations

**No violations found for Step 2.2 (Mutation Synchronization)** within the E_01 directory. All regex blocks capture the intended strings and produce the required format when base_* is the source config.

---

### 2.3 Hidden Physics Protection (INVISIBLE)

Rule: Exact values or directions of change of INVISIBLE constants (e.g. gravity magnitude, friction, damping) must NOT appear in the prompt. General warning by name is allowed only in UNIFORM_SUFFIX.

- **prompt.py:** "The gravity vector oscillates periodically between downward and upward directions (inverting gravity)." — No period, amplitude, or numeric value. **No leak.**
- **prompt.py:** No mention of friction, linear_damping, angular_damping, or beam_density_scale. **No leak.**
- **stages.py:** `mutation_description` is for logs/orchestration only and is not appended to the agent prompt; only `task_description_suffix` is. **No leak.**
- **TASK_DESCRIPTION_SUFFIX:** Refers only to what "might" have changed (e.g. "Gravity Field Dynamics", "Motion Damping"); no specific values or directions. **No leak.**

### 2.3 Violations

**No violations found for Step 2.3 (Hidden Physics Protection).**

---

### 2.4 UNIFORM_SUFFIX Audit (Union Rule)

Rule: The suffix must list the **union** of all physical variables modified in Stage-1–Stage-4, and only give a general warning (what might change), never how they change.

**Variables modified in stages:**

| Variable | Stage-1 | Stage-2 | Stage-3 | Stage-4 |
|----------|---------|---------|--------|--------|
| arena_y_max | — | 16.8 | 18.0 | 16.0 |
| build_zone_y_max | — | 16.5 | 17.0 | 15.5 |
| friction | — | 0.0 | — | 0.0 |
| gravity (function) | ✓ | ✓ | ✓ | ✓ |
| linear_damping | — | -1.0 | — | -0.4 |
| joint_force_limit | 600 | — | — | 300 |
| max_structure_mass | — | — | 55 | — |
| max_beam_count | — | — | — | 6 |

**Union:** arena/build zone boundaries, gravity, motion damping, joint strength, surface traction (friction), mass budget, beam count.

**TASK_DESCRIPTION_SUFFIX in stages.py (lines 43–55):**

- "**Arena and Build Zone Boundaries**" — covers arena_y_max, build_zone_y_max. ✓  
- "**Gravity Field Dynamics**" — covers gravity. ✓  
- "**Motion Damping**" — covers linear_damping (and angular by generality). ✓  
- "**Structural Integrity Thresholds**" — covers joint_force_limit. ✓  
- "**Surface Traction**" — covers friction. ✓  
- "**Logistical Constraints**" (mass budget, number of components) — covers max_structure_mass, max_beam_count. ✓  

Tone: "may be restricted", "may be altered", "may differ", "may have a finite strength limit", "may be strictly limited". No specific values or directions. ✓  

**angular_damping:** Not modified in any stage; union does not require it. Suffix mentions "Linear or angular damping" as a general warning; acceptable. ✓  

### 2.4 Violations

**No violations found for Step 2.4 (UNIFORM_SUFFIX).** The suffix covers the union of modified variables and does not state how they change.

---

## Summary of Violations

| Step | Category | Violations |
|------|----------|------------|
| 1 | Cross-Module Consistency | **None** |
| 2.1 | Constraint Completeness (VISIBLE) | **None** |
| 2.2 | Mutation Synchronization (regex/format) | **None** (within E_01; caller must pass base = source) |
| 2.3 | Hidden Physics Protection (INVISIBLE) | **None** |
| 2.4 | UNIFORM_SUFFIX (union + tone) | **None** |

**Total violations in E_01 directory: 0.**

---

## Notes (No Violations, For Completeness)

- **Simulation steps:** 2,500 is stated in the prompt; it is not defined in `environment.py` or `evaluator.py` (evaluator uses `max_steps` from the caller). Consistency with the runner is outside this directory.
- **Mass/beam updates:** Mass budget and beam limit appear only in success_criteria; they are updated only in `update_success_criteria_for_visible_changes`. Task_description is updated for arena, build zone, and joint strength only. This is correct for E_01.
- **Orchestrator:** If the evaluation pipeline (e.g. `evaluate_cross_mutated.py`) passes a prior stage’s config as `base_terrain_config`/`base_physics_config`, the phrase "in the source environment" will refer to that stage, not the unmutated source. The E_01 stages.py code itself assumes base = source.
