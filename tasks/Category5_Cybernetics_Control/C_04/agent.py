import math

def build_agent(sandbox):
    """
    Returns the agent's physical body.
    """
    return sandbox.get_agent_body()

def agent_action(sandbox, agent_body, step_count):
    """
    C-04: The Escaper - Behavioral Unlock Controller.
    Navigates the maze, performs the counterintuitive unlock (backward force @ low speed),
    and holds in the narrow exit zone.
    """
    # --- State Initialization ---
    if not hasattr(agent_body, '_controller_state'):
        agent_body._controller_state = {
            'phase': 'APPROACH',
            'timer': 0,
            'prev_x': None,
            'prev_y': None,
            'vx': 0.0,
            'vy': 0.0
        }
    state = agent_body._controller_state
    
    # --- Perception ---
    pos = sandbox.get_agent_position()
    x, y = pos[0], pos[1]
    front, left, right = sandbox.get_whisker_readings()
    
    # Manual velocity estimation
    dt = 1.0/60.0
    if state['prev_x'] is not None:
        state['vx'] = (x - state['prev_x']) / dt
        state['vy'] = (y - state['prev_y']) / dt
    state['prev_x'], state['prev_y'] = x, y
    vx, vy = state['vx'], state['vy']
    
    # --- Control Logic ---
    fx, fy = 0.0, 0.0
    
    # Maze Navigation - Target Y varies by X to clear obstacles
    if x < 4.0:
        target_y = 1.5
    elif x < 6.0:
        target_y = 1.9  # Clear first bottom obstacle
    elif x < 8.5:
        target_y = 1.5  # Activation zone area
    elif x < 12.0:
        target_y = 1.3  # Middle slit at x=9
    elif x < 15.5:
        target_y = 0.9  # Clear top obstacle at x=14
    else:
        target_y = 1.35 # Exit zone center
        
    if state['phase'] == 'APPROACH':
        # Move to the activation zone (x in [6, 8]) and hit the top wall
        target_y_act = 2.3 
        
        if x < 6.2:
            fx = 45.0
        else:
            # PD control to stabilize at x=7.0
            fx = 30.0 * (7.0 - x) - 15.0 * vx
        
        fy = 30.0 * (target_y_act - y) - 8.0 * vy + 50.0 
        
        # Trigger unlock when in zone, at top wall, and stable
        if 6.2 < x < 7.8 and y > 2.2 and abs(vx) < 0.5:
            state['phase'] = 'UNLOCK'
            state['timer'] = 0
            
    elif state['phase'] == 'UNLOCK':
        # Behavioral unlock: fx < -30 and speed < 1.0 for 25 steps.
        # Stay at the wall to maintain friction.
        fx = -31.0
        fy = 100.0  
        state['timer'] += 1
        if state['timer'] > 60:
            state['phase'] = 'ESCAPE'
            
    elif state['phase'] == 'ESCAPE':
        # Navigate past the current and wind obstacles to the exit
        fx = 65.0 # High thrust to overcome backward current and wind
        fy = 40.0 * (target_y - y) - 10.0 * vy + 50.0 # Added 50.0 for gravity comp
        
        # Wind compensation (wind is down at 15.5 < x < 18.0)
        if 15.5 < x < 18.0:
            fy += 28.0 # Upward force to counter wind
            
        # Basic obstacle avoidance
        if left < 0.5: fy -= 25.0
        if right < 0.5: fy += 25.0
        if front < 0.6 and x < 18.0: fx = -20.0
        
        if x > 18.5:
            state['phase'] = 'HOLD'
            
    elif state['phase'] == 'HOLD':
        # Precision hold in the narrow exit zone (x >= 18.0, y in [1.25, 1.45])
        # Target (19.0, 1.35)
        fx = 50.0 * (19.0 - x) - 20.0 * vx
        fy = 80.0 * (1.35 - y) - 25.0 * vy + 50.0 
        
    sandbox.apply_agent_force(fx, fy)
