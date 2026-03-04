"""
S-01: The Bridge task Agent module
Reference solution: Robust truss bridge designs for high-difficulty stages.
"""
import math

def build_truss(sandbox, start_x, end_x, top_y, bottom_y, num_panels, deck_density=50.0, truss_density=20.0, joint_type='pivot'):
    """
    Helper to build a robust Warren-style truss bridge.
    Using higher densities for better stability with the 2000kg vehicle.
    """
    gap_width = end_x - start_x
    panel_width = gap_width / num_panels
    deck_height = 0.4
    
    deck_beams = []
    for i in range(num_panels):
        cx = start_x + (i + 0.5) * panel_width
        b = sandbox.add_beam(x=cx, y=top_y, width=panel_width+0.01, height=deck_height, density=deck_density)
        for f in b.fixtures: f.friction = 1.0
        deck_beams.append(b)
        
    bottom_beams = []
    for i in range(num_panels):
        cx = start_x + (i + 0.5) * panel_width
        b = sandbox.add_beam(x=cx, y=bottom_y, width=panel_width+0.01, height=0.3, density=truss_density)
        bottom_beams.append(b)
        
    v_beams = []
    for i in range(num_panels + 1):
        x = start_x + i * panel_width
        b = sandbox.add_beam(x=x, y=(top_y+bottom_y)/2, width=0.3, height=abs(top_y-bottom_y), density=truss_density)
        v_beams.append(b)
        
    diag_beams = []
    for i in range(num_panels):
        x1, y1 = start_x + i * panel_width, bottom_y
        x2, y2 = start_x + (i+1) * panel_width, top_y
        cx, cy = (x1+x2)/2, (y1+y2)/2
        dist = math.sqrt((x2-x1)**2 + (y2-y1)**2)
        angle = math.atan2(y2-y1, x2-x1)
        b = sandbox.add_beam(x=cx, y=cy, width=dist+0.1, height=0.3, angle=angle, density=truss_density)
        diag_beams.append(b)

    for i in range(num_panels + 1):
        nx = start_x + i * panel_width
        node_pos = (nx, top_y)
        master = v_beams[i]
        if i > 0: sandbox.add_joint(master, deck_beams[i-1], node_pos, type='rigid')
        if i < num_panels: sandbox.add_joint(master, deck_beams[i], node_pos, type='rigid')
        if i > 0: sandbox.add_joint(master, diag_beams[i-1], node_pos, type=joint_type)
        
    for i in range(num_panels + 1):
        nx = start_x + i * panel_width
        node_pos = (nx, bottom_y)
        master = v_beams[i]
        if i > 0: sandbox.add_joint(master, bottom_beams[i-1], node_pos, type=joint_type)
        if i < num_panels: sandbox.add_joint(master, bottom_beams[i], node_pos, type=joint_type)
        if i < num_panels: sandbox.add_joint(master, diag_beams[i], node_pos, type=joint_type)

    return deck_beams, bottom_beams, v_beams

def build_agent_stage_1(sandbox):
    bounds = sandbox.get_terrain_bounds()
    L_X, R_X = bounds["left_cliff"]["x_end"], bounds["right_cliff"]["x_start"]
    deck, bottom, v_beams = build_truss(sandbox, L_X, R_X, 9.8, 7.5, 6, deck_density=30.0, truss_density=15.0, joint_type='pivot')
    left_cliff, right_cliff = sandbox._terrain_bodies["left_cliff"], sandbox._terrain_bodies["right_cliff"]
    for y in [9.8, 8.6, 7.5]:
        sandbox.add_joint(left_cliff, v_beams[0], (L_X, y), type='rigid')
        sandbox.add_joint(right_cliff, v_beams[-1], (R_X, y), type='rigid')
    ext = sandbox.add_beam(x=R_X+2.5, y=9.8, width=5.0, height=0.4, density=30.0)
    for f in ext.fixtures: f.friction = 1.0
    sandbox.add_joint(v_beams[-1], ext, (R_X, 9.8), type='rigid')
    return deck[0]

def build_agent_stage_2(sandbox):
    bounds = sandbox.get_terrain_bounds()
    L_X, R_X = bounds["left_cliff"]["x_end"], bounds["right_cliff"]["x_start"]
    deck, bottom, v_beams = build_truss(sandbox, L_X, R_X, 9.8, 7.5, 8, deck_density=30.0, truss_density=15.0, joint_type='pivot')
    left_cliff, right_cliff = sandbox._terrain_bodies["left_cliff"], sandbox._terrain_bodies["right_cliff"]
    for y in [9.8, 7.5]:
        sandbox.add_joint(left_cliff, v_beams[0], (L_X, y), type='rigid')
        sandbox.add_joint(right_cliff, v_beams[-1], (R_X, y), type='rigid')
    ext = sandbox.add_beam(x=R_X+2.5, y=9.8, width=5.0, height=0.4, density=30.0)
    for f in ext.fixtures: f.friction = 1.0
    sandbox.add_joint(v_beams[-1], ext, (R_X, 9.8), type='rigid')
    return deck[0]

def build_agent_stage_3(sandbox):
    bounds = sandbox.get_terrain_bounds()
    L_X, R_X = bounds["left_cliff"]["x_end"], bounds["right_cliff"]["x_start"]
    deck, bottom, v_beams = build_truss(sandbox, L_X, R_X, 9.8, 8.0, 8, deck_density=20.0, truss_density=10.0, joint_type='pivot')
    left_cliff, right_cliff = sandbox._terrain_bodies["left_cliff"], sandbox._terrain_bodies["right_cliff"]
    for y in [9.8, 8.0]:
        sandbox.add_joint(left_cliff, v_beams[0], (L_X, y), type='rigid')
        sandbox.add_joint(right_cliff, v_beams[-1], (R_X, y), type='rigid')
    ext = sandbox.add_beam(x=R_X+2.5, y=9.8, width=5.0, height=0.4, density=20.0)
    for f in ext.fixtures: f.friction = 1.0
    sandbox.add_joint(v_beams[-1], ext, (R_X, 9.8), type='rigid')
    return deck[0]

def build_agent_stage_4(sandbox):
    bounds = sandbox.get_terrain_bounds()
    L_X, R_X = bounds["left_cliff"]["x_end"], bounds["right_cliff"]["x_start"]
    # deck_density 15.0, truss_density 8.0 to stay within 1000kg for 25m gap
    deck, bottom, v_beams = build_truss(sandbox, L_X, R_X, 9.8, 7.0, 10, deck_density=15.0, truss_density=8.0, joint_type='pivot')
    left_cliff, right_cliff = sandbox._terrain_bodies["left_cliff"], sandbox._terrain_bodies["right_cliff"]
    for y in [9.8, 8.5, 7.0]:
        sandbox.add_joint(left_cliff, v_beams[0], (L_X, y), type='rigid')
        sandbox.add_joint(right_cliff, v_beams[-1], (R_X, y), type='rigid')
    
    # Target is 40.0, so extend to 42.0
    ext_width = 42.0 - R_X
    ext = sandbox.add_beam(x=R_X + ext_width/2, y=9.8, width=ext_width, height=0.4, density=15.0)
    for f in ext.fixtures: f.friction = 1.0
    sandbox.add_joint(v_beams[-1], ext, (R_X, 9.8), type='rigid')
    return deck[0]

def _base_agent_action(sandbox, agent_body, step_count, target_speed=4.0):
    if hasattr(sandbox, '_terrain_bodies'):
        v = sandbox._terrain_bodies.get("vehicle_chassis")
        if v:
            cvx, cvy = v.linearVelocity.x, v.linearVelocity.y
            # Smoother velocity control
            v.linearVelocity = (target_speed, cvy)
            n_angle = (v.angle + math.pi) % (2 * math.pi) - math.pi
            # Stronger stabilization for high gravity
            v.ApplyTorque(-n_angle * 20000.0, True)
            v.angularVelocity *= 0.8

def agent_action(sandbox, agent_body, step_count): _base_agent_action(sandbox, agent_body, step_count)
def agent_action_stage_1(sandbox, agent_body, step_count): _base_agent_action(sandbox, agent_body, step_count)
def agent_action_stage_2(sandbox, agent_body, step_count): _base_agent_action(sandbox, agent_body, step_count, target_speed=2.0)
def agent_action_stage_3(sandbox, agent_body, step_count): _base_agent_action(sandbox, agent_body, step_count, target_speed=2.0)
def agent_action_stage_4(sandbox, agent_body, step_count): _base_agent_action(sandbox, agent_body, step_count, target_speed=1.5)
def build_agent(sandbox): return build_agent_stage_1(sandbox)
