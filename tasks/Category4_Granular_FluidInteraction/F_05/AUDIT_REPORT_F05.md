# F_05 (The Boat) — Read-Only Audit Report

**Task directory:** `tasks/Category4_Granular_FluidInteraction/F_05`  
**Audit scope:** Cross-module consistency, constraint completeness, mutation synchronization, hidden physics protection, UNIFORM_SUFFIX.  
**No code was modified.**

---

## Step 1: Cross-Module Consistency Audit

### 1.1 Physical parameters in `environment.py` (exhaustive list)

| # | Symbol / source | Default / location | Used in |
|---|-----------------|-------------------|--------|
| 1 | `gravity` | `physics_config.get("gravity", (0, -10))` | `world`, `step()` buoyancy |
| 2 | `linear_damping` | `physics_config.get("linear_damping", 0.1)` | body damping |
| 3 | `angular_damping` | `physics_config.get("angular_damping", 0.05)` | body damping |
| 4 | `WATER_X_MIN` | `5.0` (hardcoded) | `step()`, `get_terrain_bounds`, `get_cargo_in_water_count` logic |
| 5 | `WATER_X_MAX` | `25.0` (hardcoded) | same |
| 6 | `WATER_SURFACE_Y` | `2.0` (hardcoded) | buoyancy in `step()` |
| 7 | `CARGO_WATER_Y` | `terrain_config.get("cargo_water_y", 1.98)` | cargo-in-water check, `get_terrain_bounds` |
| 8 | `BOAT_MAX_ANGLE_RAD` | `terrain_config.get("max_capsize_angle_deg", 18.0)` → radians | joint break not used; capsize in `evaluator` via env |
| 9 | `BUILD_ZONE_X_MIN` | `terrain_config.get("build_zone_x_min", 12.0)` | `add_joint`, `_check_design_constraints`, `get_terrain_bounds` |
| 10 | `BUILD_ZONE_X_MAX` | `terrain_config.get("build_zone_x_max", 18.0)` | same |
| 11 | `BUILD_ZONE_Y_MIN` | `terrain_config.get("build_zone_y_min", 2.0)` | same |
| 12 | `BUILD_ZONE_Y_MAX` | `terrain_config.get("build_zone_y_max", 4.5)` | same |
| 13 | `MAX_STRUCTURE_MASS` | `terrain_config.get("max_structure_mass", 60.0)` | `get_structure_mass` vs limit, evaluator `_check_design_constraints` |
| 14 | `_wave_amplitude` | `terrain_config.get("wave_amplitude", 10.0)` | `step()` |
| 15 | `_wave_omega` (wave_frequency) | `terrain_config.get("wave_frequency", 0.5)` | `step()` |
| 16 | `_wave2_amplitude`, `_wave2_omega` | wave2_amplitude 5.0, wave2_frequency 0.27 | `step()` |
| 17 | `_gust_amplitude`, `_gust_interval` | 4.0, 80 | `step()` |
| 18 | `_wind_amplitude`, `_wind_omega` | 5.0, 0.15 | `step()` |
| 19 | `_restoring_coeff` | 1600.0 | `step()` restoring torque |
| 20 | `_current_strength` | 0.35 | `step()` |
| 21 | `_rogue_amplitude`, `_rogue_interval`, `_rogue_double_step` | 14.0, 380, 5 | `step()` |
| 22 | `_lateral_impulse_amplitude`, `_lateral_impulse_interval` | 68.0, 200 | `step()` |
| 23 | `DECK_FRICTION` | `terrain_config.get("deck_friction", 0.5)` | hull fixture, prompt |
| 24 | `JOINT_MAX_FORCE` | `terrain_config.get("joint_max_force", float('inf'))` | joint break in `step()` (force and torque > JOINT_MAX_FORCE * 0.4) |
| 25 | `MIN_BEAM_SIZE`, `MAX_BEAM_SIZE` | 0.1, 1.0 (hardcoded) | `add_beam` clamp |
| 26 | `rocks` | default list of 4 rocks | `_create_terrain` |

### 1.2 Consistency with `evaluator.py`

- Evaluator takes `terrain_bounds` and `environment`; it reads `MAX_STRUCTURE_MASS`, `BUILD_ZONE_*`, `BOAT_MAX_ANGLE_RAD`, `CARGO_WATER_Y` from the environment instance (lines 27–33). All align with `environment.py`.
- Failure conditions: cargo in water (y < `CARGO_WATER_Y`), capsize (angle > `BOAT_MAX_ANGLE_RAD`), structure broken (joint count decreased). Environment breaks joints when force > `JOINT_MAX_FORCE` or torque > `JOINT_MAX_FORCE * 0.4` (environment.py lines 278–291). Evaluator does not duplicate force/torque constants; it only observes `structure_broken` via joint count. **No violation.**

### 1.3 Consistency with `feedback.py`

- Feedback uses only metrics from the evaluator (`cargo_water_y`, `boat_max_angle_deg`, `max_structure_mass`, `build_zone_*`, etc.). No hardcoded structural limits; thresholds come from metrics. **No violation.**

### 1.4 Consistency with `prompt.py`

- Prompt states: Build Zone x=[12.0, 18.0], y=[2.0, 4.5]; Deck friction 0.5; Cargo lost below y = 1.98 m; Boat capsize below 18°; Mass ≤ 60 kg; Beam [0.1, 1.0] m; Joint limits generic. All match environment defaults and constraint usage. **No violation.**

### 1.5 Consistency with `renderer.py`

- Renderer uses `CARGO_WATER_Y`, `BUILD_ZONE_*` from the sandbox. No extra constants. **No violation.**

### 1.6 Summary Step 1

**No violations found for Step 1 (Cross-Module Consistency).**

---

## Step 2: Information Consistency & Visibility Audit

### 2.1 Constraint completeness (VISIBLE = stated in prompt)

- **Rule:** Every structural limit or failure threshold required to solve the task must appear in the initial task description (prompt).

| Environment limit | In prompt? | Location in prompt |
|------------------|-----------|---------------------|
| `CARGO_WATER_Y` 1.98 | Yes | success_criteria: "y = 1.98 m" |
| `max_capsize_angle_deg` 18 | Yes | success_criteria: "below 18 degrees" |
| `BUILD_ZONE_*` 12, 18, 2, 4.5 | Yes | task_description: "x=[12.0, 18.0], y=[2.0, 4.5]" |
| `MAX_STRUCTURE_MASS` 60 | Yes | success_criteria: "Total structure mass <= 60 kg" |
| `MIN_BEAM_SIZE`, `MAX_BEAM_SIZE` 0.1, 1.0 | Yes | success_criteria: "clamped by the environment to [0.1, 1.0] m" |
| `DECK_FRICTION` 0.5 | Yes | task_description and success_criteria |
| `JOINT_MAX_FORCE` (when finite) | Yes | success_criteria: generic sentence; when mutated, updated by `update_success_criteria_for_visible_changes` (numeric force/torque) |
| Torque threshold (0.4 * JOINT_MAX_FORCE) | Yes when joint limit set | Exposed only as the computed torque number in the updated success_criteria, not the ratio 0.4. Acceptable. |

- `WATER_X_MIN`, `WATER_X_MAX`, `WATER_SURFACE_Y`: Define water layout, not agent constraints; agent does not place water. Omission from prompt is acceptable.
- Wave/wind/current/rogue/lateral parameters: Invisible by design; no need in prompt.

**No violations found for Step 2.1 (Constraint Completeness).**

---

### 2.2 Mutation synchronization (visible changes → prompt update)

- **Rule:** If `stages.py` changes any VISIBLE variable, the prompt must be updated with format `[new_value] (originally [old_value] in the source environment)`.

**Mutated visible variables in F_05 stages:**

| Stage | Visible mutations | Updated in prompt? |
|-------|-------------------|---------------------|
| Stage-1 | `joint_max_force` 1500 | Yes, in `update_success_criteria_for_visible_changes` |
| Stage-2 | `deck_friction` 0, `build_zone_y_min` 2.5 | Yes: deck in both update functions; build zone in `update_task_description_for_visible_changes` |
| Stage-3 | `build_zone_y_min` 2.45 | Yes, build zone in task_description |
| Stage-4 | `joint_max_force` 5000, `deck_friction` 0, `build_zone_y_min` 2.5 | Yes, same as above |

- `max_structure_mass`, `cargo_water_y`, `max_capsize_angle_deg`: Not mutated in any stage; no update required.
- **Format check:** All replacements use "(originally ... in the source environment)" for the old value. **No violation of format.**

**Regex / replacement execution (dry-run):**

1. **Build Zone** (`update_task_description_for_visible_changes`, lines 35–40)  
   - Pattern: `(- \*\*Build Zone\*\*: Structure must be attached to the boat body within x=\[)([\d.]+), ([\d.]+)(\], y=\[)([\d.]+), ([\d.]+)(\]\.)`  
   - Prompt line: `- **Build Zone**: Structure must be attached to the boat body within x=[12.0, 18.0], y=[2.0, 4.5].`  
   - Match: group(2)=12.0, group(3)=18.0, group(5)=2.0, group(6)=4.5. Replacement outputs target x/y and base x/y with "(originally x=[...], y=[...] in the source environment)." **Matches and replaces correctly.**

2. **Deck friction (task_description)** (lines 47–53)  
   - Pattern: `(- \*\*Deck friction\*\*: The vessel deck has a friction coefficient of )([\d.]+)(; lower values make cargo more prone to sliding\.)`  
   - Prompt: "... coefficient of 0.5; lower values ..."  
   - Replacement: `\g<1>{target_deck} (originally {base_deck} in the source environment){m.group(3)}`. **Matches and format correct.**

3. **Joint structural limits (success_criteria)** (lines 66–85)  
   - Pattern: `(- \*\*Joint structural limits\*\*: )(In the base environment, joints are not subject to a documented force/torque limit; in some task variants, joints may fail if reaction forces or torques exceed the environment's structural capacity\.)`  
   - Prompt: exact same sentence. Replacement: "Maximum joint force is {target_val:.0f}; joints may also fail if reaction torque exceeds {torque_limit:.0f} (originally no documented limit in the source environment)." or "(originally force {base_val:.0f}, torque {base_torque:.0f} in the source environment)." **Matches and format correct.**

4. **Deck friction (success_criteria)** (lines 94–99)  
   - Pattern: `(- \*\*Deck friction\*\*: Deck friction coefficient is )([\d.]+)( \(affects cargo sliding and containment design\)\.)`  
   - Prompt: "Deck friction coefficient is 0.5 (affects ..."  
   - Replacement: `\g<1>{target_deck_f} (originally {base_deck_f} in the source environment)\g<3>`. **Matches and format correct.**

**No violations found for Step 2.2 (Mutation Synchronization).**

---

### 2.3 Hidden physics protection (INVISIBLE not leaked)

- **Rule:** Exact values or directions of change of invisible constants (e.g. gravity, wave amplitude, friction coefficients of water/rocks) must not appear in the prompt.

- **prompt.py:** No gravity value, no wave/current/rogue/wind magnitudes. Only generic “multi-mode waves, sudden gusts, lateral wind, and water currents” and “periodic rogue waves and lateral impulses.” **No leak.**

- **stages.py:**  
  - `mutation_description` is for logs/orchestration only (per S_01-style convention), not shown to the agent.  
  - `UNIFORM_SUFFIX` only names categories (“Gravitational Acceleration”, “Wave & Current Dynamics”, “Rogue wave / periodic impulse magnitude”) and does not give values or direction of change. **No leak.**

**No violations found for Step 2.3 (Hidden Physics Protection).**

---

### 2.4 UNIFORM_SUFFIX audit (union rule and tone)

- **Rule:** UNIFORM_SUFFIX must list the **union** of all physical variables modified in Stage-1–4 and only warn *what* might have changed, not *how*.

**Union of mutated variables across stages:**

- Stage-1: `joint_max_force`, `wave_amplitude`
- Stage-2: `deck_friction`, `rogue_amplitude`, `wave_amplitude`, `build_zone_y_min`
- Stage-3: `rocks`, `build_zone_y_min`, `wave_amplitude`
- Stage-4: `joint_max_force`, `deck_friction`, `wave_amplitude`, `current_strength`, `rocks`, `build_zone_y_min`, `gravity`

**Union:** Joint load tolerance, deck friction, rocks/reefs (submerged hazard), build zone (integration zone), gravity, wave/current dynamics, rogue/periodic impulse.

**UNIFORM_SUFFIX (F_05, lines 112–126) contains:**

- Joint Load Tolerance  
- Deck Surface Traction  
- Submerged Hazard Density (reefs)  
- Integration Zone Constraints  
- Gravitational Acceleration  
- Wave & Current Dynamics  
- Rogue wave / periodic impulse magnitude  

All modified variable categories are included. Wording is generic (“may have changed”, “MIGHT have changed”); no exact values or directions of change. **No violation of union or tone.**

**No violations found for Step 2.4 (UNIFORM_SUFFIX).**

---

## Summary Table

| Step | Category | Result |
|------|----------|--------|
| 1 | Cross-Module Consistency | No violations found |
| 2.1 | Constraint Completeness (VISIBLE) | No violations found |
| 2.2 | Mutation Synchronization (regex/format) | No violations found |
| 2.3 | Hidden Physics Protection (INVISIBLE) | No violations found |
| 2.4 | UNIFORM_SUFFIX (union + tone) | No violations found |

---

## Optional note (future-proofing)

- **Mass budget:** No stage in F_05 mutates `max_structure_mass`. If a future stage did, `update_task_description_for_visible_changes` and `update_success_criteria_for_visible_changes` do not currently update the “Mass Budget” / “Total structure mass <= 60 kg” line. For the **current** stage set, this is not a violation.

**End of audit.**
