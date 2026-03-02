"""
S-01: The Bridge task Agent module
Reference solution: Clean flat bridge with minimal supports
Mutated task solutions: Stage 1-4
"""
import math

def build_agent(sandbox):
    """
    Build a clean flat bridge at ground level (y=10m) to connect two cliffs.
    Simplified design with minimal supports while maintaining stability.
    """
    LEFT_CLIFF_X = 10.0
    RIGHT_CLIFF_X = 25.0
    GAP_WIDTH = 15.0
    
    DECK_TOP_Y = 10.0  # Deck top at cliff level
    DECK_HEIGHT = 0.6  # Thicker deck for stiffness
    DECK_Y = DECK_TOP_Y - DECK_HEIGHT/2  # Deck center: 9.7m
    
    left_cliff = sandbox._terrain_bodies.get("left_cliff")
    right_cliff = sandbox._terrain_bodies.get("right_cliff")
    
    if not left_cliff or not right_cliff:
        raise ValueError("Cliff bodies not found in environment")
    
    # Main deck - Split into 2 beams (7.5m each) to respect 10m max width constraint
    deck_segment_width = 7.5
    
    # Left deck segment: x=10 to x=17.5
    deck_left_center_x = LEFT_CLIFF_X + deck_segment_width / 2
    deck_left = sandbox.add_beam(
        x=deck_left_center_x,
        y=DECK_Y,
        width=deck_segment_width,
        height=DECK_HEIGHT,
        angle=0,
        density=5.0
    )
    for fixture in deck_left.fixtures:
        fixture.friction = 0.8
    
    # Right deck segment: x=17.5 to x=25
    deck_right_center_x = LEFT_CLIFF_X + deck_segment_width + deck_segment_width / 2
    deck_right = sandbox.add_beam(
        x=deck_right_center_x,
        y=DECK_Y,
        width=deck_segment_width,
        height=DECK_HEIGHT,
        angle=0,
        density=5.0
    )
    for fixture in deck_right.fixtures:
        fixture.friction = 0.8
    
    # Connect the two deck segments
    deck_connection_x = LEFT_CLIFF_X + deck_segment_width  # x=17.5
    sandbox.add_joint(deck_left, deck_right, (deck_connection_x, DECK_TOP_Y), type='rigid')
    
    # Single support layer (simplified from 3 layers)
    support_y = 8.0
    
    # Left support segment
    support_left = sandbox.add_beam(
        x=deck_left_center_x,
        y=support_y,
        width=deck_segment_width,
        height=0.8,
        angle=0,
        density=3.0
    )
    
    # Right support segment - shorten to avoid extending into cliff
    # End support layer just before cliff edge (x=24.9m instead of x=25m)
    support_right_end_x = RIGHT_CLIFF_X - 0.1  # End at x=24.9m
    support_right_start_x = deck_connection_x  # Start at x=17.5m
    support_right_width = support_right_end_x - support_right_start_x  # ~7.4m
    support_right_center_x = (support_right_start_x + support_right_end_x) / 2
    support_right = sandbox.add_beam(
        x=support_right_center_x,
        y=support_y,
        width=support_right_width,
        height=0.8,
        angle=0,
        density=3.0
    )
    
    # Connect support segments
    sandbox.add_joint(support_left, support_right, (deck_connection_x, support_y), type='rigid')
    
    # Minimal vertical supports - only 6 evenly spaced supports
    # Stop before cliff edge to avoid extending into cliff
    num_supports = 6
    for i in range(num_supports + 1):
        support_x = LEFT_CLIFF_X + (i * GAP_WIDTH / num_supports)
        
        # Skip support at cliff edge (x=25m) to avoid extending into cliff
        if support_x >= RIGHT_CLIFF_X:
            continue
        
        # Determine which deck segment to connect to
        target_deck = deck_right if support_x >= deck_connection_x else deck_left
        # Only connect to support_right if support_x is within its range
        target_support = support_right if (support_x >= deck_connection_x and support_x <= support_right_end_x) else support_left
        
        vertical = sandbox.add_beam(
            x=support_x,
            y=(support_y + DECK_Y) / 2,
            width=0.5,
            height=abs(DECK_Y - support_y),
            angle=0,
            density=3.0
        )
        sandbox.add_joint(target_support, vertical, (support_x, support_y), type='rigid')
        sandbox.add_joint(target_deck, vertical, (support_x, DECK_TOP_Y), type='rigid')
    
    # Anchor to cliffs - simplified connections
    sandbox.add_joint(left_cliff, deck_left, (LEFT_CLIFF_X, DECK_TOP_Y), type='rigid')
    sandbox.add_joint(left_cliff, support_left, (LEFT_CLIFF_X, support_y), type='rigid')
    
    sandbox.add_joint(right_cliff, deck_right, (RIGHT_CLIFF_X, DECK_TOP_Y), type='rigid')
    # Anchor support_right at its end point, not at cliff edge
    sandbox.add_joint(right_cliff, support_right, (support_right_end_x, support_y), type='rigid')
    
    # Extension from right cliff edge to target (x=25m to x=30m)
    # Start slightly after cliff edge to avoid extending deep into cliff
    extension_start_x = RIGHT_CLIFF_X + 0.1  # Start just after cliff edge
    extension_end_x = 30.0  # Target position
    extension_width = extension_end_x - extension_start_x  # Calculate width dynamically
    extension_center_x = (extension_start_x + extension_end_x) / 2
    extension = sandbox.add_beam(
        x=extension_center_x,
        y=DECK_Y,
        width=extension_width,
        height=DECK_HEIGHT,
        angle=0,
        density=5.0
    )
    for fixture in extension.fixtures:
        fixture.friction = 0.8
    
    # Connect extension to main deck at cliff edge
    sandbox.add_joint(deck_right, extension, (RIGHT_CLIFF_X, DECK_TOP_Y), type='rigid')
    # Also anchor to cliff at the edge for stability
    sandbox.add_joint(right_cliff, extension, (RIGHT_CLIFF_X, DECK_TOP_Y), type='rigid')
    
    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {total_mass:.2f}kg exceeds limit {sandbox.MAX_STRUCTURE_MASS}kg")
    
    print(f"Bridge constructed: {len(sandbox._bodies)} beams, {len(sandbox._joints)} joints, {total_mass:.2f}kg")
    
    return deck_left


def _base_agent_action(sandbox, agent_body, step_count, target_speed=4.0):
    """
    Common agent control logic to prevent vehicle from flipping and maintain target speed.
    """
    if hasattr(sandbox, '_terrain_bodies'):
        vehicle_chassis = sandbox._terrain_bodies.get("vehicle_chassis")
        if vehicle_chassis:
            current_vx = vehicle_chassis.linearVelocity.x
            current_vy = vehicle_chassis.linearVelocity.y
            angular_vel = vehicle_chassis.angularVelocity
            angle = vehicle_chassis.angle
            
            # Normalize angle to [-pi, pi]
            normalized_angle = (angle + math.pi) % (2 * math.pi) - math.pi
            
            # Anti-flip control - reduce speed if tilting
            eff_target_speed = target_speed
            if abs(normalized_angle) > 0.3:
                eff_target_speed = target_speed * 0.5
            elif abs(normalized_angle) > 0.1:
                eff_target_speed = target_speed * 0.75
            
            if abs(angular_vel) > 0.5:
                eff_target_speed = target_speed * 0.4
            
            # Smooth velocity control
            if abs(current_vx - eff_target_speed) > 0.01:
                new_vx = current_vx + (eff_target_speed - current_vx) * 0.1
                vehicle_chassis.linearVelocity = (new_vx, current_vy)
            
            # Apply angular damping to stabilize
            if abs(angular_vel) > 0.3:
                vehicle_chassis.angularVelocity = angular_vel * 0.95

def agent_action(sandbox, agent_body, step_count):
    _base_agent_action(sandbox, agent_body, step_count)

# --- Mutated Task Solutions ---

# Helper for common bridge building across mutations
def _build_generic_bridge(sandbox, num_segments=2, deck_density=5.0, support_density=3.0, 
                         num_layers=1, support_y_offset=1.5, num_verticals=12):
    """
    Generic bridge builder that can handle different gap widths and load conditions.
    - num_segments: Number of segments to span the gap
    - num_layers: Number of overlapping beams per segment (for heavy loads)
    """
    bounds = sandbox.get_terrain_bounds()
    LEFT_CLIFF_X = bounds["left_cliff"]["x_end"]
    RIGHT_CLIFF_X = bounds["right_cliff"]["start"] if "start" in bounds["right_cliff"] else bounds["right_cliff"]["x_start"]
    GAP_WIDTH = bounds["gap"]["width"]
    
    DECK_TOP_Y = 10.0
    DECK_HEIGHT = 0.6
    DECK_Y = DECK_TOP_Y - DECK_HEIGHT/2
    support_y = DECK_TOP_Y - support_y_offset
    
    segment_width = GAP_WIDTH / num_segments
    
    # Create deck segments (possibly multiple layers)
    deck_segments = []
    for i in range(num_segments):
        center_x = LEFT_CLIFF_X + (i + 0.5) * segment_width
        layer_beams = []
        for _ in range(num_layers):
            deck = sandbox.add_beam(x=center_x, y=DECK_Y, width=segment_width, height=DECK_HEIGHT, density=deck_density/num_layers)
            for f in deck.fixtures: f.friction = 0.9
            layer_beams.append(deck)
        deck_segments.append(layer_beams)
            
    # Connect deck segments horizontally
    for i in range(num_segments - 1):
        joint_x = LEFT_CLIFF_X + (i + 1) * segment_width
        for j in range(num_layers):
            sandbox.add_joint(deck_segments[i][j], deck_segments[i+1][j], (joint_x, DECK_TOP_Y), type='rigid')
            
    # Create support segments (possibly multiple layers)
    support_segments = []
    for i in range(num_segments):
        center_x = LEFT_CLIFF_X + (i + 0.5) * segment_width
        layer_beams = []
        for _ in range(num_layers):
            # Support beams are slightly shorter to avoid clipping cliffs
            support = sandbox.add_beam(x=center_x, y=support_y, width=segment_width-0.1, height=0.6, density=support_density/num_layers)
            layer_beams.append(support)
        support_segments.append(layer_beams)
            
    # Connect support segments horizontally
    for i in range(num_segments - 1):
        joint_x = LEFT_CLIFF_X + (i + 1) * segment_width
        for j in range(num_layers):
            sandbox.add_joint(support_segments[i][j], support_segments[i+1][j], (joint_x, support_y), type='rigid')
            
    # Create vertical truss members
    for i in range(num_verticals + 1):
        x = LEFT_CLIFF_X + (i * GAP_WIDTH / num_verticals)
        if x < LEFT_CLIFF_X + 0.05 or x > RIGHT_CLIFF_X - 0.05: continue
        seg_idx = min(int(i * num_segments / num_verticals), num_segments - 1)
        
        v = sandbox.add_beam(x=x, y=(support_y + DECK_Y) / 2, width=0.3, height=abs(DECK_Y - support_y), density=support_density)
        for j in range(num_layers):
            sandbox.add_joint(deck_segments[seg_idx][j], v, (x, DECK_TOP_Y), type='rigid')
            sandbox.add_joint(support_segments[seg_idx][j], v, (x, support_y), type='rigid')

    left_cliff = sandbox._terrain_bodies.get("left_cliff")
    right_cliff = sandbox._terrain_bodies.get("right_cliff")
    
    # Anchor all layers to cliffs for maximum stability
    for j in range(num_layers):
        sandbox.add_joint(left_cliff, deck_segments[0][j], (LEFT_CLIFF_X, DECK_TOP_Y), type='rigid')
        sandbox.add_joint(left_cliff, support_segments[0][j], (LEFT_CLIFF_X, support_y), type='rigid')
        sandbox.add_joint(right_cliff, deck_segments[-1][j], (RIGHT_CLIFF_X, DECK_TOP_Y), type='rigid')
        sandbox.add_joint(right_cliff, support_segments[-1][j], (RIGHT_CLIFF_X, support_y), type='rigid')
    
    # Extension from right cliff to target zone
    dn = deck_segments[-1][0]
    ext_width = 5.0 - 0.1
    ext_center_x = RIGHT_CLIFF_X + 0.1 + ext_width/2
    extension = sandbox.add_beam(x=ext_center_x, y=DECK_Y, width=ext_width, height=DECK_HEIGHT, density=deck_density)
    for f in extension.fixtures: f.friction = 0.9
    sandbox.add_joint(dn, extension, (RIGHT_CLIFF_X, DECK_TOP_Y), type='rigid')
    sandbox.add_joint(right_cliff, extension, (RIGHT_CLIFF_X, DECK_TOP_Y), type='rigid')
    
    return deck_segments[0][0]

def build_agent_stage_1(sandbox):
    # Stage 1: Wider Gap (21m)
    return _build_generic_bridge(sandbox, num_segments=3)

def agent_action_stage_1(sandbox, agent_body, step_count):
    _base_agent_action(sandbox, agent_body, step_count)

def build_agent_stage_2(sandbox):
    # Stage 2: Heavy Gravity (-15)
    return _build_generic_bridge(sandbox, num_segments=2, num_layers=2)

def agent_action_stage_2(sandbox, agent_body, step_count):
    # Slower target speed for heavy gravity stability
    _base_agent_action(sandbox, agent_body, step_count, target_speed=3.0)

def build_agent_stage_3(sandbox):
    # Stage 3: Wider Gap (21m) + Lightweight (950kg)
    return _build_generic_bridge(sandbox, num_segments=3, deck_density=4.0, support_density=2.0)

def agent_action_stage_3(sandbox, agent_body, step_count):
    _base_agent_action(sandbox, agent_body, step_count)

def build_agent_stage_4(sandbox):
    # Stage 4: Extreme Challenge (20m gap, -15 gravity, 1200kg mass)
    return _build_generic_bridge(sandbox, num_segments=4, num_layers=3, support_y_offset=3.5, num_verticals=20)

def agent_action_stage_4(sandbox, agent_body, step_count):
    # Very slow and careful for extreme conditions
    _base_agent_action(sandbox, agent_body, step_count, target_speed=2.5)
