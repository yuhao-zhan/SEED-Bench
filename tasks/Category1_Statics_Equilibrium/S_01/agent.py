
import math

def build_truss(sandbox, start_x, end_x, top_y, bottom_y, num_panels, deck_density=50.0, truss_density=20.0, joint_type='rigid'):

    gap_width = end_x - start_x
    panel_width = gap_width / num_panels
    deck_height = 0.4

    deck_beams = []
    for i in range(num_panels):
        cx = start_x + (i + 0.5) * panel_width
        b = sandbox.add_beam(x=cx, y=top_y, width=panel_width+0.01, height=deck_height, density=deck_density)
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



def build_agent(sandbox):
    L_X, R_X = 10.0, 25.0

    deck, bottom, v_beams = build_truss(sandbox, L_X, R_X, 9.8, 8.5, 5, deck_density=30.0, truss_density=15.0, joint_type='rigid')

    sandbox.add_joint(v_beams[0], None, (L_X, 9.8), type='rigid')
    sandbox.add_joint(v_beams[-1], None, (R_X, 9.8), type='rigid')


    ext = sandbox.add_beam(x=R_X+2.5, y=9.8, width=5.0, height=0.4, density=30.0)
    sandbox.add_joint(v_beams[-1], ext, (R_X, 9.8), type='rigid')
    return deck[0]

def agent_action(sandbox, agent_body, step_count):
    pass



def build_agent_stage_1(sandbox):

    L_X, R_X = 10.0, 25.0

    deck, bottom, v_beams = build_truss(sandbox, L_X, R_X, 9.8, 7.5, 6, deck_density=30.0, truss_density=15.0, joint_type='rigid')
    for y in [9.8, 8.6, 7.5]:
        sandbox.add_joint(v_beams[0], None, (L_X, y), type='rigid')
        sandbox.add_joint(v_beams[-1], None, (R_X, y), type='rigid')
    ext = sandbox.add_beam(x=R_X+2.5, y=9.8, width=5.0, height=0.4, density=30.0)
    sandbox.add_joint(v_beams[-1], ext, (R_X, 9.8), type='rigid')
    return deck[0]

def build_agent_stage_2(sandbox):

    L_X, R_X = 10.0, 25.0

    deck, bottom, v_beams = build_truss(sandbox, L_X, R_X, 9.8, 7.5, 8, deck_density=30.0, truss_density=15.0, joint_type='rigid')
    for y in [9.8, 7.5]:
        sandbox.add_joint(v_beams[0], None, (L_X, y), type='rigid')
        sandbox.add_joint(v_beams[-1], None, (R_X, y), type='rigid')
    ext = sandbox.add_beam(x=R_X+2.5, y=9.8, width=5.0, height=0.4, density=30.0)
    sandbox.add_joint(v_beams[-1], ext, (R_X, 9.8), type='rigid')
    return deck[0]

def build_agent_stage_3(sandbox):

    L_X, R_X = 10.0, 25.0

    deck, bottom, v_beams = build_truss(sandbox, L_X, R_X, 9.8, 7.0, 8, deck_density=50.0, truss_density=20.0, joint_type='rigid')
    for y in [9.8, 8.4, 7.0]:
        sandbox.add_joint(v_beams[0], None, (L_X, y), type='rigid')
        sandbox.add_joint(v_beams[-1], None, (R_X, y), type='rigid')
    ext = sandbox.add_beam(x=R_X+2.5, y=9.8, width=5.0, height=0.4, density=30.0)
    sandbox.add_joint(v_beams[-1], ext, (R_X, 9.8), type='rigid')
    return deck[0]

def build_agent_stage_4(sandbox):

    L_X, R_X = 10.0, 35.0

    deck, bottom, v_beams = build_truss(sandbox, L_X, R_X, 10.0, 6.5, 12, deck_density=32.0, truss_density=12.0, joint_type='rigid')
    for y in [10.0, 8.25, 6.5]:
        sandbox.add_joint(v_beams[0], None, (L_X, y), type='rigid')
        sandbox.add_joint(v_beams[-1], None, (R_X, y), type='rigid')

    ext_width = 5.5
    ext = sandbox.add_beam(x=R_X + ext_width/2, y=10.0, width=ext_width, height=0.4, density=20.0)
    sandbox.add_joint(v_beams[-1], ext, (R_X, 10.0), type='rigid')
    return deck[0]

def agent_action_stage_1(sandbox, agent_body, step_count): pass
def agent_action_stage_2(sandbox, agent_body, step_count): pass
def agent_action_stage_3(sandbox, agent_body, step_count): pass
def agent_action_stage_4(sandbox, agent_body, step_count): pass
