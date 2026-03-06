

import math





BARRIER_DELAY_STEPS = 70

ZONE_CENTERS = {"A": (2.0, 2.0), "B": (4.95, 3.2), "C": (8.0, 2.0)}

MAX_FORCE = 50.0

HOLD_RADIUS = 0.75

APPROACH_RADIUS = 2.0

GAIN_APPROACH = 6.0

GAIN_NORMAL = 15.0

HOLD_GAIN = 2.5

HOLD_DAMP = 5.5

APPROACH_DAMP = 1.8

RAMP_X_LO, RAMP_X_HI = 3.5, 6.0

RAMP_Y_TARGET = 3.2

RAMP_X_FRAC = 0.3

RAMP_Y_GAIN = 48.0





_step_when_a_triggered = [None]





def build_agent(sandbox):

    return sandbox.get_agent_body()





def agent_action(sandbox, agent_body, step_count):

    triggered = sandbox.get_triggered_switches()

    if triggered and triggered[0] == "A" and _step_when_a_triggered[0] is None:

        _step_when_a_triggered[0] = step_count



    next_switch = sandbox.get_next_required_switch()

    cooldown = getattr(sandbox, "get_cooldown_remaining", lambda: 0)()

    if next_switch is None:

        vx, vy = sandbox.get_agent_velocity()

        sandbox.apply_agent_force(-HOLD_DAMP * vx, -HOLD_DAMP * vy)

        return

    if cooldown > 0:

        vx, vy = sandbox.get_agent_velocity()

        sandbox.apply_agent_force(-HOLD_DAMP * vx, -HOLD_DAMP * vy)

        return





    if next_switch == "B" and _step_when_a_triggered[0] is not None:

        steps_since_a = step_count - _step_when_a_triggered[0]

        if steps_since_a < BARRIER_DELAY_STEPS:

            vx, vy = sandbox.get_agent_velocity()

            sandbox.apply_agent_force(-HOLD_DAMP * vx, -HOLD_DAMP * vy)

            return



    tx, ty = ZONE_CENTERS[next_switch]

    x, y = sandbox.get_agent_position()

    vx, vy = sandbox.get_agent_velocity()

    dx = tx - x

    dy = ty - y

    dist = math.sqrt(dx * dx + dy * dy)





    on_flat_for_c = (y <= 2.6 or x >= 6.4) and not (3.5 <= x < 4.5)

    if next_switch == "C" and x < 7.5 and dist > 0.2 and on_flat_for_c:

        fx = MAX_FORCE * 0.98 if dx > 0 else -MAX_FORCE * 0.4

        fy = -HOLD_DAMP * vy

        sandbox.apply_agent_force(fx, fy)

        return



    if dist < 1e-6:

        sandbox.apply_agent_force(-HOLD_DAMP * vx, -HOLD_DAMP * vy)

        return



    if dist < HOLD_RADIUS:

        speed = math.sqrt(vx * vx + vy * vy)



        if next_switch == "C" or speed > 0.35:

            fx = -HOLD_DAMP * 2.5 * vx

            fy = -HOLD_DAMP * 2.5 * vy

        else:

            fx = HOLD_GAIN * dx - HOLD_DAMP * vx

            fy = HOLD_GAIN * dy - HOLD_DAMP * vy

        mag = math.sqrt(fx * fx + fy * fy)

        if mag > MAX_FORCE:

            fx, fy = fx * MAX_FORCE / mag, fy * MAX_FORCE / mag

        sandbox.apply_agent_force(fx, fy)

        return



    in_ramp = RAMP_X_LO <= x <= RAMP_X_HI



    use_ramp = in_ramp and (next_switch == "B" or (next_switch == "C" and (x < 4.5 or y > 2.4)))

    if use_ramp:

        if next_switch == "B" or (next_switch == "C" and x < 4.5):



            y_target = RAMP_Y_TARGET

            fx = min(MAX_FORCE * 0.75, 36.0) * (1.0 if dx > 0 else -0.5) - APPROACH_DAMP * vx

            fy = RAMP_Y_GAIN * (y_target - y) - APPROACH_DAMP * vy

        else:



            y_target = 2.0

            dy_local = y_target - y

            if y > 3.0:

                fx = MAX_FORCE * 0.98 if dx > 0 else -MAX_FORCE * 0.3

                fy = -APPROACH_DAMP * vy

            else:

                fx = min(MAX_FORCE * 0.95, 47.0) * (1.0 if dx > 0 else 0.5) - APPROACH_DAMP * vx

                fy = RAMP_Y_GAIN * dy_local - APPROACH_DAMP * vy

        mag = math.sqrt(fx * fx + fy * fy)

        if mag > MAX_FORCE:

            fx, fy = fx * MAX_FORCE / mag, fy * MAX_FORCE / mag

        sandbox.apply_agent_force(fx, fy)

        return



    if dist < APPROACH_RADIUS:

        force_mag = min(MAX_FORCE * 0.35, GAIN_APPROACH * dist)

        ux = dx / dist if dist > 1e-6 else 0

        uy = dy / dist if dist > 1e-6 else 0

        fx = force_mag * ux - APPROACH_DAMP * vx

        fy = force_mag * uy - APPROACH_DAMP * vy

        mag = math.sqrt(fx * fx + fy * fy)

        if mag > MAX_FORCE:

            fx, fy = fx * MAX_FORCE / mag, fy * MAX_FORCE / mag

        sandbox.apply_agent_force(fx, fy)

        return



    gain = GAIN_NORMAL * 1.2 if next_switch == "B" else GAIN_NORMAL

    force_mag = min(MAX_FORCE, gain * dist)

    ux = dx / dist if dist > 1e-6 else 0

    uy = dy / dist if dist > 1e-6 else 0

    fx = force_mag * ux

    fy = force_mag * uy

    mag = math.sqrt(fx * fx + fy * fy)

    if mag > MAX_FORCE:

        fx, fy = fx * MAX_FORCE / mag, fy * MAX_FORCE / mag

    sandbox.apply_agent_force(fx, fy)

