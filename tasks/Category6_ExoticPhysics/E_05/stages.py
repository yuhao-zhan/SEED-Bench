"""
E-05: The Magnet task curriculum stages (mutations).

Stage-1 and Stage-2: one physical parameter change each (force field timing, gravity, etc.).
Stage-3 and Stage-4: multiple parameter changes. Difficulty increases Stage-1 → Stage-4.
All changes are invisible (force field distribution/strength, gravity, damping); do NOT
tell the agent exact values — it must infer from feedback.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List

# Default magnet layout (must match environment.default_magnets() for baseline).
# Format: static (x, y, strength); oscillating (x, y, base, amp, omega) or (x, y, base, amp, omega, phase).
_DEFAULT_MAGNETS = [
    (12.0, 4.0, -300.0),
    (12.0, 5.0, -300.0),
    (12.0, 6.0, -300.0),
    (12.0, 7.0, -300.0),
    (12.0, 8.0, -280.0),
    (12.0, 8.3, -260.0),
    (11.0, 9.7, -200.0),
    (13.0, 9.7, -200.0),
    (15.0, 9.7, -200.0),
    (17.0, 9.7, -200.0),
    (19.0, 9.7, -200.0),
    (21.0, 9.7, -180.0),
    (15.0, 9.0, -250.0, 230.0, 0.12),  # Gate 1: period ~52, weak 8–20
    (20.0, 9.0, -350.0, 330.0, 0.15, 3.14159),  # Gate 2: period ~42, weak 28–35
    (19.0, 3.0, 160.0),
    (21.0, 3.5, 130.0),
    (24.0, 5.0, -190.0),
    (24.0, 8.2, -180.0),
    (24.0, 6.6, -180.0, 160.0, 0.165),  # Keyhole center: period ~38, weak 8–18
    (26.0, 5.5, -130.0),
    (27.0, 9.5, -120.0),
    (29.5, 7.5, 95.0),
]

# Indices into _DEFAULT_MAGNETS for gates and keyhole (for mutations).
_IDX_GATE1 = 12
_IDX_GATE2 = 13
_IDX_KEYHOLE_CENTER = 18


def _magnets_stage2() -> List[tuple]:
    """Gate 1: weak only when step%52 in [28,29]; much stronger base so ref pushing at 8–20 cannot get through."""
    m = [list(x) for x in _DEFAULT_MAGNETS]
    # Ref pushes when step%52 in [8,20]. Phase so weak only at 28–29; base/amp so strong phase is very high.
    omega = 0.12
    phase = -1.79  # sin(28*0.12 + phase) ≈ 1 so weak at steps 28,29 only
    m[_IDX_GATE1] = (15.0, 9.0, -520.0, 420.0, omega, phase)
    return [tuple(x) for x in m]


def _magnets_stage3() -> List[tuple]:
    """Gate 2 phase π→0 so weak window moves to ~7–14. Ref waits at 28–35 → hits strong field."""
    m = [list(x) for x in _DEFAULT_MAGNETS]
    m[_IDX_GATE2] = (20.0, 9.0, -350.0, 330.0, 0.15, 0.0)
    return [tuple(x) for x in m]


def _magnets_stage4() -> List[tuple]:
    """All magnet strengths scaled 1.3; keyhole period 38→45 and weak window shifted to ~15–28."""
    scale = 1.3
    omega_kh = 2.0 * math.pi / 45.0
    phase_kh = -1.57
    out = []
    for i, mag in enumerate(_DEFAULT_MAGNETS):
        if len(mag) == 3:
            out.append((mag[0], mag[1], mag[2] * scale))
        elif len(mag) >= 5:
            base, amp = mag[2] * scale, mag[3] * scale
            omega = mag[4]
            phase = mag[5] if len(mag) >= 6 else 0.0
            if i == _IDX_KEYHOLE_CENTER:
                omega, phase = omega_kh, phase_kh
            out.append((mag[0], mag[1], base, amp, omega, phase))
        else:
            out.append(mag)
    return out


TASK_DESCRIPTION_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - Gravity: The magnitude and direction of the gravitational field.
 - Electromagnetic Fields: The strength, position, and temporal rhythm of force fields.
 - Motion Damping: Air resistance and structural motion resistance.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_e05_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Return ordered stage configs for E-05 mutated tasks.
    Order: Stage-1 (one param) → Stage-2 (one param) → Stage-3 (multi) → Stage-4 (multi).
    Difficulty increases so that the reference solution fails in each mutated environment.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Heavier world",
            "mutation_description": "Gravity increased. Ref solution uses fixed gravity compensation; under-compensates and sinks.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -14.0),
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Shifted gate rhythm",
            "mutation_description": "Gate 1 weak window shifted to a narrow band (steps 28–29) and strength increased; ref timing (weak 8–20) never aligns.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {
                "magnets": _magnets_stage2(),
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Different gate phase and resistance",
            "mutation_description": "Gate 2 phase changed (weak window moved); gravity and linear damping changed. Ref solution timing and compensation both wrong.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {
                "magnets": _magnets_stage3(),
            },
            "physics_config": {
                "gravity": (0, -12.0),
                "linear_damping": 0.5,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Stronger fields and altered dynamics",
            "mutation_description": "All force field strengths scaled up; keyhole period and weak window shifted; gravity and damping increased. Ref solution fails on timing and thrust.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {
                "magnets": _magnets_stage4(),
            },
            "physics_config": {
                "gravity": (0, -13.0),
                "linear_damping": 0.6,
                "angular_damping": 0.25,
            },
        },
    ]
