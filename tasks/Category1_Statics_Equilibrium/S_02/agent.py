import math

def build_advanced_tower(sandbox, levels=25, base_w=4.0, beam_h=1.5, base_density=200.0, top_density=5.0,
                         taper_rate=0.8, density_taper=0.95, tmd_params=None):
    foundation_y = 1.0
    foundation = sandbox._terrain_bodies.get("foundation")
    base = sandbox.add_beam(x=0, y=foundation_y + beam_h/2, width=base_w, height=beam_h, density=base_density)
    if foundation:
        num_joints = max(4, int(base_w * 0.8))
        for i in range(num_joints):
            ax = -(base_w/2 - 0.1) + (i * (base_w-0.2)/(num_joints-1))
            sandbox.add_joint(foundation, base, (ax, foundation_y), type='rigid')
    prev = base
    prev_y = foundation_y + beam_h/2
    beams = [base]
    for i in range(1, levels):
        curr_y = prev_y + beam_h
        progress = i / (levels - 1)
        curr_w = max(0.4, base_w * (1.0 - progress**taper_rate))
        d = max(top_density, base_density * (1.0 - progress**density_taper))
        b = sandbox.add_beam(x=0, y=curr_y, width=curr_w, height=beam_h, density=d)
        anchor_y = curr_y - beam_h/2
        j_count = 3 if curr_w > 1.5 else 2
        for j in range(j_count):
            jx = -(curr_w/2 - 0.05) + (j * (curr_w-0.1)/(j_count-1))
            sandbox.add_joint(prev, b, (jx, anchor_y), type='rigid')
        prev = b
        prev_y = curr_y
        beams.append(b)
    if tmd_params:
        top = beams[-1]
        mass_w, mass_h = tmd_params.get('size', (1.0, 1.0))
        mass_d = tmd_params.get('density', 100.0)
        stiff = tmd_params.get('stiffness', 4.0)
        damp = tmd_params.get('damping', 0.9)
        tmd_body = sandbox.add_beam(x=0, y=prev_y + 1.5, width=mass_w, height=mass_h, density=mass_d)
        sandbox.add_spring(top, tmd_body, (0, prev_y + beam_h/2), (0, 0), stiffness=stiff, damping=damp)
    return base

def build_agent(sandbox):
    return build_advanced_tower(sandbox, levels=22, base_w=4.0)

def agent_action(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    return build_advanced_tower(sandbox, levels=22, base_w=4.0,
                               base_density=45.0, top_density=1.0,
                               taper_rate=0.7, density_taper=0.65)

def build_agent_stage_2(sandbox):
    tmd = {"size": (1.0, 1.0), "density": 350.0, "stiffness": 20.0, "damping": 0.98}
    return build_advanced_tower(
        sandbox, levels=22, base_w=4.0,
        base_density=45.0, top_density=1.0,
        taper_rate=0.7, density_taper=0.65,
        tmd_params=tmd,
    )

def build_agent_stage_3(sandbox):
    tmd = {"size": (1.0, 1.0), "density": 320.0, "stiffness": 18.0, "damping": 0.97}
    return build_advanced_tower(
        sandbox, levels=22, base_w=4.0,
        base_density=45.0, top_density=1.0,
        taper_rate=0.7, density_taper=0.65,
        tmd_params=tmd,
    )

def build_agent_stage_4(sandbox):
    tmd = {"size": (0.95, 0.95), "density": 280.0, "stiffness": 22.0, "damping": 0.96}
    return build_advanced_tower(
        sandbox, levels=22, base_w=4.0,
        base_density=38.0, top_density=0.85,
        taper_rate=0.68, density_taper=0.62,
        tmd_params=tmd,
    )

def agent_action_stage_1(sandbox, agent_body, step_count): pass

def agent_action_stage_2(sandbox, agent_body, step_count): pass

def agent_action_stage_3(sandbox, agent_body, step_count): pass

def agent_action_stage_4(sandbox, agent_body, step_count): pass
