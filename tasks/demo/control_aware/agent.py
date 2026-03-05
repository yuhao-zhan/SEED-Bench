"""
Control-Aware task Agent module
Contains Agent construction logic and dynamic speed control logic
"""
import math


def build_agent(sandbox):
    """
    Build slider control system
    Creates slider on track, stores reference for control
    """

    slider = sandbox.add_slider(x=0.0, y=sandbox.TRACK_Y, width=0.5, height=0.3, density=1.0)

    return {
        'slider': slider
    }


def agent_action(sandbox, agent_components, step_count):
    """
    Agent control logic - called by simulation loop at each step
    CRITICAL: Must dynamically adjust speed based on position to comply with speed limits

    Speed zones:
    - Zone 1 (0-10m): Speed limit 1.5 m/s
    - Zone 2 (10-20m): Speed limit 3.0 m/s
    - Zone 3 (20-30m): Speed limit 2.0 m/s
    """

    slider = agent_components.get('slider')
    if not slider:
        return


    position_x, velocity_x = sandbox.get_slider_state(slider)



    if position_x < 0.0:

        target_speed = 1.0
    elif 0.0 <= position_x < 10.0:

        target_speed = 1.5 * 0.95
    elif 10.0 <= position_x < 20.0:

        target_speed = 3.0 * 0.95
    elif 20.0 <= position_x < 30.0:

        target_speed = 2.0 * 0.95
    else:

        target_speed = 0.0



    sandbox.set_slider_velocity(slider, target_speed)
