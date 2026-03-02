"""
S-02: The Skyscraper task Agent module
Build a tall tower that survives earthquake and wind.
Reference solutions for initial and mutated tasks.
"""
import math

def build_agent(sandbox):
    """
    Initial Task Reference Solution.
    Build a tall skyscraper structure that can:
    1. Reach height > 30m
    2. Survive earthquake (horizontal oscillation starting at t=2s)
    3. Resist wind forces (100N lateral force above y=20m)
    4. Maintain stability (center of mass within x=[-4, 4])
    """
    # Foundation constraints
    FOUNDATION_X_MIN = -2.0
    FOUNDATION_X_MAX = 2.0
    TARGET_HEIGHT = 30.0
    MAX_WIDTH = 8.0
    
    # Design parameters
    BASE_WIDTH = 1.8 
    BEAM_HEIGHT = 0.8
    BOTTOM_BEAM_WIDTH = 1.8
    MID_BEAM_WIDTH = 1.4
    TOP_BEAM_WIDTH = 0.8
    NUM_LEVELS = 45  # Increased from 42 to provide more height buffer
    
    BOTTOM_SECTION_HEIGHT = 20.0 
    MID_SECTION_HEIGHT = 30.0
    foundation_y = 1.0
    base_center_x = 0.0
    
    # Build MULTIPLE base beams
    base_beams = []
    num_base_beams = 3
    base_spacing = BOTTOM_BEAM_WIDTH / (num_base_beams + 1)
    for i in range(num_base_beams):
        base_x = base_center_x - BOTTOM_BEAM_WIDTH/2 + (i + 1) * base_spacing
        base_y = foundation_y + BEAM_HEIGHT * 1.5 
        base_beam = sandbox.add_beam(x=base_x, y=base_y, width=BOTTOM_BEAM_WIDTH / num_base_beams * 0.9,
                                    height=BEAM_HEIGHT * 3.0, density=20.0)
        base_beams.append(base_beam)
        foundation = sandbox._terrain_bodies.get("foundation")
        if foundation:
            num_anchors = 7
            bw = BOTTOM_BEAM_WIDTH / num_base_beams * 0.9
            for j in range(num_anchors):
                ax = base_x - bw/2 + (j * bw / (num_anchors - 1))
                sandbox.add_joint(foundation, base_beam, (ax, foundation_y), type='rigid')
    
    # Connect base beams
    for i in range(len(base_beams) - 1):
        num_conn = 9
        cx = (base_beams[i].position.x + base_beams[i+1].position.x) / 2.0
        for j in range(num_conn):
            jy = foundation_y + (j * BEAM_HEIGHT * 3.0 / (num_conn - 1))
            sandbox.add_joint(base_beams[i], base_beams[i+1], (cx, jy), type='rigid')
    
    base_beam = base_beams[len(base_beams) // 2]
    previous_beam = base_beam
    previous_y = foundation_y + BEAM_HEIGHT * 1.5
    beams = list(base_beams)
    
    for i in range(1, NUM_LEVELS):
        current_y = previous_y + BEAM_HEIGHT
        if current_y <= BOTTOM_SECTION_HEIGHT:
            t = (BOTTOM_SECTION_HEIGHT - current_y) / BOTTOM_SECTION_HEIGHT
            w = MID_BEAM_WIDTH + (BOTTOM_BEAM_WIDTH - MID_BEAM_WIDTH) * t
            d = 12.0 
        elif current_y <= MID_SECTION_HEIGHT:
            t = (MID_SECTION_HEIGHT - current_y) / (MID_SECTION_HEIGHT - BOTTOM_SECTION_HEIGHT)
            w = TOP_BEAM_WIDTH + (MID_BEAM_WIDTH - TOP_BEAM_WIDTH) * (1 - t)
            d = 8.0 
        else:
            w = TOP_BEAM_WIDTH
            d = 5.0 
        
        current_beam = sandbox.add_beam(x=base_center_x, y=current_y, width=w, height=BEAM_HEIGHT, density=d)
        
        num_joints = 25
        for j in range(num_joints):
            jx = base_center_x - w/2 + (j * w / (num_joints - 1))
            sandbox.add_joint(previous_beam, current_beam, (jx, previous_y + BEAM_HEIGHT / 2), type='rigid')
        
        if current_y <= BOTTOM_SECTION_HEIGHT:
            for bb in base_beams:
                if bb != previous_beam:
                    sandbox.add_joint(bb, current_beam, (base_center_x, previous_y + BEAM_HEIGHT / 2), type='rigid')
        
        beams.append(current_beam)
        previous_beam = current_beam
        previous_y = current_y
    
    # TMD System
    top_beam = beams[-1]
    top_damper = sandbox.add_beam(x=base_center_x, y=previous_y + 0.6, width=1.0, height=1.0, density=2.0)
    sandbox.add_spring(top_beam, top_damper, (base_center_x, previous_y + BEAM_HEIGHT / 2), (0, 0), stiffness=1.85, damping=0.95)
    
    return base_beam

def agent_action(sandbox, agent_body, step_count):
    pass

# --- Mutation Stage Solutions ---

def build_agent_stage_1(sandbox):
    """
    Stage-1: 6.0m Amplitude Earthquake.
    Strategy: Ultra-heavy central leg and massive foundation plate to lower CoM.
    We also use thicker beams to maintain height.
    """
    return _build_extreme_tower(sandbox, base_density=5000.0, tower_scale=5.0, earthquake_freq=2.0)

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def build_agent_stage_2(sandbox):
    """
    Stage-2: 600N Wind.
    Strategy: Wide base, heavy bottom section to resist tipping torque.
    """
    return _build_extreme_tower(sandbox, base_density=2000.0, tower_scale=3.0, earthquake_freq=2.0)

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def build_agent_stage_3(sandbox):
    """
    Stage-3: 18.0 Hz Earthquake (High frequency).
    Strategy: Stiff connections and retuned TMD.
    """
    return _build_extreme_tower(sandbox, base_density=5000.0, tower_scale=2.0, earthquake_freq=18.0)

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def build_agent_stage_4(sandbox):
    """
    Stage-4: Perfect Storm (Combined Extreme Conditions).
    Strategy: Maximum robustness across all parameters.
    """
    return _build_extreme_tower(sandbox, base_density=6000.0, tower_scale=5.0, earthquake_freq=18.0)

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass

# --- Helper Construction Logic for Mutated Tasks ---

def _build_extreme_tower(sandbox, base_density=100.0, tower_scale=1.0, earthquake_freq=2.0):
    """
    Revised helper focused on extreme stability and rigidity.
    """
    BEAM_HEIGHT = 1.5 
    NUM_LEVELS = 22 
    foundation_y = 1.0
    base_center_x = 0.0
    foundation = sandbox._terrain_bodies.get("foundation")
    
    # 1. Base Plate - ULTRA HEAVY to keep CoM in stability zone
    plate_width = 4.0
    foundation_plate = sandbox.add_beam(x=0, y=foundation_y + 0.75, width=plate_width, height=1.5, density=100000.0)
    if foundation:
        for j in range(100):
            ax = -2.0 + (j * 4.0 / 99)
            sandbox.add_joint(foundation, foundation_plate, (ax, foundation_y), type='rigid')

    # Single robust central leg
    base_beam = sandbox.add_beam(x=0, y=foundation_y + BEAM_HEIGHT * 1.5, width=3.8,
                                height=BEAM_HEIGHT*3.0, density=base_density)
    for j in range(100):
        jx = -1.9 + (j * 3.8 / 99)
        sandbox.add_joint(base_beam, foundation_plate, (jx, foundation_y + 1.5), type='rigid')

    # 2. Main Tower starts from above leg
    previous_beam = base_beam
    previous_y = foundation_y + BEAM_HEIGHT * 3.0
    beams = [base_beam]
    
    for i in range(1, NUM_LEVELS):
        current_y = previous_y + BEAM_HEIGHT
        w = max(1.0, 3.8 * (1 - current_y / 45.0))
        d = 100.0 * tower_scale if current_y < 15 else 10.0
        current_beam = sandbox.add_beam(x=0, y=current_y, width=w, height=BEAM_HEIGHT, density=d)
        
        num_joints = 150
        for j in range(num_joints):
            jx = base_center_x - w/2 + (j * w / (num_joints - 1))
            sandbox.add_joint(previous_beam, current_beam, (jx, previous_y + BEAM_HEIGHT/2), type='rigid')
            
        beams.append(current_beam)
        previous_beam = current_beam
        previous_y = current_y
        
    # 3. TMD System
    top_beam = beams[-1]
    td = sandbox.add_beam(x=0, y=previous_y+1.0, width=2.5, height=2.5, density=1000.0)
    target_stiffness = earthquake_freq * 0.92 
    sandbox.add_spring(top_beam, td, (0, previous_y + BEAM_HEIGHT/2), (0,0), stiffness=target_stiffness, damping=0.98)
    
    return beams[0]
