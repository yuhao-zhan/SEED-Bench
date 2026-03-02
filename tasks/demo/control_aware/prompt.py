"""
Control-Aware task Prompt and Primitives definition
Task: Speed-controlled slider - control slider speed based on position to comply with speed limits
"""
TASK_PROMPT = {
    'task_description': """
You need to design a speed-controlled slider system in DaVinci Sandbox.

## Task Environment
- **Track**: A horizontal track from x=0m to x=30m at height y=3.0m
  - Track width: 0.3m
  - Track is frictionless (slider moves smoothly)
- **Slider**: A movable slider on the track
  - Slider starts at x=0m
  - Slider must reach x=30m (target position)
  - Slider can move horizontally along the track
- **Speed Limit Zones** (CRITICAL - Must be enforced):
  - **Zone 1** (x: 0m to 10m): Maximum speed **1.5 m/s** (strict enforcement)
  - **Zone 2** (x: 10m to 20m): Maximum speed **3.0 m/s** (strict enforcement)
  - **Zone 3** (x: 20m to 30m): Maximum speed **2.0 m/s** (strict enforcement)
  - **Violation**: If slider speed exceeds the zone limit, the task fails immediately

## Task Objective
Design a control system that can:
1. Move the slider along the track from start (x=0m) to target (x=30m)
2. **Dynamically adjust slider speed** based on current position to comply with speed limits
3. Reach the target position without violating any speed limits

## Control Requirement (CRITICAL)
- **Cannot use fixed speed** - must adjust based on slider position
- Must implement feedback control in `agent_action()` function
- Control strategy: 
  - Get current slider position (x coordinate)
  - Determine which speed zone the slider is in
  - Adjust slider velocity to comply with the zone's speed limit
  - Update slider velocity dynamically

## Constraints
- Slider must stay on track (y ≈ 3.0m, cannot fall off)
- Maximum slider speed: 5.0 m/s (hard limit)
- Slider cannot move backward (x cannot decrease)
- Control system must respond within reasonable time (< 30 seconds to reach target)
""",
    
    'success_criteria': """
## Success Criteria
- **Primary Objective**: Slider must reach position x=30.0m
- **Speed Compliance**: Slider must never exceed speed limits in any zone
  - Zone 1 (0-10m): Speed ≤ 1.5 m/s
  - Zone 2 (10-20m): Speed ≤ 3.0 m/s
  - Zone 3 (20-30m): Speed ≤ 2.0 m/s
- **Constraint**: Slider cannot fall off track (y < 2.5m or y > 3.5m)
- **Constraint**: Slider cannot move backward (x < previous_max_x - 0.5m)

## Scoring Criteria
- Successful completion: 100 points (must meet all constraints including speed limits)
- Partial completion: Based on distance traveled, up to 80 points (if speed limits violated, score is 0)
- Failure: 0 points (fell off track, moved backward, violated speed limits, or timeout)
""",
    
    'primitives_api': """
## Available Primitives API

### 1. Add Slider
```python
slider = sandbox.add_slider(x, y, width, height, density=1.0)
```
- `x, y`: Slider center position (meters)
- `width, height`: Slider dimensions (meters)
- `density`: Density (kg/m³)
- Returns: Slider body object
- **Note**: Slider is constrained to move along the track (y position fixed)

### 2. Get Slider State
```python
position, velocity = sandbox.get_slider_state(slider)
```
- `slider`: Slider body object
- Returns: `(position, velocity)` tuple
  - `position`: Current x position (meters)
  - `velocity`: Current x velocity (m/s)

### 3. Set Slider Velocity
```python
sandbox.set_slider_velocity(slider, velocity_x)
```
- `slider`: Slider body object
- `velocity_x`: Horizontal velocity (m/s, range [0, 5.0])
- **Note**: This sets slider velocity directly (simplified control)
- **CRITICAL**: Velocity can be adjusted dynamically in `agent_action()` based on position

### 4. Apply Force to Slider
```python
sandbox.apply_force_to_slider(slider, force_x)
```
- `slider`: Slider body object
- `force_x`: Horizontal force (N)
- **Note**: Alternative control method using forces

## Control Logic Requirement
You must implement the `agent_action()` function that:
1. Gets current slider position (x coordinate)
2. Determines which speed zone the slider is in
3. Calculates appropriate velocity based on zone limit
4. Updates slider velocity dynamically

Example control logic structure:
```python
def agent_action(sandbox, agent_components, step_count):
    slider = agent_components['slider']
    
    # Get slider state
    position, velocity = sandbox.get_slider_state(slider)
    
    # Determine target speed based on zone
    if 0 <= position < 10:
        # Zone 1: Speed limit 1.5 m/s
        target_speed = 1.5
    elif 10 <= position < 20:
        # Zone 2: Speed limit 3.0 m/s
        target_speed = 3.0
    elif 20 <= position < 30:
        # Zone 3: Speed limit 2.0 m/s
        target_speed = 2.0
    else:
        # After target - stop or slow down
        target_speed = 0.0
    
    # Apply control (with some margin to stay under limit)
    safe_speed = target_speed * 0.95  # 95% of limit to be safe
    sandbox.set_slider_velocity(slider, safe_speed)
```

## Physics Background
- Slider moves along frictionless track
- Velocity control: Setting velocity directly controls slider movement
- Speed limits: Must be strictly enforced - exceeding limit causes failure
- Dynamic control: Must adjust speed as slider moves through different zones
"""
}
