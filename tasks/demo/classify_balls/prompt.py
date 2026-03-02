"""
ClassifyBalls task Prompt and Primitives definition
"""
TASK_PROMPT = {
    'task_description': """
You need to design a ball classification device in DaVinci Sandbox.

## Task Environment (Ultra Simplified)
- Conveyor: From x=-5.0m to x=0.0m, height y=5.0m, balls spawn from left and move right
- Conveyor speed: 2.0 m/s (faster - balls move more quickly)
- Spawn point: (-4.0, 6.0), balls spawn from left side of conveyor
- Agent build area: x=[0.5, 5.0]m, y=[0.0, 5.0]m
- Blue bin (Bin A): Position (0.5, 0.0), width 3.5m (covers from -1.25 to 2.25m), height 4.0m - positioned to catch naturally falling balls
- Red bin (Bin B): Position (4.0, 0.0), width 3.0m (covers from 2.5 to 5.5m), height 4.0m - positioned right for pushed balls
- Ball radius: 0.3m (larger for easier detection and interaction)
- Ball spawn interval: 15 seconds (more time between balls for easier classification)
- Ball density: Ultra light (0.5 kg/m³) - extremely easy to push
- Total balls: 4 (reduced for easier testing)
- Sensor detection tolerance: 1.0m (ultra large - almost always detects)

## Task Objective (Simplified)
Design a device that can:
1. Detect the color of balls coming from the conveyor (red or blue)
2. For RED balls: Gently deflect/push them rightward into red bin (Bin B at x=3.0)
3. For BLUE balls: Let them naturally fall into blue bin (Bin A at x=2.0)

**Key Simplification**: 
- Blue balls naturally fall into the left bin (x=0.8) due to their trajectory
- Red balls only need a gentle push/deflection to reach the right bin (x=3.5)
- Balls have high horizontal velocity (3.5 m/s), making deflection easier
- Larger bins (2.4m x 1.5m) provide more tolerance

## Constraints
- Device must be within build area (x=[0.5, 5.0], y=[0.0, 5.0])
- Maximum sensor length: 5.0m
- Maximum piston length: 5.0m (increased for longer reach)
- Maximum motor torque: 3000 N·m (further increased for maximum power)
- Balls fall from conveyor end (x=0), need to detect and classify here or nearby
""",
    
    'success_criteria': """
## Success Criteria
- **Primary Objective**: All balls correctly classified into corresponding color bins
- Red balls must enter red bin (Bin B, x=4.0, range 2.5-5.5)
- Blue balls must enter blue bin (Bin A, x=0.5, range -1.25-2.25)
- Note: Bins overlap significantly, making classification very forgiving
- **Scoring Criteria**: Based on classification accuracy
  - 100% accuracy: 100 points
  - Partial accuracy: Score based on accuracy rate
  - 0% accuracy: 0 points
- **Simplified Design**: 
  - Blue balls naturally fall left (no action needed)
  - Red balls need gentle rightward deflection (easier than pushing)
  - Larger bins and lighter balls make classification more forgiving
""",
    
    'primitives_api': """
## Available Primitives API

### 1. Add Beam
```python
beam = sandbox.add_beam(start_pos, end_pos, material='steel', density=1.0)
```
- `start_pos`: (x, y) Start position (meters)
- `end_pos`: (x, y) End position (meters)
- `material`: Material type ('steel', 'wood', 'plastic')
- `density`: Density (kg/m³)
- Returns: Beam body object

### 2. Add Plate
```python
plate = sandbox.add_plate(center, width, height, angle=0, density=1.0)
```
- `center`: (x, y) Center position (meters)
- `width, height`: Dimensions (meters)
- `angle`: Rotation angle (radians)
- `density`: Density (kg/m³)
- Returns: Plate body object

### 3. Add Joint
```python
joint = sandbox.add_joint(body_a, body_b, anchor_point, joint_type='revolute')
```
- `body_a, body_b`: Two body objects to connect
- `anchor_point`: (x, y) Anchor point position (meters)
- `joint_type`: 'revolute' (rotating) or 'fixed' (fixed)
- Returns: Joint object

### 4. Add Piston
```python
piston = sandbox.add_piston(base_pos, direction, max_length, speed, density=1.0)
```
- `base_pos`: (x, y) Base position (meters), must be within build area
- `direction`: (dx, dy) Direction vector (normalized)
- `max_length`: Maximum extension length (meters, max 5.0m)
- `speed`: Speed (m/s)
- `density`: Density (kg/m³)
- Returns: Piston dictionary object
- **Usage**: `sandbox.activate_piston(piston, activate=True)` to activate piston

### 5. Add Motor
```python
motor = sandbox.add_motor(body, anchor_point, torque, speed)
```
- `body`: Object to drive
- `anchor_point`: (x, y) Anchor point position (meters)
- `torque`: Torque (N·m, max 500)
- `speed`: Angular velocity (rad/s)
- Returns: Motor dictionary object
- **Usage**: `sandbox.set_motor_speed(motor, speed)` to set speed

### 6. Add Raycast Sensor
```python
sensor = sandbox.add_raycast_sensor(origin, direction, length)
```
- `origin`: (x, y) Origin position (meters)
- `direction`: (dx, dy) Direction vector (normalized)
- `length`: Ray length (meters, max 5.0m)
- Returns: Sensor dictionary object
- **Usage**: `sandbox.get_detected_object_color(sensor)` to get detected color ('RED', 'BLUE', 'NONE')

### 7. Logic Gates
```python
# AND gate
and_gate = sandbox.add_logic_and(input_a, input_b)

# OR gate
or_gate = sandbox.add_logic_or(input_a, input_b)

# NOT gate
not_gate = sandbox.add_logic_not(input_a)
```
- Inputs can be sensors, logic gates, etc.
- Returns: Gate dictionary object with 'output' field

### 8. Delay
```python
delay = sandbox.add_delay(input_signal, delay_seconds, output_duration=0.1)
```
- `input_signal`: Input signal (sensor, logic gate, etc.)
- `delay_seconds`: Delay seconds
- `output_duration`: Output duration (seconds)
- Returns: Delay dictionary object

### 9. Wire
```python
wire = sandbox.add_wire(source, target)
```
- `source`: Source (sensor, logic gate, delay, etc.)
- `target`: Target (actuator, logic gate, etc.)
- Returns: Wire object

## Example Logic Flow (Simplified)
```
1. Sensor detects ball color on conveyor (before ball falls)
2. If RED ball detected:
   - Delay waits for ball to reach deflector/piston position
   - Delay outputs signal → Activate deflector/piston
   - Gentle push/deflection sends red ball rightward into red bin (x=3.0)
3. If BLUE ball detected:
   - Don't activate deflector/piston
   - Ball naturally falls into blue bin (x=2.0)

## Simplified Design Tips
- **Natural Separation**: Blue balls naturally fall left (x~0.8), red balls need gentle rightward push
- **Larger Bins**: 2.4m x 1.5m bins provide generous tolerance
- **Lighter Balls**: Density 3.0 kg/m³ makes deflection easy
- **Higher Speed**: 3.5 m/s horizontal velocity means gentle deflection is sufficient
- **More Time**: 6 seconds between balls gives plenty of reaction time
- **Larger Balls**: 0.3m radius for easier detection and interaction
- **Strategy**: Use a small deflector plate or piston to gently push red balls right, let blue balls fall naturally
```
"""
}
