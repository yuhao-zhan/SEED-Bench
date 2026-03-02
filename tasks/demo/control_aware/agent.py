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
    # Create slider at start position
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
    # Get slider
    slider = agent_components.get('slider')
    if not slider:
        return
    
    # Get slider state
    position_x, velocity_x = sandbox.get_slider_state(slider)
    
    # Determine target speed based on current zone
    # Use the same zone boundaries as evaluator for consistency
    if position_x < 0.0:
        # Before start - move forward slowly
        target_speed = 1.0
    elif 0.0 <= position_x < 10.0:
        # Zone 1: Speed limit 1.5 m/s - use low speed
        target_speed = 1.5 * 0.95  # 95% of limit for safety margin
    elif 10.0 <= position_x < 20.0:
        # Zone 2: Speed limit 3.0 m/s - can use higher speed
        target_speed = 3.0 * 0.95  # 95% of limit for safety margin
    elif 20.0 <= position_x < 30.0:
        # Zone 3: Speed limit 2.0 m/s - reduce speed
        target_speed = 2.0 * 0.95  # 95% of limit for safety margin
    else:
        # After target - stop
        target_speed = 0.0
    
    # Apply control - use direct velocity setting (simpler and more reliable)
    # The velocity is set directly, which should work immediately
    sandbox.set_slider_velocity(slider, target_speed)
