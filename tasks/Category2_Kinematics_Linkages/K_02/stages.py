"""
K-02: The Climber mutated task stages
Defines 4 distinct stages with increasing complexity and morphology-forcing constraints.
"""

# The uniform suffix for all mutated tasks
UNIFORM_SUFFIX = (
    "Environmental conditions include Atmospheric Shear, Surface Slickness, "
    "Seismic Resonance, Geological Instability, and Structural Thresholds. "
    "Robotic entities must adapt their physical form and control parameters "
    "to maintain wall adhesion and achieve vertical ascent."
)

def get_stage_config(stage_index: int):
    """
    Returns (terrain_config, physics_config, task_description) for the given stage.
    """
    if stage_index == 1:
        # Stage 1: Gauntlet - Restricted build zone
        terrain_config = {
            "build_zone_y_max": 5.0, # Forces mobile climbing
            "target_height": 20.0
        }
        physics_config = {}
        task_desc = (
            "Gauntlet Phase: Structural clearance is restricted to the base zone (y < 5.0m). "
            "A static tower is no longer feasible. You must design a mobile climbing mechanism "
            "capable of independent vertical locomotion to reach the 20m threshold. "
            f"{UNIFORM_SUFFIX}"
        )
        return terrain_config, physics_config, task_desc

    elif stage_index == 2:
        # Stage 2: Gapped Wall - Forces long reach
        terrain_config = {
            "build_zone_y_max": 5.0,
            "target_height": 20.0,
            "suction_zones": [(0, 5), (10, 15), (20, 25)] # 5m gaps in wall suction
        }
        physics_config = {}
        task_desc = (
            "Reach Phase: The wall surface is segmented. Suction mechanisms only function "
            "within specific resonance bands: [0-5m], [10-15m], and [20-25m]. "
            "Your entity must possess sufficient reach to span these dead zones. "
            f"{UNIFORM_SUFFIX}"
        )
        return terrain_config, physics_config, task_desc

    elif stage_index == 3:
        # Stage 3: Seismic Heavyweight - Forces high mass
        terrain_config = {
            "build_zone_y_max": 5.0,
            "target_height": 20.0,
            "wall_oscillation_amp": 0.2,
            "wall_oscillation_freq": 10.0,
            "min_structure_mass": 20.0 # Force a heavy design
        }
        physics_config = {}
        task_desc = (
            "Heavyweight Phase: Seismic Resonance has destabilized the environment. "
            "Lightweight entities are easily shaken loose. A minimum structural mass of 20kg "
            "is required for inertial stability against high-frequency wall oscillations. "
            f"{UNIFORM_SUFFIX}"
        )
        return terrain_config, physics_config, task_desc

    elif stage_index == 4:
        # Stage 4: Storm Cell - Tightest build zone + Wind
        terrain_config = {
            "build_zone_y_max": 2.0, # Extremely tight
            "target_height": 20.0,
            "wind_force": -5.0, # Constant horizontal push
            "vortex_y": 10.0,
            "vortex_force_x": 10.0 # Higher altitude vortex
        }
        physics_config = {}
        task_desc = (
            "Storm Cell: Final environmental threshold. Clearance is extremely restricted (y < 2.0m). "
            "Atmospheric Shear creates strong lateral forces at ground level and a high-altitude "
            "vortex above 10m. You must design an ultra-compact, high-torque climber. "
            f"{UNIFORM_SUFFIX}"
        )
        return terrain_config, physics_config, task_desc

    return {}, {}, ""
