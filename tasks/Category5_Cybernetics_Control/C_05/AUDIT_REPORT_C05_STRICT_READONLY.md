# C_05 Audit Follow-Up (Evaluator, Feedback, Agent, Primitives, Debug)

**Task directory:** `tasks/Category5_Cybernetics_Control/C_05`  
**Scope:** Cross-module consistency fixes from strict read-only audit; re-check imports, JSON, and mutation regex anchors.

---

## Fixes Applied (this round)

1. **environment.py** — Added `REPULSION_STRONG_THRESHOLD = 40.0` (single source for “strong repulsion” feedback flags).
2. **evaluator.py** — Imports `FORCE_LIMIT_INSIDE` and `REPULSION_STRONG_THRESHOLD` from `environment.py`; removes magic `40.0` / `60.0` literals for flags.
3. **feedback.py** — Renamed/clarified speed line: global |v| vs in-zone dwell gating.
4. **agent.py** — `RAMP_Y_TARGET = 3.5` to match platform top in `environment.py` (`platform_y = 3.5`).
5. **prompt.py** — Success criterion 2 wording: “final gate” → explicit A→B→C completion + timed barrier.
6. **tasks/primitives_api.json (`C_05`)** — Documented `get_barrier_x`, `get_barrier_delay_steps`, `get_steps_in_current_zone`, `get_steps_required_to_trigger`; fixed `get_next_required_switch` example variable name.
7. **debug_C05_stage1.py / debug_C05_stage2.py** — `physics_config` aligned with `stages.py` Stage-1 and Stage-2.

---

## Re-Check Results

- **`primitives_api.json`**: Parses with `json.load`.
- **Bytecode**: `py_compile` on modified `C_05` Python modules succeeds.
- **`update_task_description_for_visible_changes` / `update_success_criteria_for_visible_changes`**: Baseline regex anchors still match current `prompt.py` (success-criteria edit does not touch mutated bullets).

---

## Summary

| Item                         | Status   |
|-----------------------------|----------|
| Evaluator ↔ env constants   | **Aligned** |
| Feedback speed semantics    | **Clarified** |
| Agent ramp target ↔ terrain | **Aligned** |
| Primitives vs `Sandbox` API | **Expanded** |
| Debug scripts ↔ `stages.py` | **Aligned** |

Earlier rounds (feedback C-altitude text, `stages.py` regex fixes) remain as documented in git history / prior report sections if preserved elsewhere.
