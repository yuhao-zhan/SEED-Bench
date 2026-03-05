
import math

def build_agent(sandbox):
    return None

def agent_action(sandbox, agent_body, step_count):
    seat = sandbox.get_swing_seat()
    if seat is None:
        return

    pos = seat.position
    vel = seat.linearVelocity


    vx = vel.x
    target_y = 11.7



    if pos.y < target_y:
        force_mag = 42.0

        if (pos.x < 10.0 and vx > 0) or (pos.x > 10.0 and vx < 0):
            sandbox.apply_force_to_seat(force_mag if vx > 0 else -force_mag, 0)
        elif (pos.x < 10.0 and vx < 0) or (pos.x > 10.0 and vx > 0):

            sandbox.apply_force_to_seat(-force_mag if pos.x < 10.0 else force_mag, 0)
    else:

        sandbox.apply_force_to_seat(-vx * 10.0, 0)
