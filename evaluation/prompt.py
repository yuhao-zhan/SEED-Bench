"""
Prompt template management module
Responsible for generating and formatting prompts sent to solver agent
"""
import os
import sys
import re
from typing import List, Optional, Tuple

# Add path to import task modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

INITIAL_DEMONSTRATION = """
# Example: Basic Task Solution

## Task Description

You need to design a vehicle that can climb slopes in the Sandbox.

### Task Environment
- Start position: x=5.0m
- Target position: x=30.0m (must pass all obstacles)
- Terrain: Contains rough terrain and obstacles
  - **Ground**: Starts from x=0, width 50m, **ground top is at y=1.0m** (ground bottom is at y=0m, ground height is 1.0m)
  - Obstacle 1: Position x=15m, height 2m, angle 0.2 radians
  - Obstacle 2: Position x=25m, height 3m, angle -0.3 radians

### Task Objective
Design a mechanical structure (vehicle) that can:
1. Move stably on the terrain
2. Pass all obstacles
3. Reach the target position (x=30.0m)

### Success Criteria
- **Primary Objective**: Agent's chassis must reach position x=30.0m
- **Secondary Constraint**: Agent cannot fall off the map (y < -10)
- **Design Constraint**: Agent cannot move backward too much (x < start_x - 5)
- **Stability Constraint**: Agent must move stably on the terrain
  - Angular velocity must remain below 2.0 rad/s
  - Altitude must remain below 8.0m
  - **Cannot rotate more than 180 degrees while airborne** (agent cannot flip/spin excessively in the air)

---

## Step 1: Physical Analysis

1. **Understand the Physics**: This task involves designing a vehicle that can traverse terrain with obstacles. Key physics principles:
   - **Kinematics**: Vehicle must move forward (x-direction) from start (5.0m) to target (30.0m)
   - **Dynamics**: Wheels provide traction and motors provide torque to overcome friction and climb slopes
   - **Geometry**: Wheel radius determines obstacle clearance (obstacles are 2m and 3m high)
   - **Stability**: Vehicle must maintain stable orientation (angular velocity < 2.0 rad/s, no excessive rotation while airborne)

2. **Design Strategy**: 
   - Use 2 wheels (maximum allowed) for stability and traction
   - Wheel radius should be large enough (≥1.5m) to clear obstacles (2m and 3m height)
   - Motor speed and torque must be sufficient to overcome friction and climb slopes
   - Chassis should be low and wide for stability

3. **Parameter Reasoning**:
   - **Wheel radius**: 1.5m provides good clearance for 2m obstacle, adequate for 3m obstacle
   - **Motor speed**: -6.0 rad/s provides sufficient forward force
   - **Motor torque**: 1800.0 N·m provides power to overcome friction and climb slopes
   - **Chassis**: Width 5.0m, height 0.4m (within 1.0m limit), positioned above wheels

## Step 2: Code

```python
def build_agent(sandbox):
    GROUND_TOP = 1.0
    WHEEL_RADIUS = 1.5
    wheel_y = GROUND_TOP + WHEEL_RADIUS
    chassis = sandbox.add_beam(x=5.0, y=wheel_y + 0.2, width=5.0, height=0.4, density=3.0)
    wheel1 = sandbox.add_wheel(x=3.2, y=wheel_y, radius=WHEEL_RADIUS, friction=4.0, density=1.0)
    wheel2 = sandbox.add_wheel(x=6.8, y=wheel_y, radius=WHEEL_RADIUS, friction=4.0, density=1.0)
    sandbox.connect(chassis, wheel1, anchor_x=3.2, anchor_y=wheel_y, motor_speed=-6.0, max_torque=1800.0)
    sandbox.connect(chassis, wheel2, anchor_x=6.8, anchor_y=wheel_y, motor_speed=-6.0, max_torque=1800.0)
    return chassis

def agent_action(sandbox, agent_body, step_count):
    pass
```

**Result**: This design successfully reaches the target position (x=30.0m) with score 100/100.

---

# Example 2: Control-Aware Task Solution

## Task Description

You need to design a speed-controlled slider system in the Sandbox.

### Task Environment
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

### Task Objective
Design a control system that can:
1. Move the slider along the track from start (x=0m) to target (x=30m)
2. **Dynamically adjust slider speed** based on current position to comply with speed limits
3. Reach the target position without violating any speed limits

### Success Criteria
- **Primary Objective**: Slider must reach position x=30.0m
- **Speed Compliance**: Slider must never exceed speed limits in any zone
  - Zone 1 (0-10m): Speed ≤ 1.5 m/s
  - Zone 2 (10-20m): Speed ≤ 3.0 m/s
  - Zone 3 (20-30m): Speed ≤ 2.0 m/s
- **Constraint**: Slider cannot fall off track (y < 2.5m or y > 3.5m)
- **Constraint**: Slider cannot move backward (x < previous_max_x - 0.5m)

---

## Step 1: Physical Analysis

1. **Understand the Physics**: This task involves designing a control system for a slider. Key physics principles:
   - **Kinematics**: Slider must move forward (x-direction) from start (0m) to target (30m)
   - **Control**: Velocity must be dynamically adjusted based on position to comply with zone speed limits
   - **Constraints**: Speed limits are strictly enforced - exceeding limit causes immediate failure
   - **Feedback Control**: Must implement position-based feedback control in `agent_action()` function

2. **Design Strategy**: 
   - Create slider at start position (x=0m)
   - Implement dynamic control in `agent_action()` that:
     - Gets current slider position
     - Determines which speed zone the slider is in
     - Sets velocity to comply with zone speed limit (with safety margin)
   - Use 95% of speed limit as target speed to ensure safety margin

3. **Parameter Reasoning**:
   - **Zone boundaries**: Match evaluator boundaries exactly (0-10m, 10-20m, 20-30m)
   - **Target speeds**: Use 95% of limit (Zone 1: 1.425 m/s, Zone 2: 2.85 m/s, Zone 3: 1.9 m/s)
   - **Safety margin**: 5% margin prevents numerical errors from causing violations
   - **Control frequency**: Called every simulation step, allowing real-time adjustment

## Step 2: Code

```python
def build_agent(sandbox):
    # Create slider at start position
    slider = sandbox.add_slider(x=0.0, y=sandbox.TRACK_Y, width=0.5, height=0.3, density=1.0)
    
    return {
        'slider': slider
    }

def agent_action(sandbox, agent_components, step_count):
    # Get slider
    slider = agent_components.get('slider')
    if not slider:
        return
    
    # Get slider state
    position_x, velocity_x = sandbox.get_slider_state(slider)
    
    # Determine target speed based on current zone
    if position_x < 0.0:
        # Before start - move forward slowly
        target_speed = 1.0
    elif 0.0 <= position_x < 10.0:
        # Zone 1: Speed limit 1.5 m/s - use low speed
        target_speed = 1.5 * 0.95  # 95% of limit for safety margin
    elif 10.0 <= position_x < 20.0:
        # Zone 2: Speed limit 3.0 m/s - can use higher speed
        target_speed = 3.0 * 0.95  # 95% of limit for safety margin
    elif 20.0 <= position_x < 30.0:
        # Zone 3: Speed limit 2.0 m/s - reduce speed
        target_speed = 2.0 * 0.95  # 95% of limit for safety margin
    else:
        # After target - stop
        target_speed = 0.0
    
    # Apply control - use direct velocity setting
    sandbox.set_slider_velocity(slider, target_speed)
```

**Result**: This design successfully reaches the target position (x=30.02m) with score 100/100, no speed violations.

---

"""


# Revision demonstration: shows how to diagnose and fix based on feedback
REVISION_DEMONSTRATION = """# Example: Revision Process

## Task Description

You need to design a vehicle that can climb slopes in the Sandbox.

### Task Environment
- Start position: x=5.0m
- Target position: x=30.0m (must pass all obstacles)
- Terrain: Contains rough terrain and obstacles
  - **Ground**: Starts from x=0, width 50m, **ground top is at y=1.0m** (ground bottom is at y=0m, ground height is 1.0m)
  - Obstacle 1: Position x=15m, height 2m, angle 0.2 radians
  - Obstacle 2: Position x=25m, height 3m, angle -0.3 radians

### Task Objective
Design a mechanical structure (vehicle) that can:
1. Move stably on the terrain
2. Pass all obstacles
3. Reach the target position (x=30.0m)

### Success Criteria
- **Primary Objective**: Agent's chassis must reach position x=30.0m
- **Secondary Constraint**: Agent cannot fall off the map (y < -10)
- **Design Constraint**: Agent cannot move backward too much (x < start_x - 5)
- **Stability Constraint**: Agent must move stably on the terrain
  - Angular velocity must remain below 2.0 rad/s
  - Altitude must remain below 8.0m
  - **Cannot rotate more than 180 degrees while airborne** (agent cannot flip/spin excessively in the air)

---

## Previous Attempt (with issues)

```python
def build_agent(sandbox):
    GROUND_TOP = 1.0
    WHEEL_RADIUS = 1.0  # Too small - reduces obstacle clearance
    wheel_y = GROUND_TOP + WHEEL_RADIUS
    chassis = sandbox.add_beam(x=5.0, y=wheel_y + 0.2, width=5.0, height=0.4, density=3.0)
    wheel1 = sandbox.add_wheel(x=3.2, y=wheel_y, radius=WHEEL_RADIUS, friction=4.0, density=1.0)
    wheel2 = sandbox.add_wheel(x=6.8, y=wheel_y, radius=WHEEL_RADIUS, friction=4.0, density=1.0)
    sandbox.connect(chassis, wheel1, anchor_x=3.2, anchor_y=wheel_y, motor_speed=-3.0, max_torque=1000.0)
    sandbox.connect(chassis, wheel2, anchor_x=6.8, anchor_y=wheel_y, motor_speed=-3.0, max_torque=1000.0)
    return chassis

def agent_action(sandbox, agent_body, step_count):
    pass
```

## Evaluation Feedback

## Iteration 1 Evaluation Results

❌ **Task failed**: Vehicle rotated 180.3° while airborne (exceeds 180° limit)

**Score**: 0.0/100

## Task Execution Results

**Distance traveled**: 14.84m
**Current position**: x=19.84m, y=2.76m
**Target position**: x=30.00m
**Progress**: 59.4%
**Maximum distance reached**: 15.75m
**Simulation steps**: 700

**Physical State Information**:
- Agent position: (19.838, 2.759)
- Agent velocity: 4.058 m/s
- Agent velocity components: vx=0.647 m/s, vy=-4.006 m/s
- Agent angular velocity: 1.209 rad/s
- Agent angle: 3.718 rad (213.0°)

**Additional Metrics**:
- is_airborne: True
- airborne_rotation_accumulated: 3.147 rad (180.3°) - net rotation (true flip)

## Step 1: Physical Diagnosis (Required)

### 1. Interpret Metrics
- Distance traveled: 14.84m (target: 25.0m)
- Progress: 59.4%
- Final position: x=19.84m (target: 30.0m)
- Final velocity: 4.058 m/s
- Angular velocity: 1.209 rad/s
- Airborne rotation accumulated: 3.147 rad (180.3°) - this is the **net rotation** (absolute difference between clockwise and counterclockwise rotations), indicating the vehicle has truly flipped

### 2. Identify the Physical Problem
The vehicle failed due to excessive rotation while airborne. The metrics show:
- **Stability violation**: Vehicle rotated 180.3° while airborne (net rotation), exceeding the 180° limit
- **Root cause**: The combination of small wheel radius (1.0m) and low motor power (speed -3.0 rad/s, torque 1000.0 N·m) causes the vehicle to launch into the air when hitting obstacles
- **Physical mechanism**: When the vehicle hits an obstacle with insufficient power and small wheels, it gets launched upward. While airborne, the low motor torque cannot maintain stable orientation, causing the vehicle to flip (net rotation exceeds 180°, meaning the vehicle has truly flipped - rear wheels have passed the front wheels)
- **Note on rotation tracking**: The system tracks net rotation (the absolute difference between clockwise and counterclockwise rotations). If the vehicle rotates CCW then CW back, they cancel out. Only when the net rotation exceeds 180° does it indicate a true flip.
- **Evidence**: Vehicle reached x=19.84m (59% progress) but failed due to instability (flipping), not lack of progress

### 3. Propose Fix
To address these physical issues:
1. **Increase wheel radius** from 1.0m to 1.5m: Larger wheels provide better geometric clearance and reduce the likelihood of launching into the air when hitting obstacles
2. **Increase motor speed** from -3.0 rad/s to -6.0 rad/s: Higher angular velocity generates more forward force, allowing smoother obstacle traversal without launching
3. **Increase motor torque** from 1000.0 N·m to 1800.0 N·m: Higher torque provides more power to maintain stable motion and prevent excessive rotation, especially when airborne

**Why this works**: Larger wheels reduce the impact angle when hitting obstacles, preventing launch. Higher motor parameters provide sufficient force to maintain forward motion and stability, preventing excessive rotation even if the vehicle briefly becomes airborne.

## Step 2: Fixed Code

```python
def build_agent(sandbox):
    GROUND_TOP = 1.0
    WHEEL_RADIUS = 1.5  # Fixed: increased from 1.0m
    wheel_y = GROUND_TOP + WHEEL_RADIUS
    chassis = sandbox.add_beam(x=5.0, y=wheel_y + 0.2, width=5.0, height=0.4, density=3.0)
    wheel1 = sandbox.add_wheel(x=3.2, y=wheel_y, radius=WHEEL_RADIUS, friction=4.0, density=1.0)
    wheel2 = sandbox.add_wheel(x=6.8, y=wheel_y, radius=WHEEL_RADIUS, friction=4.0, density=1.0)
    sandbox.connect(chassis, wheel1, anchor_x=3.2, anchor_y=wheel_y, motor_speed=-6.0, max_torque=1800.0)  # Fixed: increased speed and torque
    sandbox.connect(chassis, wheel2, anchor_x=6.8, anchor_y=wheel_y, motor_speed=-6.0, max_torque=1800.0)  # Fixed: increased speed and torque
    return chassis

def agent_action(sandbox, agent_body, step_count):
    pass
```

**Result**: Fixed design successfully reaches the target position (x=30.0m) with score 100/100.

---

# Example 2: Control-Aware Task Revision

## Task Description

You need to design a speed-controlled slider system in the Sandbox.

### Task Environment
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

### Task Objective
Design a control system that can:
1. Move the slider along the track from start (x=0m) to target (x=30m)
2. **Dynamically adjust slider speed** based on current position to comply with speed limits
3. Reach the target position without violating any speed limits

### Success Criteria
- **Primary Objective**: Slider must reach position x=30.0m
- **Speed Compliance**: Slider must never exceed speed limits in any zone
  - Zone 1 (0-10m): Speed ≤ 1.5 m/s
  - Zone 2 (10-20m): Speed ≤ 3.0 m/s
  - Zone 3 (20-30m): Speed ≤ 2.0 m/s
- **Constraint**: Slider cannot fall off track (y < 2.5m or y > 3.5m)
- **Constraint**: Slider cannot move backward (x < previous_max_x - 0.5m)

---

## Previous Attempt (with issues)

```python
def build_agent(sandbox):
    # Create slider at start position
    slider = sandbox.add_slider(x=0.0, y=sandbox.TRACK_Y, width=0.5, height=0.3, density=1.0)
    
    return {
        'slider': slider
    }

def agent_action(sandbox, agent_components, step_count):
    # Get slider
    slider = agent_components.get('slider')
    if not slider:
        return
    
    # WRONG: Using fixed speed (2.5 m/s) for all zones
    # This violates Zone 1 limit (1.5 m/s) and Zone 3 limit (2.0 m/s)
    fixed_speed = 2.5  # Too fast for Zone 1 and Zone 3
    
    # Apply control
    sandbox.set_slider_velocity(slider, fixed_speed)
```

## Evaluation Feedback

## Iteration 1 Evaluation Results

❌ **Task failed**: Speed limit violated in Zone 1: speed 2.50 m/s exceeds limit 1.50 m/s

**Score**: 0.0/100

## Task Execution Results

**Distance traveled**: 4.17m
**Current position**: x=4.17m
**Target position**: x=30.00m
**Progress**: 13.9%
**Maximum distance reached**: 4.17m

**Speed Zone Information**:
- Current zone: Zone 1
- Speed limit: 1.50 m/s
- Current speed: 2.50 m/s
- ⚠️ **SPEED LIMIT VIOLATED**
- Total speed violations: 2

## Step 1: Physical Diagnosis (Required)

### 1. Interpret Metrics
- Distance traveled: 4.17m (target: 30.0m)
- Progress: 13.9%
- Final position: x=4.17m (target: 30.0m)
- Final velocity: 2.50 m/s
- Speed violation: True (2 violations detected)
- Current zone: Zone 1 (speed limit 1.50 m/s)

### 2. Identify the Physical Problem
The control system failed due to speed limit violation. The metrics show:
- **Speed limit violation**: Slider speed (2.50 m/s) exceeds Zone 1 limit (1.50 m/s)
- **Root cause**: Using fixed speed (2.5 m/s) for all zones instead of dynamic control
  - Fixed speed violates Zone 1 limit (1.5 m/s) - slider speed is 67% over limit
  - Fixed speed would also violate Zone 3 limit (2.0 m/s) if slider reached that zone
  - **Critical issue**: No position-based feedback control - speed is not adjusted based on slider position
- **Physical mechanism**: The task requires dynamic control that adjusts speed as slider moves through different zones. Fixed speed cannot comply with varying speed limits across zones.

### 3. Propose Fix
To address these physical issues:
1. **Implement dynamic control**: Replace fixed speed with position-based speed control in `agent_action()`
2. **Get current position**: Use `sandbox.get_slider_state(slider)` to get current x position
3. **Determine zone**: Check which speed zone the slider is in based on position
4. **Set zone-appropriate speed**: Set velocity to comply with zone limit (use 95% of limit for safety margin)
   - Zone 1 (0-10m): Set speed to 1.425 m/s (95% of 1.5 m/s)
   - Zone 2 (10-20m): Set speed to 2.85 m/s (95% of 3.0 m/s)
   - Zone 3 (20-30m): Set speed to 1.9 m/s (95% of 2.0 m/s)

**Why this works**: Dynamic control allows the slider to adjust speed in real-time based on position. The 95% safety margin prevents numerical errors from causing violations. Position-based feedback ensures compliance with zone-specific speed limits.

## Step 2: Fixed Code

```python
def build_agent(sandbox):
    # Create slider at start position
    slider = sandbox.add_slider(x=0.0, y=sandbox.TRACK_Y, width=0.5, height=0.3, density=1.0)
    
    return {
        'slider': slider
    }

def agent_action(sandbox, agent_components, step_count):
    # Get slider
    slider = agent_components.get('slider')
    if not slider:
        return
    
    # Get slider state
    position_x, velocity_x = sandbox.get_slider_state(slider)
    
    # Determine target speed based on current zone
    # Fixed: Implement dynamic control based on position
    if position_x < 0.0:
        # Before start - move forward slowly
        target_speed = 1.0
    elif 0.0 <= position_x < 10.0:
        # Zone 1: Speed limit 1.5 m/s - use low speed
        target_speed = 1.5 * 0.95  # Fixed: 95% of limit for safety margin
    elif 10.0 <= position_x < 20.0:
        # Zone 2: Speed limit 3.0 m/s - can use higher speed
        target_speed = 3.0 * 0.95  # Fixed: 95% of limit for safety margin
    elif 20.0 <= position_x < 30.0:
        # Zone 3: Speed limit 2.0 m/s - reduce speed
        target_speed = 2.0 * 0.95  # Fixed: 95% of limit for safety margin
    else:
        # After target - stop
        target_speed = 0.0
    
    # Apply control - use direct velocity setting
    sandbox.set_slider_velocity(slider, target_speed)
```

**Result**: Fixed design successfully reaches the target position (x=30.02m) with score 100/100, no speed violations.

---

"""


# Task setting for all mutated (cross-environment) prompts: clarify that we migrated from old to new env
MUTATED_TASK_SETTING = """## Task Setting

You are adapting a solution from an **old (source) environment** to a **new (target) environment**. The environment has changed (e.g. terrain, physics, constraints). Your goal is to revise the code so it works in the **new** environment. Numbers and criteria in the task description and success criteria below are for the **new** environment; where the source environment differed, it is noted as "(originally ... in the source environment)".
"""

# Mutated environment demonstration: shows how to adapt when environment changes
# Contains two examples: one requiring only build_agent changes, one requiring both build_agent and agent_action
MUTATED_DEMONSTRATION = """# Example: Environment Change Adaptation

## Task Description

You need to design a vehicle that can climb slopes in the Sandbox.

### Task Environment
- Start position: x=5.0m
- Target position: x=30.0m (must pass all obstacles)
- Terrain: Contains rough terrain and obstacles
  - **Ground**: Starts from x=0, width 50m, **ground top is at y=1.0m** (ground bottom is at y=0m, ground height is 1.0m)
  - Obstacle 1: Position x=15m, height 2m, angle 0.2 radians
  - Obstacle 2: Position x=25m, height 3m, angle -0.3 radians

### Task Objective
Design a mechanical structure (vehicle) that can:
1. Move stably on the terrain
2. Pass all obstacles
3. Reach the target position (x=30.0m)

### Success Criteria
- **Primary Objective**: Agent's chassis must reach position x=30.0m
- **Secondary Constraint**: Agent cannot fall off the map (y < -10)
- **Design Constraint**: Agent cannot move backward too much (x < start_x - 5)
- **Stability Constraint**: Agent must move stably on the terrain
  - Angular velocity must remain below 2.0 rad/s
  - Altitude must remain below 8.0m
  - **Cannot rotate more than 180 degrees while airborne** (agent cannot flip/spin excessively in the air)

---

## Previous Successful Code (worked in the Original Environment)

```python
def build_agent(sandbox):
    GROUND_TOP = 1.0
    WHEEL_RADIUS = 1.5
    wheel_y = GROUND_TOP + WHEEL_RADIUS
    chassis = sandbox.add_beam(x=5.0, y=wheel_y + 0.2, width=5.0, height=0.4, density=3.0)
    wheel1 = sandbox.add_wheel(x=3.2, y=wheel_y, radius=WHEEL_RADIUS, friction=4.0, density=1.0)
    wheel2 = sandbox.add_wheel(x=6.8, y=wheel_y, radius=WHEEL_RADIUS, friction=4.0, density=1.0)
    sandbox.connect(chassis, wheel1, anchor_x=3.2, anchor_y=wheel_y, motor_speed=-6.0, max_torque=1800.0)
    sandbox.connect(chassis, wheel2, anchor_x=6.8, anchor_y=wheel_y, motor_speed=-6.0, max_torque=1800.0)
    return chassis

def agent_action(sandbox, agent_body, step_count):
    pass
```

## Test Result in Original Environment

✅ **Task completed successfully!**

**Score**: 100.0/100

**Distance traveled**: 37.43m
**Current position**: x=42.43m, y=2.71m
**Target position**: x=30.00m
**Progress**: 100.0%

---

# Example : Environment Change

## ⚠️ CRITICAL: The Physical Environment Has Changed

The physics environment has been modified. Your previously successful design NO LONGER WORKS.
You must **infer what changed** from the feedback and adapt.

## Feedback from Running Previous Code in the NEW Environment

## Iteration 1 Evaluation Results

⚠️ **Task not completed**

**Score**: 24.8/100

## Task Execution Results

**Distance traveled**: 7.75m
**Current position**: x=12.75m, y=3.64m
**Target position**: x=30.00m
**Progress**: 31.0%
**Maximum distance reached**: 7.75m
**Simulation steps**: 588

**Physical State Information**:
- Agent position: (12.751, 3.639)
- Agent velocity: 0.000 m/s
- Agent velocity components: vx=0.000 m/s, vy=-0.000 m/s
- Agent angular velocity: -0.000 rad/s
- Agent angle: 0.565 rad (32.4°)

**Additional Metrics**:
- is_airborne: True
- airborne_rotation_accumulated: 0.339 rad

## Step 1: Environment Change Diagnosis (Required)

### 1. Compare Expected vs Actual
The code worked successfully in the original environment (reached target, score 100/100).
However, in the new environment, the same code failed or performed poorly.

### 2. Hypothesize
Based on the feedback, the physical environment has changed. Key observations:
- Vehicle only traveled 7.75m (target: 25.0m), far less than expected
- Vehicle appears stuck or unable to maintain forward motion
- **Likely cause**: Ground friction has decreased significantly
- Low friction causes wheels to slip, especially with high motor torque and speed
- High motor speed (-6.0 rad/s) with low ground friction causes excessive wheel spin, preventing forward progress

### 3. Plan Adaptation
To adapt to low friction environment:
1. **Increase wheel friction** from 4.0 to 5.0: Higher friction provides better traction on slippery surfaces
2. **Reduce motor speed** from -6.0 to -3.2 rad/s: Lower speed prevents wheel slip in low friction conditions
3. **Increase wheel radius** from 1.5m to 1.8m: Larger wheels provide better contact area and stability
4. **Widen wheelbase** (1.5 to 8.5m): Wider wheelbase increases stability on slippery surfaces
5. **Lower chassis** (height 0.2m, y=wheel_y+0.0): Lower center of mass improves stability
6. **Adjust density** (chassis 1.5, wheels 1.0): Balanced weight distribution for stability

**Why this works**: In low friction environments, high torque causes wheel slip. Lower speed with higher wheel friction provides better traction. Wider wheelbase and lower center of mass prevent sliding and improve stability.

## Step 2: Adapted Code (Static Parameters Only)

```python
def build_agent(sandbox):
    GROUND_TOP = 1.0
    WHEEL_RADIUS = 1.8  # Larger wheels for better obstacle clearance
    wheel_y = GROUND_TOP + WHEEL_RADIUS
    # Very wide wheelbase (1.5 to 8.5) and low chassis for maximum stability
    # Balanced density for stability
    chassis = sandbox.add_beam(x=5.0, y=wheel_y + 0.0, width=7.5, height=0.2, density=1.5)
    wheel1 = sandbox.add_wheel(x=1.5, y=wheel_y, radius=WHEEL_RADIUS, friction=5.0, density=1.0)
    wheel2 = sandbox.add_wheel(x=8.5, y=wheel_y, radius=WHEEL_RADIUS, friction=5.0, density=1.0)
    # Safe speed to prevent rotation, maximum torque to overcome obstacles
    sandbox.connect(chassis, wheel1, anchor_x=1.5, anchor_y=wheel_y, motor_speed=-3.2, max_torque=2000.0)
    sandbox.connect(chassis, wheel2, anchor_x=8.5, anchor_y=wheel_y, motor_speed=-3.2, max_torque=2000.0)
    return chassis

def agent_action(sandbox, agent_body, step_count):
    pass
```

## Test Result in New Environment (with Adapted Code)

✅ **Task completed successfully!**

**Score**: 100.0/100

**Distance traveled**: 29.49m
**Current position**: x=34.49m, y=2.93m
**Target position**: x=30.00m
**Progress**: 100.0%

---

"""


def normalize_task_path_to_module(task_path: str) -> str:
    """
    Convert task path to Python module name
    Handles special characters like '-' that are not valid in Python module names
    
    Args:
        task_path: Task path like 'Category1_Statics_Equilibrium/S_01' or 'demo/basic'
    Returns:
        Python module path like 'Category1_Statics_Equilibrium.S_01' or 'demo.basic'
    """
    # Replace '/' with '.' and '-' with '_' for Python module compatibility
    module_path = task_path.replace('/', '.').replace('-', '_')
    return module_path


def parse_task_name(task_name: str) -> Tuple[str, str]:
    """
    Parse task name into (task_path, module_path)
    Supports multiple formats:
    - 'category_1_01' -> ('Category1_Statics_Equilibrium/S_01', 'Category1_Statics_Equilibrium.S_01')
    - 'category_1' -> ('Category1_Statics&Equilibrium', 'Category1_Statics_Equilibrium') (for category-level)
    - 'Category1_Statics_Equilibrium/S_01' -> (same, normalized module path)
    - 'demo/basic' -> ('demo/basic', 'demo.basic')
    - 'basic' -> ('demo/basic', 'demo.basic') (legacy format)
    
    Args:
        task_name: Task name in various formats
    Returns:
        Tuple of (task_path, module_path) where:
        - task_path: File system path relative to tasks/ directory
        - module_path: Python module path (normalized)
    """
    tasks_dir = os.path.join(os.path.dirname(__file__), '..', 'tasks')
    
    # Pattern: category_X_YY where X is category number, YY is task number
    category_task_pattern = re.match(r'^category_(\d+)_(\d+)$', task_name.lower())
    if category_task_pattern:
        cat_num = int(category_task_pattern.group(1))
        task_num = int(category_task_pattern.group(2))
        
        # Map category numbers to category names and task subdir prefix (S_ for Cat1, K_ for Cat2, etc.)
        category_map = {
            1: 'Category1_Statics_Equilibrium',
            2: 'Category2_Kinematics_Linkages',
            3: 'Category3_Dynamics_Energy',
            4: 'Category4_Granular_FluidInteraction',
            5: 'Category5_Cybernetics_Control',
            6: 'Category6_ExoticPhysics',
        }
        category_task_prefix = {
            1: 'S',
            2: 'K',
            3: 'D',  # Category3_Dynamics_Energy uses D_01, D_02, ...
            4: 'F',  # Category4_Granular_FluidInteraction uses F_01, F_02, ...
            5: 'C',  # Category5_Cybernetics_Control uses C_01, C_02, ...
            6: 'E',  # Category6_ExoticPhysics uses E_01, E_02, ...
        }
        
        if cat_num not in category_map:
            raise ValueError(f"Unknown category number: {cat_num}. Supported: 1-6")
        
        category_name = category_map[cat_num]
        prefix = category_task_prefix.get(cat_num, 'S')
        task_subdir = f'{prefix}_{task_num:02d}'  # S_01, K_01, etc. to match directory names
        task_path = f'{category_name}/{task_subdir}'
        module_path = normalize_task_path_to_module(task_path)
        return task_path, module_path
    
    # Pattern: category_X (category-level, no specific task)
    category_pattern = re.match(r'^category_(\d+)$', task_name.lower())
    if category_pattern:
        cat_num = int(category_pattern.group(1))
        category_map = {
            1: 'Category1_Statics_Equilibrium',
            2: 'Category2_Kinematics_Linkages',
            3: 'Category3_Dynamics_Energy',
            4: 'Category4_Granular_FluidInteraction',
            5: 'Category5_Cybernetics_Control',
            6: 'Category6_ExoticPhysics',
        }
        if cat_num not in category_map:
            raise ValueError(f"Unknown category number: {cat_num}. Supported: 1-6")
        category_name = category_map[cat_num]
        task_path = category_name
        module_path = normalize_task_path_to_module(task_path)
        return task_path, module_path
    
    # Check if it's already a path format (contains '/')
    if '/' in task_name:
        task_path = task_name
        module_path = normalize_task_path_to_module(task_path)
        return task_path, module_path
    
    # Legacy format: check if it's a demo task
    demo_tasks = ['basic', 'classify_balls', 'control_aware', 'simple_task']
    if task_name in demo_tasks:
        task_path = f'demo/{task_name}'
        module_path = normalize_task_path_to_module(task_path)
        return task_path, module_path
    
    # Try direct module import (backward compatibility)
    task_path = task_name
    module_path = task_name
    return task_path, module_path


def get_all_tasks_in_category(category_num: int) -> List[str]:
    """
    Get all task names in a category
    
    Args:
        category_num: Category number (1-6)
    Returns:
        List of task names in format 'category_X_YY'
    """
    category_map = {
        1: 'Category1_Statics_Equilibrium',
        2: 'Category2_Kinematics_Linkages',
        3: 'Category3_Dynamics_Energy',
        4: 'Category4_Granular_FluidInteraction',
        5: 'Category5_Cybernetics_Control',
        6: 'Category6_ExoticPhysics',
    }
    
    if category_num not in category_map:
        raise ValueError(f"Unknown category number: {category_num}. Supported: 1-6")
    
    category_name = category_map[category_num]
    # Task subdir prefix per category: Category1 uses S_01, Category2 uses K_01, Category3 uses D_01, Category5 uses C_01, Category6 uses E_01, etc.
    category_task_prefix = {
        1: 'S',
        2: 'K',
        3: 'D',
        4: 'F',  # Category4 uses F_01, F_02, ...
        5: 'C',  # Category5 uses C_01, C_02, ...
        6: 'E',  # Category6 uses E_01, E_02, ...
    }
    prefix = category_task_prefix.get(category_num, 'S')
    prefix_pattern = re.compile(rf'^{re.escape(prefix)}_(\d+)$')

    tasks_dir = os.path.join(os.path.dirname(__file__), '..', 'tasks', category_name)
    
    if not os.path.exists(tasks_dir):
        return []
    
    tasks = []
    for item in sorted(os.listdir(tasks_dir)):
        item_path = os.path.join(tasks_dir, item)
        if os.path.isdir(item_path):
            task_match = prefix_pattern.match(item)
            if task_match:
                task_num = int(task_match.group(1))
                tasks.append(f'category_{category_num}_{task_num:02d}')
    
    return tasks


def get_all_tasks() -> List[str]:
    """
    Get all task names across all categories
    
    Returns:
        List of task names in format 'category_X_YY'
    """
    all_tasks = []
    for cat_num in range(1, 7):
        all_tasks.extend(get_all_tasks_in_category(cat_num))
    return all_tasks


def load_task_prompt(task_name):
    """
    Load task prompt and primitives
    Args:
        task_name: Task name in various formats ('category_1_01', 'Category1_Statics_Equilibrium/S_01', 'basic', etc.)
    Returns:
        dict: Dictionary containing task_description and primitives_api
    """
    import importlib
    
    # Parse task name to get file system path and module path
    task_path, module_path = parse_task_name(task_name)
    
    # Build full path to prompt.py file (for existence check)
    script_dir = os.path.dirname(os.path.dirname(__file__))
    prompt_file = os.path.join(script_dir, 'tasks', task_path, 'prompt.py')
    
    if not os.path.exists(prompt_file):
        raise ImportError(f"Prompt file not found: {prompt_file}")
    
    # Load module via proper package import so relative imports (from ...primitives_api) work
    full_module_name = f"tasks.{module_path}.prompt"
    mod = importlib.import_module(full_module_name)
    
    return mod.TASK_PROMPT


def _with_prompt_trailer(prompt: str, task_prompt: dict) -> str:
    """Append mutated-environment footer after the full formatted prompt when present."""
    trailer = (task_prompt.get("prompt_trailer") or "").strip()
    if not trailer:
        return prompt
    return prompt.rstrip() + "\n\n" + trailer + "\n"


def format_initial_prompt(task_prompt):
    """
    Format initial prompt (first iteration) with one-shot demonstration
    Args:
        task_prompt: Dictionary returned from load_task_prompt
    Returns:
        str: Formatted prompt string
    """
    # One-shot demonstration: reference solution for basic task
    
    prompt = f"""# Task Description

{task_prompt['task_description']}

# Success Criteria

{task_prompt['success_criteria']}

# Available Primitives API

{task_prompt['primitives_api']}

{INITIAL_DEMONSTRATION}

# Your Task

You are designing a physical system in a 2D physics simulation. Before writing code, you MUST reason through the physical design.

## Step 1: Physical Analysis (Required)

1. **Understand the Physics**: What physical principles govern this task? (equilibrium, kinematics, dynamics, energy, fluid interaction, etc.)

2. **Design Strategy**: How will your structure/mechanism achieve the goal? What is the key physical insight?

3. **Parameter Reasoning**: Estimate key parameters (dimensions, masses, forces, speeds) based on physical reasoning.

## Step 2: Write Code

**Code Requirements**:
- All code must be inside functions
- Do not use `sandbox` variable outside functions

**Output Format**:

```python
def build_agent(sandbox):
    # Your implementation
    return chassis

def agent_action(sandbox, agent_body, step_count):
    # Control logic if needed
    pass
```

Begin with your physical analysis, then provide the code.
"""
    return _with_prompt_trailer(prompt, task_prompt)


def format_revision_prompt(task_prompt, previous_code, feedback):
    """
    Format revision prompt (subsequent iterations) with one-shot demonstration
    Args:
        task_prompt: Dictionary returned from load_task_prompt
        previous_code: Code from previous iteration
        feedback: Evaluation feedback
    Returns:
        str: Formatted prompt string
    """
    prompt = f"""# Task Description

{task_prompt['task_description']}

# Success Criteria

{task_prompt['success_criteria']}

# Available Primitives API

{task_prompt['primitives_api']}

{REVISION_DEMONSTRATION}

# Previous Iteration Code

```python
{previous_code}
```

# Evaluation Feedback

{feedback}

# Your Task: Diagnose and Fix

## Step 1: Physical Diagnosis (Required)

Analyze the feedback to find the **root physical cause**:

1. **Interpret Metrics**: What do the numbers tell you about the system's behavior?

2. **Identify the Physical Problem**: Based on the metrics, what is physically wrong? (e.g., insufficient force, wrong direction, instability, constraint violation, energy loss, timing issue, etc.)

3. **Propose Fix**: What specific changes will address this physical issue? Explain WHY.

## Step 2: Implement the Fix

Modify the code based on your diagnosis.

**Code Requirements**:
- All code must be inside functions
- Do not use `sandbox` variable outside functions
- Provide COMPLETE code

**Output Format**:

```python
def build_agent(sandbox):
    # Your fixed implementation
    return chassis

def agent_action(sandbox, agent_body, step_count):
    # Control logic if needed
    pass
```

Begin with your physical diagnosis, then provide the fixed code.
"""
    return _with_prompt_trailer(prompt, task_prompt)


def format_system_prompt_with_task(task_prompt, include_demonstrations=True):
    """
    Format system prompt that includes task information.
    Used when context='all' to avoid repeating task info in each turn.
    Args:
        task_prompt: Dictionary returned from load_task_prompt
        include_demonstrations: Whether to include demonstration examples
    Returns:
        str: Formatted system prompt string
    """
    demonstrations = INITIAL_DEMONSTRATION if include_demonstrations else ""
    
    system_prompt = f"""You are a physics-based agent designer for a 2D physics simulation.

When given a task:
1) FIRST: analyze the physical situation and reason about a design/strategy
2) THEN: output the final implementation code

Output requirements:
- You MAY include analysis text BEFORE the code
- You MUST include the code inside ONE fenced block: ```python ... ```
- The code MUST define `build_agent(sandbox)` (return the main body)
- Optionally define `agent_action(sandbox, agent_body, step_count)` for control
- Do NOT include any text AFTER the code block

# Task Description

{task_prompt['task_description']}

# Success Criteria

{task_prompt['success_criteria']}

# Available Primitives API

{task_prompt['primitives_api']}

{demonstrations}

# Your Task

You are designing a physical system in a 2D physics simulation. Before writing code, you MUST reason through the physical design.

## Step 1: Physical Analysis (Required)

1. **Understand the Physics**: What physical principles govern this task? (equilibrium, kinematics, dynamics, energy, fluid interaction, etc.)

2. **Design Strategy**: How will your structure/mechanism achieve the goal? What is the key physical insight?

3. **Parameter Reasoning**: Estimate key parameters (dimensions, masses, forces, speeds) based on physical reasoning.

## Step 2: Write Code

**Code Requirements**:
- All code must be inside functions
- Do not use `sandbox` variable outside functions

**Output Format**:

```python
def build_agent(sandbox):
    # Your implementation
    return chassis

def agent_action(sandbox, agent_body, step_count):
    # Control logic if needed
    pass
```

Begin with your physical analysis, then provide the code.
"""
    return _with_prompt_trailer(system_prompt, task_prompt)


def format_revision_prompt_chat(task_prompt, feedback):
    """
    Revision prompt for multi-turn chat mode with one-shot demonstration.
    The model is expected to have access to the full conversation history (all previous solutions + feedback).
    Args:
        task_prompt: Dictionary returned from load_task_prompt
        feedback: Evaluation feedback from the last run
    Returns:
        str: Formatted prompt string
    """
    prompt = f"""# Task Description

{task_prompt['task_description']}

# Success Criteria

{task_prompt['success_criteria']}

# Available Primitives API

{task_prompt['primitives_api']}

{REVISION_DEMONSTRATION}

# Latest Evaluation Feedback (most important)

{feedback}

# Your Task

You have access to the FULL conversation history of all previous attempts (solutions + feedback).

## Step 1: Physical Diagnosis (Required)

Infer the root physical cause of failure/success trends from the feedback and the history of changes.

## Step 2: Provide the Next Attempt

Give the next improved solution.

Remember: include analysis first if needed, then output ONE ```python ... ``` code block containing the complete updated implementation.
"""
    return _with_prompt_trailer(prompt, task_prompt)


def format_revision_prompt_chat_simplified(feedback, iteration: int = 2):
    """
    Simplified revision prompt for multi-turn chat mode when context='all'.
    Task information is already in system prompt, so we only send feedback.
    Args:
        feedback: Evaluation feedback from the last run
        iteration: Current iteration number (default 2). If iteration == 2, includes REVISION_DEMONSTRATION
    Returns:
        str: Formatted prompt string (only feedback, with demonstration for iteration 2)
    """
    # Include REVISION_DEMONSTRATION for the second iteration
    demonstration = ""
    if iteration == 2:
        demonstration = f"""
# ⚠️ Note: The example below uses an example task that is different from the current task - focus on the revision methodology, not the specific solution.

{REVISION_DEMONSTRATION}

--------------------------------
"""
    
    prompt = f"""{demonstration}# Latest Evaluation Feedback

{feedback}

# Your Task

You have access to the FULL conversation history of all previous attempts (solutions + feedback).
The task description, success criteria, and API documentation are in the system prompt.

## Step 1: Physical Diagnosis (Required)

Infer the root physical cause of failure/success trends from the feedback and the history of changes.

## Step 2: Provide the Next Attempt

Give the next improved solution.

Remember: include analysis first if needed, then output ONE ```python ... ``` code block containing the complete updated implementation.
"""
    return prompt


def format_mutated_revision_prompt_chat_simplified(feedback):
    """
    Simplified revision prompt for mutated tasks in multi-turn chat mode when context='all'.
    Task information is already in system prompt, so we only send feedback.
    Args:
        feedback: Evaluation feedback from the last run
    Returns:
        str: Formatted prompt string (only feedback)
    """
    prompt = f"""# Latest Evaluation Feedback

{feedback}

# Your Task

You have access to the FULL conversation history of all previous attempts (solutions + feedback).
The task description, success criteria, and API documentation are in the system prompt.

## Step 1: Environment Change Diagnosis (Required)

1. **Compare Expected vs Actual**: The code worked before. What behavior do you expect vs what actually happened?

2. **Hypothesize**: What physical property likely changed? (gravity, friction, constraints, material properties, etc.)
   - **Note**: Multiple physical parameters may have changed simultaneously.

3. **Plan Adaptation**: How will you modify the design to compensate?

## Step 2: Implement Adapted Design

Provide the next improved solution.

Remember: include analysis first if needed, then output ONE ```python ... ``` code block containing the complete updated implementation.
"""
    return prompt


def format_revision_prompt_last_n(task_prompt, previous_codes_and_feedbacks, feedback):
    history_section = ""
    for i, (code, fb) in enumerate(previous_codes_and_feedbacks, 1):
        history_section += f"\n## Attempt {i}:\n\n```python\n{code}\n```\n\nFeedback: {fb}\n"
    
    # Note: feedback parameter is the same as the last item in previous_codes_and_feedbacks
    # We don't display it separately to avoid duplication
    prompt = f"""# Task Description

{task_prompt['task_description']}

# Success Criteria

{task_prompt['success_criteria']}

# Available Primitives API

{task_prompt['primitives_api']}

{REVISION_DEMONSTRATION}

# Previous Attempts (Last {len(previous_codes_and_feedbacks)} iterations)

{history_section}

# Your Task: Diagnose and Fix

Analyze the trend across these attempts to identify the root physical cause, then provide an improved solution.

**Output Format**:

```python
def build_agent(sandbox):
    # Your improved implementation
    return chassis

def agent_action(sandbox, agent_body, step_count):
    # Control logic if needed
    pass
```

Begin with your analysis, then provide the code.
"""
    return _with_prompt_trailer(prompt, task_prompt)


def format_revision_prompt_best_score(task_prompt, best_code, best_feedback, current_feedback):
    prompt = f"""# Task Description

{task_prompt['task_description']}

# Success Criteria

{task_prompt['success_criteria']}

# Available Primitives API

{task_prompt['primitives_api']}

{REVISION_DEMONSTRATION}

# Best-Scoring Attempt (Reference)

```python
{best_code}
```

Feedback from best attempt: {best_feedback}

# Latest Evaluation Feedback

{current_feedback}

# Your Task: Diagnose and Fix

Compare the best attempt with the latest results. What worked well? What needs improvement? Provide an improved solution.

**Output Format**:

```python
def build_agent(sandbox):
    # Your improved implementation
    return chassis

def agent_action(sandbox, agent_body, step_count):
    # Control logic if needed
    pass
```

Begin with your analysis, then provide the code.
"""
    return _with_prompt_trailer(prompt, task_prompt)


def format_revision_prompt_best_plus_previous(task_prompt, best_code, best_feedback, previous_code, previous_feedback, current_feedback, best_iteration=None, previous_iteration=None, current_iteration=None, memory_block=None):
    # Check if iterations are the same (avoid duplication)
    show_previous = previous_code and (best_iteration != previous_iteration if best_iteration is not None and previous_iteration is not None else True)
    # current_feedback is always the same as the most recent iteration's feedback, which is either:
    # - best_feedback (if best == previous, i.e., show_previous is False)
    # - previous_feedback (if best != previous, i.e., show_previous is True)
    # So we should never show current_feedback separately - it's always a duplicate
    show_current = False

    # When memory_block is provided (e.g. rememberer), insert after demonstration and before best attempt
    memory_section = f"""

---
## Relevant experience from memory (same-category other tasks)

{memory_block}

""" if memory_block else ""

    prompt = f"""# Task Description

{task_prompt['task_description']}

# Success Criteria

{task_prompt['success_criteria']}

# Available Primitives API

{task_prompt['primitives_api']}

{REVISION_DEMONSTRATION}
{memory_section}
# Best-Scoring Attempt (Reference)

```python
{best_code}
```

Feedback: {best_feedback}
{'' if not show_previous else f'''
# Previous Attempt

```python
{previous_code}
```

Feedback: {previous_feedback}
'''}
{'' if not show_current else f'''
# Latest Evaluation Feedback

{current_feedback}
'''}

# Your Task: Diagnose and Fix

Compare these attempts. Learn from what worked best and what changed recently. Provide an improved solution.

**Output Format**:

```python
def build_agent(sandbox):
    # Your improved implementation
    return chassis

def agent_action(sandbox, agent_body, step_count):
    # Control logic if needed
    pass
```

Begin with your analysis, then provide the code.
"""
    return _with_prompt_trailer(prompt, task_prompt)


def format_mutated_revision_prompt_best_plus_previous(
    task_prompt,
    previous_successful_code,
    feedback_from_running_original_in_new_env,
    best_code,
    best_feedback,
    previous_code,
    previous_feedback,
    current_feedback,
    best_iteration=None,
    previous_iteration=None,
    current_iteration=None,
    rememberer_memory_block=None,
):
    """
    Mutated task revision prompt: same structure as format_revision_prompt_best_plus_previous
    (best + previous), but prepended with env-change notice + original successful code + its
    feedback in the new environment. One whole prompt (no system/user split).
    """
    show_previous = previous_code and (
        best_iteration != previous_iteration
        if best_iteration is not None and previous_iteration is not None
        else True
    )

    _mem = f"\n\n{rememberer_memory_block.strip()}\n\n" if rememberer_memory_block else ""

    prompt = f"""{MUTATED_TASK_SETTING}

# Task Description

{task_prompt['task_description']}

# Success Criteria

{task_prompt['success_criteria']}

# Available Primitives API

{task_prompt['primitives_api']}

{MUTATED_DEMONSTRATION}

# ⚠️ CRITICAL: The Physical Environment Has Changed

The physics environment has been modified. Your previously successful design NO LONGER WORKS.

# Previous Successful Code (worked in the Original Environment)

```python
{previous_successful_code}
```

# Feedback from Running in the NEW Environment (Iteration 1)

{feedback_from_running_original_in_new_env}

You must **infer what changed** from the feedback above and adapt.
{_mem}# Best-Scoring Attempt So Far (in New Environment)

```python
{best_code}
```

Feedback: {best_feedback}
{'' if not show_previous else f'''
# Previous Attempt

```python
{previous_code}
```

Feedback: {previous_feedback}
'''}

# Your Task: Diagnose and Adapt

Compare these attempts. Learn from what worked best and what changed recently. Provide an improved adapted solution.

**Output Format**:

```python
def build_agent(sandbox):
    # Your improved implementation
    return chassis

def agent_action(sandbox, agent_body, step_count):
    # Control logic if needed
    pass
```

Begin with your analysis, then provide the code.
"""
    return _with_prompt_trailer(prompt, task_prompt)


def format_mutated_revision_prompt(
    task_prompt,
    previous_successful_code,
    feedback_from_running_original_in_new_env,
    previous_code,
    previous_feedback,
    last_feedback,
    rememberer_memory_block=None,
):
    """
    Mutated task revision prompt (previous attempt only): env change + original code + its feedback,
    then previous attempt + latest feedback. One whole prompt.
    """
    _mem = f"\n\n{rememberer_memory_block.strip()}\n\n" if rememberer_memory_block else ""

    prompt = f"""{MUTATED_TASK_SETTING}

# Task Description

{task_prompt['task_description']}

# Success Criteria

{task_prompt['success_criteria']}

# Available Primitives API

{task_prompt['primitives_api']}

{MUTATED_DEMONSTRATION}

# ⚠️ CRITICAL: The Physical Environment Has Changed

The physics environment has been modified. Your previously successful design NO LONGER WORKS.

# Previous Successful Code (worked in the Original Environment)

```python
{previous_successful_code}
```

# Feedback from Running in the NEW Environment (Iteration 1)

{feedback_from_running_original_in_new_env}
{_mem}# Previous Attempt (in New Environment)

```python
{previous_code}
```

Feedback: {previous_feedback}

# Latest Evaluation Feedback

{last_feedback}

# Your Task: Diagnose and Adapt

Analyze the feedback and provide an improved adapted solution.

**Output Format**:

```python
def build_agent(sandbox):
    # Your improved implementation
    return chassis

def agent_action(sandbox, agent_body, step_count):
    # Control logic if needed
    pass
```

Begin with your analysis, then provide the code.
"""
    return _with_prompt_trailer(prompt, task_prompt)


def format_revision_prompt_memory_only(task_prompt):
    """
    Format revision prompt for a_mem_sys: same structure as revision (task + REVISION_DEMONSTRATION)
    but no inline previous/best code or feedback. History is provided only via the memory block
    appended after this prompt (in evaluate.py).
    """
    prompt = f"""# Task Description

{task_prompt['task_description']}

# Success Criteria

{task_prompt['success_criteria']}

# Available Primitives API

{task_prompt['primitives_api']}

{REVISION_DEMONSTRATION}

# Relevant Experience from Memory

Below you will see relevant experience from memory (past attempts and feedback). Use it to diagnose and provide an improved solution.

# Your Task: Diagnose and Fix

Use the experience from memory (provided below) to inform your analysis and code. Provide an improved solution.

**Output Format**:

```python
def build_agent(sandbox):
    # Your improved implementation
    return chassis

def agent_action(sandbox, agent_body, step_count):
    # Control logic if needed
    pass
```

Begin with your analysis, then provide the code.
"""
    return _with_prompt_trailer(prompt, task_prompt)


def format_mutated_prompt(task_prompt, previous_successful_code, feedback, rememberer_memory_block=None):
    """
    Prompt for every round of mutated task. Mutated has no separate "initial" — each round
    is a revision/adaptation given previous successful code and its feedback in the new environment.
    Self-contained: task description, success criteria, API, env-change notice, previous code, feedback.
    """
    _mem = f"\n\n{rememberer_memory_block.strip()}\n\n" if rememberer_memory_block else ""

    prompt = f"""{MUTATED_TASK_SETTING}

# Task Description

{task_prompt['task_description']}

# Success Criteria

{task_prompt['success_criteria']}

# Available Primitives API

{task_prompt['primitives_api']}

{MUTATED_DEMONSTRATION}

# ⚠️ CRITICAL: The Physical Environment Has Changed

The physics environment has been modified. Your previously successful design NO LONGER WORKS.

# Previous Successful Code (worked in the Original Environment)
# (Self-contained: includes build_agent, agent_action, and all functions they call.)

```python
{previous_successful_code}
```

# Feedback from Running in the NEW Environment

{feedback}

You must **infer what changed** from the feedback above and adapt.
{_mem}# Your Task: Diagnose and Adapt

## Step 1: Environment Change Diagnosis (Required)

1. **Compare Expected vs Actual**: The code worked before. What behavior do you expect vs what actually happened?

2. **Hypothesize**: What physical property likely changed? (gravity, friction, constraints, material properties, etc.)
   - **Note**: Multiple physical parameters may have changed simultaneously.

3. **Plan Adaptation**: How will you modify the design to compensate?

## Step 2: Implement Adapted Design

**Code Requirements**:
- All code must be inside functions
- Do not use `sandbox` variable outside functions
- Provide COMPLETE code

**Output Format**:

```python
def build_agent(sandbox):
    # Adapted implementation
    return chassis

def agent_action(sandbox, agent_body, step_count):
    # Control logic if needed
    pass
```

Begin with your diagnosis, then provide the adapted code.
"""
    return _with_prompt_trailer(prompt, task_prompt)
