# EVOLVE-BLOCK-START
def build_agent(sandbox):
    import math
    num_beams = 12
    radius = 1.3
    total_mass = 0.0
    beams = []
    
    # Create vertical beams around the core
    for i in range(num_beams):
        angle = 2 * math.pi * i / num_beams
        x = radius * math.cos(angle)
        y = 0.0
        beam = sandbox.add_beam(x, y, 0.1, 4.5, angle=0, density=1.0)
        beams.append(beam)
        total_mass += 0.1 * 4.5 * 1.0  # width * height * density
    
    # Create horizontal beams connecting vertical beams at y=4.5m
    for i in range(num_beams):
        angle = 2 * math.pi * i / num_beams
        x1 = radius * math.cos(angle)
        y1 = 4.5
        angle_next = 2 * math.pi * (i + 1) / num_beams
        x2 = radius * math.cos(angle_next)
        y2 = 4.5
        length = math.hypot(x2 - x1, y2 - y1)
        beam = sandbox.add_beam((x1 + x2)/2, y1, length, 0.1, angle=0, density=1.0)
        beams.append(beam)
        total_mass += length * 0.1 * 1.0  # length * height * density
    
    # Connect vertical and horizontal beams with rigid joints
    for i in range(num_beams):
        vertical_beam = beams[i]
        horizontal_beam = beams[num_beams + i]
        angle = 2 * math.pi * i / num_beams
        x_i = radius * math.cos(angle)
        anchor_point = (x_i, 4.5)
        sandbox.add_joint(vertical_beam, horizontal_beam, anchor_point, type='rigid')
    
    # Set low restitution for energy absorption
    for beam in beams:
        sandbox.set_material_properties(beam, restitution=0.2)
    
    # Ensure mass budget constraint
    if total_mass > 120:
        raise ValueError("Mass exceeds budget")
    
    return beams[0]
# EVOLVE-BLOCK-END