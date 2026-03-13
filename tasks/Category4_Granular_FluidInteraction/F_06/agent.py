import math

def _build_agent_impl(sandbox):
    beams = []
    for i in range(3):
        x = 6.5 + i * 1.0
        y = 0.5 + i * 0.7
        b = sandbox.add_beam(x, y, 1.1, 0.2, angle=0.6, density=50.0)
        sandbox.add_joint(b, None, (x, 0.0), type='rigid')
        beams.append(b)
    for i in range(9):
        x = 9.5 + i * 1.0
        y = 2.5
        b = sandbox.add_beam(x, y, 1.1, 0.2, angle=0, density=50.0)
        sandbox.add_joint(b, None, (x, 0.0), type='rigid')
        beams.append(b)
    return beams[0]

def build_agent(sandbox):
    return _build_agent_impl(sandbox)

def agent_action(sandbox, agent_body, step_count):
    if not hasattr(sandbox, "get_fluid_particles") or not hasattr(sandbox, "apply_force_to_particle"):
        return
    budget = getattr(sandbox, 'FORCE_BUDGET_PER_STEP', 12000.0)
    particles = sandbox.get_fluid_particles()
    if not particles:
        return
    def get_prio(p):
        px = p.position.x
        if 10.0 <= px <= 18.0: return 0
        if px < 10.0: return 1
        return 2
    particles.sort(key=get_prio)
    used = 0.0
    m = 25.0
    g = 10.0
    for p in particles:
        if used >= budget:
            break
        x, y = p.position.x, p.position.y
        vx, vy = p.linearVelocity.x, p.linearVelocity.y
        fx, fy = 0.0, 0.0
        if x > 22.0:
            fx = -m * 10.0 * (vx + 2.0)
            fy = m * g
        elif x >= 18.0:
            if abs(vx) > 0.2:
                fx = -m * 10.0 * vx
            if y > 0.2:
                fy = -m * 5.0
        elif x < 6.0:
            target_vx = 5.0
            target_vy = 2.0
            fx = m * 5.0 * (target_vx - vx)
            fy = m * (g + 5.0 * (target_vy - vy))
        else:
            target_vx = 6.0
            target_vy = 0.0
            if y < 2.6:
                target_vy = 3.0
            fx = m * 5.0 * (target_vx - vx)
            fy = m * (g + 5.0 * (target_vy - vy))
            if y > 3.0:
                fx += 150.0
        mag = math.sqrt(fx*fx + fy*fy)
        if mag > 0:
            if used + mag <= budget:
                sandbox.apply_force_to_particle(p, fx, fy)
                used += mag
            else:
                scale = (budget - used) / mag
                if scale > 0.1:
                    sandbox.apply_force_to_particle(p, fx * scale, fy * scale)
                    used = budget

def build_agent_stage_1(sandbox):
    beams = []
    pipeline_y = 2.5
    num_slanted = 5
    dx = 0.8
    for i in range(num_slanted):
        x = 6.5 + i * dx
        y = 0.5 + i * (pipeline_y - 0.5) / (num_slanted - 1)
        angle = math.atan2((pipeline_y - 0.5) / (num_slanted - 1), dx)
        b = sandbox.add_beam(x, y, 1.1, 0.2, angle=angle, density=50.0)
        sandbox.add_joint(b, None, (x, 0.0), type='rigid')
        beams.append(b)
    start_flat_x = 6.5 + (num_slanted - 1) * dx + 0.8
    for i in range(15):
        x = start_flat_x + i * 0.9
        if x > 17.9: break
        y = pipeline_y
        b = sandbox.add_beam(x, y, 1.1, 0.2, angle=0, density=50.0)
        sandbox.add_joint(b, None, (x, 0.0), type='rigid')
        beams.append(b)
    return beams[0]

def agent_action_stage_1(sandbox, agent_body, step_count):
    if not hasattr(sandbox, "get_fluid_particles") or not hasattr(sandbox, "apply_force_to_particle"):
        return
    budget = 5000.0
    particles = sandbox.get_fluid_particles()
    if not particles: return
    def get_prio(p):
        px = p.position.x
        if 10.0 <= px < 18.0: return 0
        if px < 10.0: return 1
        return 2
    particles.sort(key=get_prio)
    m = 25.13
    used = 0.0
    target_y_min = 0.0
    target_y_max = 1.5
    ty_target = (target_y_min + target_y_max) / 2.0
    gravity_y = 10.0
    viscosity = 20.0
    pipeline_y = 2.5
    tx_base = 10.0
    for p in particles:
        if used >= budget: break
        x, y = p.position.x, p.position.y
        vx, vy = p.linearVelocity.x, p.linearVelocity.y
        tx = tx_base
        ty = ty_target
        if x >= 18.0:
            tx = 0.0
            ax = (tx - vx) * 2.0
            ay = (ty - y) * 5.0 + (0.0 - vy) * 2.0 + gravity_y
        elif x < 6.5:
            tx = tx_base * 0.8
            ty = 1.2
            ax = (tx - vx) * 10.0
            ay = (ty - y) * 20.0 + (0.0 - vy) * 10.0 + gravity_y
        else:
            if x < 10.0:
                ty = 0.5 + (x - 6.5) * (pipeline_y - 0.5) / 3.2 + 0.3
            else:
                ty = pipeline_y + 0.3
            ax = (tx - vx) * 10.0
            ay = (ty - y) * 20.0 + (0.0 - vy) * 10.0 + gravity_y
        ax += vx * viscosity * 0.1
        ay += vy * viscosity * 0.1
        fx = m * ax
        fy = m * ay
        mag = math.sqrt(fx*fx + fy*fy)
        if mag > 0:
            scale = min(1.0, (budget - used) / mag)
            sandbox.apply_force_to_particle(p, fx * scale, fy * scale)
            used += mag * scale

def build_agent_stage_2(sandbox):
    beams = []
    pipeline_y = 3.2
    num_slanted = 5
    dx = 0.8
    for i in range(num_slanted):
        x = 6.5 + i * dx
        y = 0.5 + i * (pipeline_y - 0.5) / (num_slanted - 1)
        angle = math.atan2((pipeline_y - 0.5) / (num_slanted - 1), dx)
        b = sandbox.add_beam(x, y, 1.1, 0.2, angle=angle, density=50.0)
        sandbox.add_joint(b, None, (x, 0.0), type='rigid')
        beams.append(b)
    start_flat_x = 6.5 + (num_slanted - 1) * dx + 0.8
    for i in range(15):
        x = start_flat_x + i * 0.9
        if x > 17.9: break
        y = pipeline_y
        b = sandbox.add_beam(x, y, 1.1, 0.2, angle=0, density=50.0)
        sandbox.add_joint(b, None, (x, 0.0), type='rigid')
        beams.append(b)
    return beams[0]

def agent_action_stage_2(sandbox, agent_body, step_count):
    if not hasattr(sandbox, "get_fluid_particles") or not hasattr(sandbox, "apply_force_to_particle"):
        return
    budget = getattr(sandbox, 'FORCE_BUDGET_PER_STEP', 12000.0)
    particles = sandbox.get_fluid_particles()
    if not particles: return
    def get_prio(p):
        px = p.position.x
        if 10.0 <= px < 18.0: return 0
        if px < 10.0: return 1
        return 2
    particles.sort(key=get_prio)
    m = 25.13
    used = 0.0
    target_y_min = 2.5
    target_y_max = 4.0
    ty_target = (target_y_min + target_y_max) / 2.0
    gravity_y = 10.0
    viscosity = 0.25
    pipeline_y = 3.2
    tx_base = 10.0
    for p in particles:
        if used >= budget: break
        x, y = p.position.x, p.position.y
        vx, vy = p.linearVelocity.x, p.linearVelocity.y
        tx = tx_base
        ty = ty_target
        if x >= 18.0:
            tx = 0.0
            ax = (tx - vx) * 2.0
            ay = (ty - y) * 5.0 + (0.0 - vy) * 2.0 + gravity_y
        elif x < 6.5:
            tx = tx_base * 0.8
            ty = 1.2
            ax = (tx - vx) * 10.0
            ay = (ty - y) * 20.0 + (0.0 - vy) * 10.0 + gravity_y
        else:
            if x < 10.0:
                ty = 0.5 + (x - 6.5) * (pipeline_y - 0.5) / 3.2 + 0.3
            else:
                ty = pipeline_y + 0.3
            ax = (tx - vx) * 10.0
            ay = (ty - y) * 20.0 + (0.0 - vy) * 10.0 + gravity_y
        ax += vx * viscosity * 0.1
        ay += vy * viscosity * 0.1
        fx = m * ax
        fy = m * ay
        mag = math.sqrt(fx*fx + fy*fy)
        if mag > 0:
            scale = min(1.0, (budget - used) / mag)
            sandbox.apply_force_to_particle(p, fx * scale, fy * scale)
            used += mag * scale

def build_agent_stage_3(sandbox):
    beams = []
    pipeline_y = 2.5
    num_slanted = 5
    dx = 0.8
    for i in range(num_slanted):
        x = 6.5 + i * dx
        y = 0.5 + i * (pipeline_y - 0.5) / (num_slanted - 1)
        angle = math.atan2((pipeline_y - 0.5) / (num_slanted - 1), dx)
        b = sandbox.add_beam(x, y, 1.1, 0.2, angle=angle, density=50.0)
        sandbox.add_joint(b, None, (x, 0.0), type='rigid')
        beams.append(b)
    start_flat_x = 6.5 + (num_slanted - 1) * dx + 0.8
    for i in range(15):
        x = start_flat_x + i * 0.9
        if x > 17.9: break
        y = pipeline_y
        b = sandbox.add_beam(x, y, 1.1, 0.2, angle=0, density=50.0)
        sandbox.add_joint(b, None, (x, 0.0), type='rigid')
        beams.append(b)
    return beams[0]

def agent_action_stage_3(sandbox, agent_body, step_count):
    if not hasattr(sandbox, "get_fluid_particles") or not hasattr(sandbox, "apply_force_to_particle"):
        return
    budget = getattr(sandbox, 'FORCE_BUDGET_PER_STEP', 12000.0)
    particles = sandbox.get_fluid_particles()
    if not particles: return
    def get_prio(p):
        px = p.position.x
        if 10.0 <= px < 18.0: return 0
        if px < 10.0: return 1
        return 2
    particles.sort(key=get_prio)
    m = 25.13
    used = 0.0
    target_y_min = 0.0
    target_y_max = 1.5
    ty_target = (target_y_min + target_y_max) / 2.0
    gravity_y = 10.0
    viscosity = 30.0
    pipeline_y = 2.5
    tx_base = 10.0
    for p in particles:
        if used >= budget: break
        x, y = p.position.x, p.position.y
        vx, vy = p.linearVelocity.x, p.linearVelocity.y
        tx = tx_base
        ty = ty_target
        if x >= 18.0:
            tx = 0.0
            ax = (tx - vx) * 2.0
            ay = (ty - y) * 5.0 + (0.0 - vy) * 2.0 + gravity_y
        elif x < 6.5:
            tx = tx_base * 0.8
            ty = 1.2
            ax = (tx - vx) * 10.0
            ay = (ty - y) * 20.0 + (0.0 - vy) * 10.0 + gravity_y
        else:
            if x < 10.0:
                ty = 0.5 + (x - 6.5) * (pipeline_y - 0.5) / 3.2 + 0.3
            else:
                ty = pipeline_y + 0.3
            ax = (tx - vx) * 10.0
            ay = (ty - y) * 20.0 + (0.0 - vy) * 10.0 + gravity_y
        ax += vx * viscosity * 0.1
        ay += vy * viscosity * 0.1
        fx = m * ax
        fy = m * ay
        mag = math.sqrt(fx*fx + fy*fy)
        if mag > 0:
            scale = min(1.0, (budget - used) / mag)
            sandbox.apply_force_to_particle(p, fx * scale, fy * scale)
            used += mag * scale

def build_agent_stage_4(sandbox):
    beams = []
    pipeline_y = 3.2
    num_slanted = 5
    dx = 0.8
    for i in range(num_slanted):
        x = 6.5 + i * dx
        y = 0.5 + i * (pipeline_y - 0.5) / (num_slanted - 1)
        angle = math.atan2((pipeline_y - 0.5) / (num_slanted - 1), dx)
        b = sandbox.add_beam(x, y, 1.1, 0.2, angle=angle, density=50.0)
        sandbox.add_joint(b, None, (x, 0.0), type='rigid')
        beams.append(b)
    start_flat_x = 6.5 + (num_slanted - 1) * dx + 0.8
    for i in range(15):
        x = start_flat_x + i * 0.9
        if x > 17.9: break
        y = pipeline_y
        b = sandbox.add_beam(x, y, 1.1, 0.2, angle=0, density=50.0)
        sandbox.add_joint(b, None, (x, 0.0), type='rigid')
        beams.append(b)
    return beams[0]

def agent_action_stage_4(sandbox, agent_body, step_count):
    if not hasattr(sandbox, "get_fluid_particles") or not hasattr(sandbox, "apply_force_to_particle"):
        return
    budget = getattr(sandbox, 'FORCE_BUDGET_PER_STEP', 12000.0)
    particles = sandbox.get_fluid_particles()
    if not particles: return
    def get_prio(p):
        px = p.position.x
        if 10.0 <= px < 18.0: return 0
        if px < 10.0: return 1
        return 2
    particles.sort(key=get_prio)
    m = 25.13
    used = 0.0
    target_y_min = 2.5
    target_y_max = 4.0
    ty_target = (target_y_min + target_y_max) / 2.0
    gravity_y = 15.0
    viscosity = 2.0
    pipeline_y = 3.2
    tx_base = 10.0
    for p in particles:
        if used >= budget: break
        x, y = p.position.x, p.position.y
        vx, vy = p.linearVelocity.x, p.linearVelocity.y
        tx = tx_base
        ty = ty_target
        if x >= 18.0:
            tx = 0.0
            ax = (tx - vx) * 2.0
            ay = (ty - y) * 5.0 + (0.0 - vy) * 2.0 + gravity_y
        elif x < 6.5:
            tx = tx_base * 0.8
            ty = 1.2
            ax = (tx - vx) * 10.0
            ay = (ty - y) * 20.0 + (0.0 - vy) * 10.0 + gravity_y
        else:
            if x < 10.0:
                ty = 0.5 + (x - 6.5) * (pipeline_y - 0.5) / 3.2 + 0.3
            else:
                ty = pipeline_y + 0.3
            ax = (tx - vx) * 10.0
            ay = (ty - y) * 20.0 + (0.0 - vy) * 10.0 + gravity_y
        ax += vx * viscosity * 0.1
        ay += vy * viscosity * 0.1
        fx = m * ax
        fy = m * ay
        mag = math.sqrt(fx*fx + fy*fy)
        if mag > 0:
            scale = min(1.0, (budget - used) / mag)
            sandbox.apply_force_to_particle(p, fx * scale, fy * scale)
            used += mag * scale
