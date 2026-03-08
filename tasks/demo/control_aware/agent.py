import math

def build_agent(sandbox):
    slider = sandbox.add_slider(x=0.0, y=sandbox.TRACK_Y, width=0.5, height=0.3, density=1.0)
    return {
        : slider
    }

def agent_action(sandbox, agent_components, step_count):
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
