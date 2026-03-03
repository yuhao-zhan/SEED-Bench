"""
D-04: The Swing task Agent module
Pumping strategy for parametric resonance.
"""
import math

def build_agent(sandbox):
    return None

def agent_action(sandbox, agent_body, step_count):
    seat = sandbox.get_swing_seat()
    if seat is None:
        return

    pos = seat.position
    vel = seat.linearVelocity
    
    # Pivot at (10, 10).
    vx = vel.x
    target_y = 11.7
    
    # Increase force when moving towards center to add energy
    # Decrease force as we approach the target height to stabilize
    if pos.y < target_y:
        force_mag = 42.0
        # If moving away from center, apply force towards center
        if (pos.x < 10.0 and vx > 0) or (pos.x > 10.0 and vx < 0):
            sandbox.apply_force_to_seat(force_mag if vx > 0 else -force_mag, 0)
        elif (pos.x < 10.0 and vx < 0) or (pos.x > 10.0 and vx > 0):
            # Also apply force when moving away if we need a lot of energy
            sandbox.apply_force_to_seat(-force_mag if pos.x < 10.0 else force_mag, 0)
    else:
        # Stabilization near apex
        sandbox.apply_force_to_seat(-vx * 10.0, 0)
