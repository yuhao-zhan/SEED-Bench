from evaluation.evaluate import CodeVerifier

def get_stages():
    """
    Returns a list of stage configurations for C_01.
    Very simple settings to ensure success.
    """
    return [
        {
            "name": "Initial",
            "description": "Initial Task (Upright Start)",
            "config_overrides": {
                "pole_start_angle": 0.0,
                "gravity": 9.8,
                "pole_length": 2.0,
                "max_steps": 10000
            },
            "build_fn": "build_agent",
            "action_fn": "agent_action"
        },
        {
            "name": "Stage-1",
            "description": "Simple Swing-up (No extra perturbations)",
            "config_overrides": {
                "pole_start_angle": 3.14159,
                "gravity": 9.8,
                "pole_length": 2.0,
                "max_steps": 10000
            },
            "build_fn": "build_agent_stage_1",
            "action_fn": "agent_action_stage_1"
        },
        {
            "name": "Stage-2",
            "description": "Minimal Gravity Increase (11.0 m/s^2)",
            "config_overrides": {
                "pole_start_angle": 3.14159,
                "gravity": 11.0,
                "max_steps": 10000
            },
            "build_fn": "build_agent_stage_2",
            "action_fn": "agent_action_stage_2"
        },
        {
            "name": "Stage-3",
            "description": "Small Sensor Delay (2 steps)",
            "config_overrides": {
                "pole_start_angle": 3.14159,
                "sensor_delay_angle_steps": 2,
                "sensor_delay_omega_steps": 2,
                "max_steps": 10000
            },
            "build_fn": "build_agent_stage_3",
            "action_fn": "agent_action_stage_3"
        },
        {
            "name": "Stage-4",
            "description": "Combined Minor Perturbations",
            "config_overrides": {
                "pole_start_angle": 3.14159,
                "gravity": 10.5,
                "pole_length": 2.1,
                "max_steps": 10000
            },
            "build_fn": "build_agent_stage_4",
            "action_fn": "agent_action_stage_4"
        }
    ]
