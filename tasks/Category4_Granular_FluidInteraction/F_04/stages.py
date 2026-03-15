"""
F-04: The Filter task curriculum stages (mutations).

Mutated tasks vary invisible physical parameters: mix ratio (small/medium/large counts),
viscosity (linear/angular damping), particle friction, gravity, min_purity.
The solver is NOT told exact values; it must infer from environment feedback.
Stage-1/2: single parameter change each. Stage-3/4: multiple parameter changes.
Ordered by difficulty ascending.
Information Hiding: mutation_description is for logs/orchestration only and must NOT be shown to the agent.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes using format: [new_value] (originally [old_value] in the source environment)."""
    description = base_description
    base_mass = base_terrain_config.get("max_structure_mass", 75.0)
    target_mass = target_terrain_config.get("max_structure_mass", 75.0)
    if target_mass != base_mass:
        mass_pattern = r"(Total structure mass <= )(\d+\.?\d*)( kg)"
        if re.search(mass_pattern, description):
            description = re.sub(
                mass_pattern,
                lambda m: f"{m.group(1)}{target_mass:.0f}{m.group(3)} (originally {base_mass:.0f}{m.group(3)} in the source environment)",
                description,
            )
    base_beams = base_terrain_config.get("max_beams", 6)
    target_beams = target_terrain_config.get("max_beams", 6)
    if target_beams != base_beams:
        beams_pattern = r"(Maximum )(\d+)( beams)"
        if re.search(beams_pattern, description):
            description = re.sub(
                beams_pattern,
                lambda m: f"{m.group(1)}{target_beams}{m.group(3)} (originally {base_beams}{m.group(3)} in the source environment)",
                description,
            )
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes using format: [new_value] (originally [old_value] in the source environment)."""
    criteria = base_success_criteria

    target_purity = target_terrain_config.get("min_purity", 0.35)
    base_purity = base_terrain_config.get("min_purity", 0.35)
    if target_purity != base_purity:
        criteria = criteria.replace(
            f">= {base_purity*100:.0f}%",
            f">= {target_purity*100:.0f}% (originally >= {base_purity*100:.0f}% in the source environment)",
            1,
        )

    target_mass = target_terrain_config.get("max_structure_mass", 75.0)
    base_mass = base_terrain_config.get("max_structure_mass", 75.0)
    if target_mass != base_mass:
        mass_pattern = r"(Total structure mass <= )(\d+\.?\d*)( kg\.?)"
        if re.search(mass_pattern, criteria):
            criteria = re.sub(
                mass_pattern,
                lambda m: f"{m.group(1)}{target_mass:.0f} kg (originally {base_mass:.0f} kg in the source environment).",
                criteria,
            )
        else:
            criteria = criteria.replace("<= 75 kg", f"<= {target_mass:.0f} kg (originally {base_mass:.0f} kg in the source environment)").replace("<= 75.0 kg", f"<= {target_mass:.0f} kg (originally {base_mass:.0f} kg in the source environment)")

    target_beams = target_terrain_config.get("max_beams", 6)
    base_beams = base_terrain_config.get("max_beams", 6)
    if target_beams != base_beams:
        beams_pattern = r"(Maximum )(\d+)( beams\.?)"
        if re.search(beams_pattern, criteria):
            criteria = re.sub(
                beams_pattern,
                lambda m: f"{m.group(1)}{target_beams} beams (originally {base_beams} beams in the source environment).",
                criteria,
            )
        else:
            criteria = criteria.replace("Maximum 6 beams", f"Maximum {target_beams} beams (originally {base_beams} beams in the source environment)")

    return criteria


def get_f04_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for F-04 mutated tasks.
    Information Hiding: Uniform suffix for all stages to test physical reasoning.
    mutation_description is for logs/orchestration only and must NOT be shown to the agent.
    """
    UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Structural Limits (`max_beams`, `max_structure_mass`)**: The maximum number of allowable beams and the total mass budget may differ from the initial environment; use feedback to determine the effective limits.
- **Gravitational Field (`gravity`)**: The gravity vector might differ from standard; particle motion may not match the initial environment.
- **Ambient Viscosity (`linear_damping`, `angular_damping`)**: The fluid medium’s damping may differ from standard, affecting how particle motion decays.
- **Lateral Wind & Gusts (`wind_amplitude`, `gust_amplitude`, `wind_period_steps`)**: Wind forces may be present or differ from standard; their strength or timing may affect particle trajectories.
- **Surface Elasticity & Density (`mix.restitution`, `mix.density`)**: Particle restitution or density may differ from standard, affecting collisions and flow.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Minimalist Constraints",
            "mutation_description": "Strict limit on beams and mass.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_beams": 4,
                "max_structure_mass": 30.0,
                "min_purity": 0.35
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Anti-Gravity & Viscous",
            "mutation_description": "Particles float upwards due to reversed gravity and high fluid damping.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "min_purity": 0.35
            },
            "physics_config": {
                "gravity": (0, 3.0),
                "linear_damping": 0.5,
                "angular_damping": 0.5
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Hurricane Elasticity",
            "mutation_description": "High winds and bouncy particles with restricted beam count.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_beams": 5,
                "wind_amplitude": 300.0,
                "wind_period_steps": 10000,
                "gust_amplitude": 100.0,
                "mix": {
                    "restitution": 0.9
                },
                "min_purity": 0.35
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "The Ultimate Vortex Sieve",
            "mutation_description": "Combined constraints.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_beams": 5,
                "max_structure_mass": 40.0,
                "wind_amplitude": 250.0,
                "wind_period_steps": 10000,
                "mix": {
                    "density": 2000.0,
                    "restitution": 0.8
                },
                "min_purity": 0.35
            },
            "physics_config": {
                "linear_damping": 0.4,
                "angular_damping": 0.4
            },
        },
    ]
