"""
F-05: The Boat task Prompt and Primitives definition
"""

import os
import json
import sys

# Add the tasks directory to sys.path to find primitives_api.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from primitives_api import API_INTRO

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'primitives_api.json'), 'r') as f:
    _api_data = json.load(f)

if 'F_05' in _api_data and 'API_INTRO' in _api_data['F_05']:
    del _api_data['F_05']['API_INTRO']


TASK_PROMPT = {
    "task_description": """
Design a stabilization and containment structure for a boat in rough water.

## Task Environment
- **Water / interaction band**: Buoyancy and wave forcing apply when the hull is in x ∈ [5.0, 25.0] m and its center satisfies y ≤ 3.0 m (i.e. within 1.0 m above the nominal free surface y = 2.0 m).
- **Cargo vs hull in water**: Cargo particles receive an extra upward fluid-style impulse only while their center lies **strictly below** the nominal free surface y = 2.0 m and x is in the same water band; the hull uses the y ≤ 3.0 m band above. Coupling differs between hull and cargo in the simulator—treat both bands as part of the coupled fluid interaction.
- **Buoyancy and fluid coupling**: In the water band, hull support uses an upward term **1.5 × (hull + structure + cargo mass) × |g| × (y_ref − y_hull)**, clamped to ≥ 0, with **y_ref = 2.5 m** (nominal free surface **y = 2.0 m** plus **0.5 m** reference offset). Submerged cargo (**center strictly below y = 2.0 m** in the water band) receives an additional upward **0.5 × m_cargo × |g|** each step. Wave and impulsive forces are separate. This coupling is **not** the same as the evaluator’s cargo **loss plane** (see Success Criteria).
- **Evaluator loss plane vs free surface**: Retention is scored against a separate horizontal **loss plane** (y given under Success Criteria), which may be **above or below** the nominal free surface y = 2.0 m in variants. A particle can fail retention without ever dropping below y = 2.0 m if the loss plane is raised.
- **Loss-plane grace window**: The evaluator ignores loss-plane crossings during the first **`cargo_loss_grace_steps`** physics steps (environment configuration; baseline default **120**). The first numbered cargo-retention rule in the scoring section uses that baseline default; staged prompts update the step count when variants change it.
- **Boat**: Hull center at x≈15 m, y≈2.5 m. The hull is a 3.0 m × 0.4 m rectangle (full width × height) and is dynamically simulated (it can translate and roll). The hull body uses fixture density 80 (2D simulator units; with this rectangle area, implied hull mass at creation is about **96 kg** before cargo and any beams).
- **Hull & beam deck friction**: The hull and beams you build share a single deck-facing friction coefficient in the simulator; the baseline value is **0.5** (variants may override). Infer effective traction at contacts with cargo, floor, and rocks from interaction and feedback. In Box2D, contact friction combines **both** colliding fixtures: agent beams therefore interact with the floor and rocks using a **mixed** effective friction, not the rock/floor coefficients alone.
- **Cargo**: 10 circular particles, radius 0.15 m; baseline disk density 260, friction 0.28, restitution 0.12 (variants may override contact parameters).
- **Cargo placement**: Horizontal spawn offsets are pseudo-random with a fixed evaluation seed under the standard harness so initial layouts are reproducible across runs. Baseline uses RNG **seed 42** (overridable via `terrain_config["target_rng_seed"]` or `cargo["seed"]`). Baseline draws: horizontal offset of each disk center from the hull center along the deck in **approximately [-1.35, 1.35] m** (hull half-beam 1.5 m minus disk radius 0.15 m), plus a vertical offset **in [0, 0.55] m** above the hull top contact band before placing the disk center (radius added by the simulator).
- **Submerged obstacles**: four rocks: (13.50, 1.00, r=0.24); (14.50, 1.10, r=0.22); (15.50, 1.05, r=0.23); (16.50, 1.08, r=0.22). Each baseline rock fixture uses **friction 0.6** and **restitution 0.2** in the simulator; variants may change positions/radii and therefore the hazard field.
- **Seabed / floor**: A horizontal floor spans x ∈ [0, 30] m with its top near y = 0 m. The baseline floor fixture uses **friction 0.4**; agent beams that touch the floor or rocks combine those coefficients with deck friction in Box2D.
- **Build zone**: Beam centers must lie in x=[12.0, 18.0], y=[2.0, 4.5]. Every weld anchor for `add_joint` (hull attachment or beam–beam) must lie in the same box (enforced at build time and in design checks). **Beam footprint**: each beam is an oriented rectangle; **all four corner vertices in world space** (after rotation) must lie inside this same x/y box—the design checker tests these corners (not a separate world-axis-aligned hull of the slanted rectangle).
- **Hull attachment**: With `add_joint(..., body_b=None)`, the anchor welds to the hull and must lie in the build zone (same rule as all other joints).
- **Damping (baseline)**: Hull, beams, and cargo use linear damping **0.1** and angular damping **0.05** by default (simulator units; variants may override per body class).
- **Harness dynamics**: If the evaluation harness invokes `agent_action` each physics step, it may apply additional **torque on the hull** and, in some profiles, **forces on cargo** bodies. These effects are outside `add_beam` / `add_joint` but change rollout physics when that hook is enabled.
- **Environmental loading**: The simulator applies coupled external and contact-driven disturbances. Exact mechanisms, magnitudes, and timing are not enumerated here; infer them from interaction and feedback.
- **Default beam material**: If you omit `density` in `add_beam`, the environment uses 150 kg/m²-equivalent for the beam body (see API).
- **Episode length**: The run uses a fixed maximum physics-step budget from the harness configuration (hard stop at `max_steps`). The standard F-05 task verifier and `test_mutated_tasks.py` use **10,000** steps unless the caller overrides `max_steps`. Final scoring occurs at episode end, and safety violations are tracked over time according to the evaluator rules.

## Task Objective
Design a structure that:
1. Prevents cargo from crossing the evaluator loss plane despite severe vessel motion.
2. Lowers the center of mass or provides stabilization to prevent the boat from capsizing.
3. Withstands periodic and impulsive loads from the simulated sea state.
""",
    "success_criteria": """
## Success Criteria
1. **Cargo Retention**: A particle fails if its center **ever** falls below y = 1.98 m after the first 120 physics steps (brief spawn/settling is ignored).
2. **Stability**: Peak absolute hull roll angle after that same settling window must stay at or below 18.0 degrees.

## Design Constraints
- **Mass Budget**: Total structure mass <= 60 kg.
- **Beam dimensions**: Each beam width and height is clamped by the environment to [0.1, 1.0] m (see Add Beam in the API below).
- **Joint structural limits**: When no per-weld load cap is configured, welds do not break under reaction loads. When a force cap **F_max** (N) is configured, the simulator also enforces a coupled torque cap **0.4 × F_max** (N·m); a weld breaks if simulated reaction force exceeds **F_max** or reaction torque exceeds that torque cap. Numeric **F_max** and the derived torque cap appear in Success Criteria when configured; use episode feedback when limits are not printed.
- **APIs**: Use only the primitives documented below.
""",
    'primitives_api': API_INTRO + '\n' + '\n\n'.join(_api_data['F_05'].values()),
}
