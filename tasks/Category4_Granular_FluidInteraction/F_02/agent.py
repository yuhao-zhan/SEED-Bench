import math

def build_agent(sandbox):
    beam_w = 0.62
    beam_h = 0.35
    density = 35.0
    centers_x = [2.31 + i * 0.62 for i in range(9)]
    y_center = 0.5 + beam_h / 2
    bodies = []
    for x in centers_x:
        b = sandbox.add_beam(x, y_center, beam_w, beam_h, angle=0, density=density)
        sandbox.set_material_properties(b, restitution=0.05)
        bodies.append(b)
    for i in range(8):
        anchor_x = (centers_x[i] + centers_x[i + 1]) / 2
        sandbox.add_joint(bodies[i], bodies[i + 1], (anchor_x, y_center), type='rigid')
    return bodies[-1]

def agent_action(sandbox, agent_body, step_count):
    if agent_body is None or not agent_body.active:
        return
    front_x = sandbox.get_vehicle_front_x() or agent_body.position.x
    target_x = 26.0
    if front_x >= target_x + 0.1:
        for b in sandbox.bodies:
            if b.active:
                b.linearVelocity = (0, 0)
                b.angularVelocity = 0
        return
    THRUST_F = 520.0
    LIFT_F = 400.0
    in_danger_zone = (12.0 <= front_x <= 22.0)
    for b in sandbox.bodies:
        if not b.active: continue
        fx = THRUST_F
        fy = 0.0
        if in_danger_zone:
            fy = LIFT_F
        vx = b.linearVelocity.x
        if vx > 1.8: fx *= 0.1
        elif vx > 1.0: fx *= 0.4
        sandbox.apply_force(b, fx, fy, step_count=step_count)
