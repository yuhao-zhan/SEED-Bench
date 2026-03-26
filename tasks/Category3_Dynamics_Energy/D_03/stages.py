"""
D-03: Phase-Locked Gate curriculum stages (mutations).

Stage order: Stage-1 < Stage-2 < Stage-3 < Stage-4 (difficulty ascending).
All mutations use non-visible physical parameters (impulse strength, damping, gravity);
do NOT expose exact values in the task prompt — the agent must infer from feedback.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

_DEFAULT_IMPULSE_MAGNITUDE = 1.5
_DEFAULT_IMPULSE2_MAGNITUDE = 0.55
_DEFAULT_DECEL_DAMPING = 3.2


def update_task_description_for_visible_changes(
    base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update task description with visible changes: [new_value] [unit] (originally [old_value] [unit] in the source environment).

    Callers MUST pass the pristine, unmodified base task description in base_description.
    """
    if "(originally " in base_description and " in the source environment)" in base_description:
        raise ValueError(
            "update_task_description_for_visible_changes requires a pristine base task description."
        )
    description = base_description
    target = target_terrain_config or {}
    base = base_terrain_config or {}

    # First impulse zone magnitude
    target_imp = target.get("impulse_magnitude", _DEFAULT_IMPULSE_MAGNITUDE)
    base_imp = base.get("impulse_magnitude", _DEFAULT_IMPULSE_MAGNITUDE)
    if target_imp != _DEFAULT_IMPULSE_MAGNITUDE or base_imp != _DEFAULT_IMPULSE_MAGNITUDE:
        # Capture: (intro)(value)(unit)(rest)
        pattern = r"(- \*\*First impulse zone\*\*: x=\[8\.0, 9\.0\] m; a one-time backward impulse of magnitude )(\d+\.?\d*)( N·s \(per component\))( is applied when the cart first enters\.)"
        if re.search(pattern, description):
            if target_imp != base_imp:
                replacement = lambda m: f"{m.group(1)}{target_imp:.2g}{m.group(3)} (originally {base_imp:.2g}{m.group(3)} in the source environment){m.group(4)}"
            else:
                replacement = lambda m: f"{m.group(1)}{target_imp:.2g}{m.group(3)}{m.group(4)}"
            description = re.sub(pattern, replacement, description)

    # Second impulse zone magnitude
    target_imp2 = target.get("impulse2_magnitude", _DEFAULT_IMPULSE2_MAGNITUDE)
    base_imp2 = base.get("impulse2_magnitude", _DEFAULT_IMPULSE2_MAGNITUDE)
    if target_imp2 != _DEFAULT_IMPULSE2_MAGNITUDE or base_imp2 != _DEFAULT_IMPULSE2_MAGNITUDE:
        pattern = r"(- \*\*Second impulse zone\*\*: x=\[10\.5, 11\.0\] m; a one-time backward impulse of magnitude )(\d+\.?\d*)( N·s \(per component\))( is applied when the cart first enters\.)"
        if re.search(pattern, description):
            if target_imp2 != base_imp2:
                replacement = lambda m: f"{m.group(1)}{target_imp2:.2g}{m.group(3)} (originally {base_imp2:.2g}{m.group(3)} in the source environment){m.group(4)}"
            else:
                replacement = lambda m: f"{m.group(1)}{target_imp2:.2g}{m.group(3)}{m.group(4)}"
            description = re.sub(pattern, replacement, description)

    # Decel zone damping
    target_decel = target.get("decel_damping", _DEFAULT_DECEL_DAMPING)
    base_decel = base.get("decel_damping", _DEFAULT_DECEL_DAMPING)
    if target_decel != _DEFAULT_DECEL_DAMPING or base_decel != _DEFAULT_DECEL_DAMPING:
        pattern = r"(- \*\*Decel zone\*\*: x=\[9\.5, 11\.0\] m; linear velocity damping coefficient )(\d+\.?\d*)( N·s/m \(applied to each structural component\))(\.)"
        if re.search(pattern, description):
            if target_decel != base_decel:
                replacement = lambda m: f"{m.group(1)}{target_decel:.2g}{m.group(3)} (originally {base_decel:.2g}{m.group(3)} in the source environment){m.group(4)}"
            else:
                replacement = lambda m: f"{m.group(1)}{target_decel:.2g}{m.group(3)}{m.group(4)}"
            description = re.sub(pattern, replacement, description)

    return description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update success criteria only for visible changes."""
    return base_success_criteria


def get_task_description_suffix(stages: List[Dict[str, Any]]) -> str:
    """Generate a dynamic suffix based on the union of all mutated variables."""
    union_keys = set()
    for s in stages:
        union_keys.update(s.get("terrain_config", {}).keys())
        union_keys.update(s.get("physics_config", {}).keys())

    mapping = {
        "impulse_magnitude": "- **First impulse zone**: The magnitude of the backward impulse applied in the first track zone may vary.",
        "impulse2_magnitude": "- **Second impulse zone**: The magnitude of the backward impulse applied in the second track zone may vary.",
        "linear_damping": "- **Ambient Resistance**: Linear or angular damping across the environment may be altered, causing the cart to shed speed differently.",
        "angular_damping": "- **Ambient Resistance**: Linear or angular damping across the environment may be altered, causing the cart to shed speed differently.",
        "decel_damping": "- **Deceleration Zone Damping**: The resistance within specific slowing zones may have been adjusted, altering how effectively the cart is braked.",
        "gravity": "- **Gravity**: Changes in the gravitational field may affect the effective weight and friction of the cart as it moves.",
    }

    detected_messages = []
    for key in sorted(mapping.keys()):
        if key in union_keys:
            msg = mapping[key]
            if msg not in detected_messages:
                detected_messages.append(msg)

    if not detected_messages:
        return ""

    suffix = "\n## Environmental Anomalies Detected\n"
    suffix += "Sensors indicate that this region exhibits non-standard physical properties.\n"
    suffix += "While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:\n"
    suffix += "\n".join(detected_messages) + "\n"
    suffix += "\n**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.\n"
    return suffix


def get_d03_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Return ordered stage configs for D-03 mutated tasks.
    Stage-1/2: single physical parameter change (harder so original solution fails).
    Stage-3/4: multiple parameter changes (progressively harder).
    """
    stages = [
        {
            "stage_id": "Stage-1",
            "title": "Stronger first impulse",
            "mutation_description": "Impulse magnitude in zone [8,9] increased; need more mass to survive speed trap v(9)≥2.8.",
            "terrain_config": {
                "impulse_magnitude": 2.5,  # default 1.5 — stronger backward kick, original solution may fail v(9)≥2.8
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Higher ambient damping",
            "mutation_description": "Linear and angular damping increased; cart sheds more speed everywhere, v(11) band and gate timing harder.",
            "terrain_config": {},
            "physics_config": {
                "linear_damping": 0.55,
                "angular_damping": 0.55,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Stronger impulses and decel zone",
            "mutation_description": "First impulse, second impulse, and decel zone damping all increased; v(9) and v(11) both harder to meet.",
            "terrain_config": {
                "impulse_magnitude": 2.5,
                "impulse2_magnitude": 0.95,
                "decel_damping": 4.8,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Heavy world and strong impulses",
            "mutation_description": "Gravity increased, both impulses and decel damping stronger, plus ambient damping; full profile and phase must be re-tuned.",
            "terrain_config": {
                "impulse_magnitude": 2.6,
                "impulse2_magnitude": 0.95,
                "decel_damping": 4.5,
            },
            "physics_config": {
                "gravity": (0, -12),
                "linear_damping": 0.4,
                "angular_damping": 0.4,
            },
        },
    ]

    # Apply the dynamic suffix to all stages
    suffix = get_task_description_suffix(stages)
    for s in stages:
        s["task_description_suffix"] = suffix

    return stages
